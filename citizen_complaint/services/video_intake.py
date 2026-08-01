"""
Step 1 — Video intake.

fetch_metadata()   -> title/description/channel via YouTube Data API v3
                       (falls back to oEmbed when no API key or non-YouTube URL)
fetch_transcript()  -> auto-caption transcript via Supadata (YouTube, Rumble, etc.)
extract_incident_data() -> regex pass over description+transcript for
                       agencies/emails/phones/addresses/links, then an AI
                       pass (GPT-4o) for the rest (spoken location/agency
                       mentions, summary), following the same
                       call-then-parse-JSON pattern as
                       documents/services/openai_service.py

run_intake(incident) is the single entry point the view calls; it owns
quota enforcement via services.api_quota.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse, parse_qs

import requests
from django.conf import settings

from citizen_complaint.models import TargetAgency
from citizen_complaint.services import api_quota

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15

EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
PHONE_RE = re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
URL_RE = re.compile(r'https?://\S+')
ADDRESS_RE = re.compile(
    r'\d{1,6}\s+[A-Za-z0-9.\'\s]{2,60}\b(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|'
    r'Dr|Drive|Ln|Lane|Way|Ct|Court|Pl|Place|Hwy|Highway)\b\.?,?\s*[A-Za-z\s]{0,30},?\s*[A-Z]{2}\s*\d{5}?',
    re.IGNORECASE,
)


def detect_platform(url: str) -> str:
    host = (urlparse(url).hostname or '').lower()
    if 'youtube.com' in host or 'youtu.be' in host:
        return 'youtube'
    if 'rumble.com' in host:
        return 'rumble'
    return 'other'


def extract_youtube_id(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if 'youtu.be' in host:
        return parsed.path.lstrip('/').split('/')[0]
    if 'youtube.com' in host:
        qs = parse_qs(parsed.query)
        if 'v' in qs:
            return qs['v'][0]
        # /shorts/<id> or /embed/<id>
        parts = [p for p in parsed.path.split('/') if p]
        if parts:
            return parts[-1]
    return ''


def regex_extract_contacts(text: str) -> dict:
    """Cheap, deterministic pass — always run regardless of AI availability."""
    if not text:
        return {'emails': [], 'phones': [], 'addresses': [], 'links': []}
    return {
        'emails': sorted(set(EMAIL_RE.findall(text))),
        'phones': sorted(set(PHONE_RE.findall(text))),
        'addresses': sorted(set(m.strip() for m in ADDRESS_RE.findall(text))),
        'links': sorted(set(URL_RE.findall(text))),
    }


# ---------------------------------------------------------------------------
# Metadata fetch
# ---------------------------------------------------------------------------

def _http_error_detail(exc: requests.RequestException) -> str:
    """requests.HTTPError's default message is just the generic status line
    ('403 Client Error: Forbidden for url: ...') — it never includes the
    response body, which is where Google/oEmbed's actual reason lives (e.g.
    'API key not valid', 'quotaExceeded', 'accessNotConfigured'). Surfacing
    the body is the difference between a real diagnosis and a bare status
    code."""
    response = getattr(exc, 'response', None)
    if response is None:
        return str(exc)
    detail = ''
    try:
        detail = response.json().get('error', {}).get('message', '')
    except ValueError:
        pass
    if not detail:
        detail = (response.text or '').strip()[:300]
    return f'{exc} — {detail}' if detail else str(exc)


def fetch_youtube_metadata(video_id: str) -> tuple[dict | None, str | None]:
    api_key = getattr(settings, 'YOUTUBE_API_KEY', '')
    if not api_key or not video_id:
        return None, 'YouTube Data API key not configured or invalid video ID.'
    try:
        resp = requests.get(
            'https://www.googleapis.com/youtube/v3/videos',
            params={'id': video_id, 'part': 'snippet', 'key': api_key},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items') or []
        if not items:
            return None, 'Video not found or is private/unlisted.'
        snippet = items[0].get('snippet', {})
        return {
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'channel_name': snippet.get('channelTitle', ''),
            'published_at': snippet.get('publishedAt', ''),
        }, None
    except requests.RequestException as exc:
        logger.exception('YouTube Data API call failed')
        return None, _http_error_detail(exc)


def fetch_oembed_metadata(url: str, platform: str) -> tuple[dict | None, str | None]:
    """Fallback for non-YouTube platforms (or when no YouTube API key is set).
    oEmbed never returns a description — only title + author — so extraction
    quality is lower via this path."""
    oembed_endpoints = {
        'youtube': 'https://www.youtube.com/oembed',
        'rumble': 'https://rumble.com/api/Media/oembed.json',
    }
    endpoint = oembed_endpoints.get(platform)
    if not endpoint:
        return None, f'No oEmbed endpoint known for platform "{platform}".'
    try:
        resp = requests.get(endpoint, params={'url': url, 'format': 'json'}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return {
            'title': data.get('title', ''),
            'description': '',
            'channel_name': data.get('author_name', ''),
        }, None
    except requests.RequestException as exc:
        logger.exception('oEmbed call failed')
        return None, _http_error_detail(exc)


def fetch_metadata(video_url: str, platform: str) -> tuple[dict | None, str | None]:
    if platform == 'youtube':
        video_id = extract_youtube_id(video_url)
        metadata, api_error = fetch_youtube_metadata(video_id)
        if metadata:
            return metadata, None
        # Fall back to oEmbed (title/channel only, never a description) if the
        # Data API isn't configured or the call failed. Surface BOTH errors —
        # oEmbed failing too doesn't mean the Data API's own failure reason
        # should be lost; that's usually the more actionable one (missing/
        # invalid key, quota) and was previously discarded here.
        metadata, oembed_error = fetch_oembed_metadata(video_url, platform)
        if metadata:
            return metadata, None
        return None, f'YouTube Data API: {api_error} | oEmbed fallback: {oembed_error}'
    return fetch_oembed_metadata(video_url, platform)


# ---------------------------------------------------------------------------
# Transcript fetch (Supadata)
# ---------------------------------------------------------------------------

def fetch_transcript(video_url: str) -> tuple[str, str | None]:
    """
    Supadata covers YouTube, TikTok, and other platforms behind one API.
    NOTE: verify the request/response shape against Supadata's current docs
    before relying on this in production — this integration was written
    without live access to their docs.
    """
    api_key = getattr(settings, 'SUPADATA_API_KEY', '')
    if not api_key:
        return '', 'SUPADATA_API_KEY not configured.'
    try:
        resp = requests.get(
            'https://api.supadata.ai/v1/transcript',
            params={'url': video_url, 'text': 'true'},
            headers={'x-api-key': api_key},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get('content', '')
        if isinstance(content, list):
            content = ' '.join(seg.get('text', '') for seg in content)
        return content or '', None
    except requests.RequestException as exc:
        logger.exception('Supadata transcript call failed')
        return '', str(exc)


# ---------------------------------------------------------------------------
# AI extraction pass
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You help identify government agencies and contact details from a \
video about a citizen's encounter with officials (e.g. a First Amendment audit, a \
police stop, a public-records dispute).

Given a video title, description, and (if available) a spoken transcript, extract:
- agencies: list of every distinct government agency/department mentioned or clearly \
implicated (e.g. "Saint Louis Public Library", "Saint Louis Metropolitan Police Department"). \
An incident can involve multiple agencies.
- location: best-guess city/state or address where the incident occurred.
- incident_date: date if mentioned, else empty string.
- contacts: any names, emails, phone numbers, or agency contacts mentioned in the story.
- summary: 2-4 sentence neutral, factual summary of what happened, from the citizen's \
perspective, with no legal conclusions.
- agency_contacts: many auditors list exactly who to complain to right in the video \
description — a block naming an agency followed by named officials and their direct \
emails (e.g. "Joseph A. Farrow- Chief of Police / Email: jafarrow@ucdavis.edu"). When the \
description or transcript contains such an explicit block, return one entry per agency: \
{"agency": "<agency name, matching an entry in agencies>", "address": "<street address if \
given, else empty string>", "phone": "<general phone if given, else empty string>", \
"contacts": [{"name": "...", "title": "...", "email": "..."}, ...]}. Only include a \
contact if their email is EXPLICITLY written in the text — copy it exactly, character for \
character. Never invent, guess, or complete a partial email address. If no such explicit \
block exists anywhere in the text, return an empty list for agency_contacts.

Return ONLY a JSON object with exactly these keys: agencies (list of strings), \
location (string), incident_date (string), contacts (list of strings), summary (string), \
agency_contacts (list of objects as described above)."""


