"""
Step 2 — Agency identification.

resolve_agency_email(name, location) is called once per agency detected in
Step 1 (and again if the user manually types a name with no email on the
agencies-review page). Order of trust, cheapest/most-reliable first:

  1. Curated Agency DB (admin-managed — same trust model as documents.CaseLaw)
  2. SerpApi (Google-engine web search) + an AI pass over the snippets to
     propose an email. (Google's own Custom Search API can no longer search
     the open web for newly-created engines as of Jan 2026, and Bing's
     Search API was fully retired in Aug 2025 — SerpApi is the option that's
     actually available for this.)
  3. Give up — return blank, user must type the email themselves

Every proposed address is marked non-`db_match`, and the UI (agencies-review
page) never lets an unconfirmed address auto-send — the user always sees and
confirms every recipient, per the app's core constraint.
"""
from __future__ import annotations

import json
import logging

import requests
from django.conf import settings

from citizen_complaint.models import Agency
from citizen_complaint.services import api_quota

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15


def _match_curated_db(name: str, location: str):
    qs = Agency.objects.filter(is_active=True)
    # Exact-ish name match first
    match = qs.filter(name__iexact=name).first()
    if match:
        return match
    match = qs.filter(name__icontains=name).first()
    if match:
        return match
    if location:
        match = qs.filter(name__icontains=name.split()[0], jurisdiction__icontains=location).first()
        if match:
            return match
    return None


def _serpapi_search(query: str) -> tuple[list, str | None]:
    api_key = getattr(settings, 'SERPAPI_API_KEY', '')
    if not api_key:
        return [], 'SerpApi not configured.'
    try:
        resp = requests.get(
            'https://serpapi.com/search',
            params={'engine': 'google', 'q': query, 'api_key': api_key, 'num': 5},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        # organic_results entries carry the same title/link/snippet shape
        # _ai_pick_email already expects (previously fed by Google Custom Search).
        return data.get('organic_results', []) or [], None
    except requests.RequestException as exc:
        logger.exception('SerpApi search call failed')
        return [], str(exc)


def _ai_pick_email(agency_name: str, search_results: list) -> tuple[str, str | None]:
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key or not search_results:
        return '', 'No search results to analyze.'

    snippets = '\n'.join(
        f'- {r.get("title", "")}: {r.get("snippet", "")} ({r.get("link", "")})'
        for r in search_results
    )
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': (
                    'You identify the best official contact/complaint email address for a '
                    'government agency from web search snippets. If no email address appears '
                    'anywhere in the snippets, return an empty string — never invent one. '
                    'Return ONLY JSON: {"email": "..."} (empty string if none found).'
                )},
                {'role': 'user', 'content': f'Agency: {agency_name}\n\nSearch results:\n{snippets}'},
            ],
            temperature=0,
            response_format={'type': 'json_object'},
        )
        data = json.loads(response.choices[0].message.content)
        return data.get('email', ''), None
    except Exception as exc:
        logger.exception('AI email-pick call failed')
        return '', str(exc)


def resolve_agency_email(name: str, location: str = '', incident=None) -> tuple[str, str]:
    """
    Returns (email, source). source is one of TargetAgency.SOURCE_CHOICES keys.
    Never raises — quota/lookup failures just fall back to a blank email that
    the user fills in manually on the agencies-review page.
    """
    match = _match_curated_db(name, location)
    if match:
        return match.complaint_email, 'db_match'

    if incident is not None:
        try:
            api_quota.consume_call(incident)
        except (api_quota.QuotaExceeded, api_quota.AICallTooSoon):
            return '', 'detected'

    query = f'"{name}" {location} official complaint email contact'.strip()
    results, search_error = _serpapi_search(query)
    if search_error or not results:
        return '', 'detected'

    email, ai_error = _ai_pick_email(name, results)
    if email:
        return email, 'ai_lookup'
    return '', 'detected'
