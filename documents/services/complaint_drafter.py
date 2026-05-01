"""
documents/services/complaint_drafter.py

GPT-4 service that turns a user's raw story + structured wizard data into a
list of numbered first-person factual allegations for a §1983 complaint.

This is the ONLY AI surface in PDF generation. Everything else (caption,
jurisdiction, count headings, prayer for relief, signature, case law) is
deterministic Django templating.

Usage:
    from documents.services.complaint_drafter import generate_factual_allegations

    paragraphs, error = generate_factual_allegations(document)
    # paragraphs: list[str] of numbered allegations in chronological order
    # error: None on success, str on failure

The service does NOT save — the caller is responsible for persisting the
returned paragraphs to Document.factual_allegations_json.
"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You draft the FACTUAL ALLEGATIONS section of a federal §1983 civil rights
complaint for a pro se plaintiff. The plaintiff is not a lawyer. Your job is
to turn their story into clear, numbered, first-person factual paragraphs
suitable for the body of a federal complaint.

VOICE RULES (these are non-negotiable):
- First person ("I"), past tense.
- Plain English. No Latin, no Bluebook signals, no Bluebook abbreviations.
- One discrete fact per paragraph. Short sentences are good.
- Chronological order. Use approximate times when the user gave them.
- Use the defendants' names verbatim from the structured data. If the story
  references an officer not in the defendants list, use generic phrasing
  like "an officer".
- Quote the plaintiff's own words when they captured something the officer
  said ("Officer Smith said, 'Stop filming.'").

WHAT YOU MUST NOT DO:
- Do not add facts that are not in the story or the structured data. If a
  detail is unclear, leave it out — never guess, never embellish.
- Do not characterize conduct legally. Say what happened, not "unlawfully
  arrested" or "in violation of the First Amendment". Legal characterization
  belongs in the count headings, not the factual allegations.
- Do not cite cases, statutes, or constitutional provisions in this section.
- Do not summarize damages, relief, or evidence — those have their own
  sections in the complaint.

OUTPUT FORMAT:
Return ONLY a JSON object with this exact shape:

{"paragraphs": ["...", "...", "..."]}

Each string is one numbered allegation. Do NOT include the leading number —
it will be added at render time. Aim for 8–25 paragraphs depending on the
complexity of the story.
"""


def generate_factual_allegations(document):
    """
    Call GPT to generate numbered factual-allegation paragraphs.
    Returns (paragraphs_list, error_str). One of the two is always None.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        return None, 'OPENAI_API_KEY is not configured.'

    session = getattr(document, 'wizard_session', None)
    story = (session.story_text if session else '') or ''
    if not story.strip():
        return None, 'No story text on file. Go back to the story step and add details.'

    user_message = _build_user_message(document, story)

    raw_text, error = _call_openai(api_key, SYSTEM_PROMPT, user_message)
    if error:
        return None, f'AI request failed: {error}'

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.exception('Could not parse complaint drafter JSON')
        return None, f'Could not parse AI response: {exc}'

    paragraphs = data.get('paragraphs') or []
    if not isinstance(paragraphs, list):
        return None, 'AI response did not contain a paragraphs list.'

    cleaned = [str(p).strip() for p in paragraphs if str(p).strip()]
    if not cleaned:
        return None, 'AI returned an empty draft. Try adding more detail to your story.'

    return cleaned, None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_user_message(document, story):
    """
    Build the structured-fact context the AI gets, plus the raw story.
    """
    incident = getattr(document, 'incident_overview', None)
    defendants = list(document.defendants.all())
    plaintiff = getattr(document, 'plaintiff_info', None)

    lines = ['STRUCTURED FACTS (use these verbatim — do not invent more):', '']

    if plaintiff:
        plaintiff_name = (plaintiff.full_name or '').strip()
        if plaintiff_name:
            lines.append(f'Plaintiff: {plaintiff_name} (refer to them as "I").')

    if incident:
        if incident.incident_date:
            time_part = f' at approximately {incident.incident_time}' if incident.incident_time else ''
            lines.append(f'Date/time: {incident.incident_date}{time_part}.')
        loc_bits = [
            getattr(incident, 'address', '') or '',
            getattr(incident, 'city', '') or '',
            getattr(incident, 'state', '') or '',
        ]
        loc = ', '.join([b for b in loc_bits if b])
        if loc:
            lines.append(f'Location: {loc}.')
        if getattr(incident, 'location_description', ''):
            lines.append(f'Location description: {incident.location_description}.')
        if getattr(incident, 'plaintiff_activity', ''):
            lines.append(f'What plaintiff was doing: {incident.plaintiff_activity}.')
        if getattr(incident, 'force_used', None):
            lines.append('Force was used by officers.')
        if getattr(incident, 'equipment_seized_or_damaged', None):
            lines.append('Plaintiff\'s equipment was seized or damaged.')

    if defendants:
        lines.append('')
        lines.append('Defendants (use these names exactly):')
        for d in defendants:
            name = (d.full_name or '').strip() or 'Unknown officer'
            agency = (d.agency_name or '').strip()
            badge = (d.badge_number or '').strip()
            extras = []
            if d.rank_title:
                extras.append(d.rank_title)
            if badge:
                extras.append(f'Badge #{badge}')
            if agency:
                extras.append(agency)
            extra_str = f' ({", ".join(extras)})' if extras else ''
            lines.append(f'- {name}{extra_str}')

    lines.append('')
    lines.append('PLAINTIFF\'S STORY (the source of truth — do not add facts beyond this):')
    lines.append('')
    lines.append(story.strip())

    return '\n'.join(lines)


def _call_openai(api_key, system_prompt, user_message):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message},
            ],
            temperature=0.2,
            response_format={'type': 'json_object'},
        )
        return response.choices[0].message.content, None
    except Exception as exc:
        logger.exception('OpenAI complaint drafter call failed')
        return None, str(exc)