def _call_openai(user_message: str) -> tuple[str | None, str | None]:
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        return None, 'OPENAI_API_KEY is not configured.'
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_message},
            ],
            temperature=0.2,
            response_format={'type': 'json_object'},
        )
        return response.choices[0].message.content, None
    except Exception as exc:
        logger.exception('OpenAI extraction call failed')
        return None, str(exc)


def verify_agency_contacts(raw_agency_contacts: list, verified_emails: set[str]) -> dict[str, list[dict]]:
    """
    Cross-checks each AI-proposed (agency, name, title, email) against the
    deterministic regex pass over the same text. An email that isn't
    literally present in the description/transcript is dropped rather than
    trusted — this is what lets 'description' source be pre-checked by
    default instead of treated as an unverified guess.

    Returns {agency_name: [{'name', 'title', 'email'}, ...]}, agency names
    as originally written by the AI (matched case-insensitively by callers).
    """
    verified: dict[str, list[dict]] = {}
    for entry in raw_agency_contacts or []:
        agency_name = (entry.get('agency') or '').strip()
        if not agency_name:
            continue
        good_contacts = []
        for contact in entry.get('contacts') or []:
            email = (contact.get('email') or '').strip()
            if not email or email.lower() not in verified_emails:
                continue
            good_contacts.append({
                'name': (contact.get('name') or '').strip(),
                'title': (contact.get('title') or '').strip(),
                'email': email,
            })
        if good_contacts:
            verified.setdefault(agency_name, []).extend(good_contacts)
    return verified


def ai_extract(incident) -> tuple[dict | None, str | None]:
    user_message = (
        f'Title: {incident.video_title}\n\n'
        f'Description:\n{incident.video_description}\n\n'
        f'Transcript:\n{incident.transcript[:12000]}\n'
    )
    raw, error = _call_openai(user_message)
    if error:
        return None, error
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f'Could not parse AI response: {exc}'


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_intake(incident) -> tuple[bool, str]:
    """
    Runs the full Step 1 pipeline for `incident`: metadata, transcript,
    regex extraction, AI extraction. Populates fields + creates detected
    TargetAgency rows. Returns (success, message).

    Each external call consumes one unit of the incident's AI/API quota;
    raises QuotaExceeded/AICallTooSoon (caller handles the user-facing message).
    """
    platform = detect_platform(incident.video_url)
    incident.video_platform = platform

    api_quota.consume_call(incident)
    metadata, meta_error = fetch_metadata(incident.video_url, platform)
    if metadata:
        incident.video_title = metadata.get('title', '')[:500]
        incident.video_description = metadata.get('description', '')
        incident.video_channel_name = metadata.get('channel_name', '')[:255]
        incident.metadata_json = metadata
    else:
        incident.extraction_error = meta_error or 'Could not fetch video metadata.'

    api_quota.consume_call(incident)
    transcript, transcript_error = fetch_transcript(incident.video_url)
    incident.transcript = transcript
    if transcript_error and not transcript:
        incident.extraction_error = (incident.extraction_error + ' ' if incident.extraction_error else '') + \
            f'Transcript unavailable: {transcript_error}'

    regex_hits = regex_extract_contacts(f'{incident.video_description}\n{incident.transcript}')

    api_quota.consume_call(incident)
    ai_data, ai_error = ai_extract(incident)
    if ai_error:
        incident.extraction_error = (incident.extraction_error + ' ' if incident.extraction_error else '') + \
            f'AI extraction failed: {ai_error}'
        ai_data = {}

    verified_emails = {e.lower() for e in regex_hits['emails']}
    agency_contacts = verify_agency_contacts(
        ai_data.get('agency_contacts', []) if ai_data else [], verified_emails,
    )

    extracted = {
        'agencies': ai_data.get('agencies', []) if ai_data else [],
        'location': ai_data.get('location', '') if ai_data else '',
        'incident_date': ai_data.get('incident_date', '') if ai_data else '',
        'contacts': ai_data.get('contacts', []) if ai_data else [],
        'summary': ai_data.get('summary', '') if ai_data else '',
        'agency_contacts': agency_contacts,
        'regex': regex_hits,
    }
    incident.extracted_data = extracted
    incident.status = 'agencies_reviewed' if extracted['agencies'] else 'intake'
    incident.current_step = 1
    incident.save()

    _create_detected_agencies(incident, extracted['agencies'], agency_contacts)

    if not metadata and not ai_data:
        return False, 'Could not extract anything useful from this video. You can still add agencies manually.'
    return True, 'Video processed.'


def _normalize_agency_name(name: str) -> str:
    return re.sub(r'[^a-z0-9 ]', '', name.lower()).strip()


def _create_detected_agencies(incident, agency_names, agency_contacts=None):
    """
    Creates a TargetAgency row per agency, plus one extra row per named
    official found in the description (agency_contacts).

    agency_contacts is keyed by whatever agency name the AI wrote in that
    part of its response — which is NOT guaranteed to match, character for
    character, how the same agency is spelled in the plain `agencies` list
    (e.g. "U.C. Davis Police Department" vs "UC Davis"). An earlier version
    of this function required the two to match before trusting the named
    contacts, which silently dropped real, regex-verified data whenever the
    AI phrased them differently. Now agency_contacts entries are processed
    using their OWN name directly — no matching required — and the plain
    `agencies` list only fills in names not already covered by a contacts
    block (compared loosely, just to avoid an obvious duplicate row).
    """
    from citizen_complaint.services.agency_lookup import match_curated_agency, resolve_agency_email

    agency_contacts = agency_contacts or {}
    existing_rows = set(incident.target_agencies.values_list('name', 'contact_name'))
    existing_general = {name for name, contact_name in existing_rows if not contact_name}
    order = incident.target_agencies.count()
    location = incident.extracted_data.get('location', '')
    covered_normalized = set()

    for raw_name, contacts in agency_contacts.items():
        name = (raw_name or '').strip()[:255]
        if not name or not contacts:
            continue

        for contact in contacts:
            key = (name, contact['name'][:255])
            if key in existing_rows:
                continue
            existing_rows.add(key)
            TargetAgency.objects.create(
                incident=incident, name=name, email=contact['email'],
                contact_name=contact['name'][:255], contact_title=contact['title'][:255],
                source='description', confirmed=True, order=order,
            )
            order += 1

        covered_normalized.add(_normalize_agency_name(name))

        if name in existing_general:
            continue
        # Admin-vetted general line still wins when it exists, added alongside
        # the named contacts; skip the AI/SerpApi guess entirely since we
        # already have a real, source-verified answer for this agency.
        email = match_curated_agency(name, location)
        if email:
            existing_general.add(name)
            TargetAgency.objects.create(
                incident=incident, name=name, email=email, source='db_match', order=order,
            )
            order += 1

    for name in agency_names:
        name = (name or '').strip()
        if not name:
            continue
        name = name[:255]
        if _normalize_agency_name(name) in covered_normalized or name in existing_general:
            continue

        email, source = resolve_agency_email(name, location, incident=incident)
        existing_general.add(name)
        TargetAgency.objects.create(
            incident=incident, name=name, email=email, source=source, order=order,
        )
        order += 1
