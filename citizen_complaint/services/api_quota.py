"""
Per-incident AI/API quota + cooldown enforcement — the free-tier equivalent
of documents/services/ai_quota.py. This feature has no paid tier to reset
the counter, so the cap is flat: once an incident hits it, it's done
consuming external calls (transcript fetch, metadata fetch, GPT extraction,
agency search, per-agency drafts) — the user can still view/edit/send what
was already produced.

Two entry points, not one, because a single user action can legitimately
fan out into several external calls in one request (video intake alone is
metadata + transcript + extraction + a search per detected agency):

  consume_call()          — budget-only. Use for every call inside a chain
                             that was already triggered by one user action
                             (intake pipeline, initial per-agency drafting).
  consume_call_throttled() — budget + cooldown. Use only at the entry point
                             of something a user could rapidly re-click
                             (e.g. the "Regenerate this draft" button), so
                             mashing it can't fire a burst of paid calls.
"""
from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db.models import F

from citizen_complaint.models import Incident


def _cooldown_seconds() -> int:
    return getattr(settings, 'CITIZEN_COMPLAINT_AI_CALL_COOLDOWN_SECONDS', 10)


class QuotaExceeded(Exception):
    def __init__(self, incident: Incident, message: str = ''):
        self.incident = incident
        super().__init__(
            message or f'AI/API quota exhausted for this incident '
                       f'({incident.api_calls_used}/{incident.api_quota_limit()}).'
        )


class AICallTooSoon(Exception):
    def __init__(self, incident: Incident, retry_after: int = None):
        self.incident = incident
        self.retry_after = retry_after if retry_after is not None else _cooldown_seconds()
        super().__init__(f'AI call cooldown active — retry in {self.retry_after}s.')


def _cooldown_key(incident: Incident) -> str:
    return f'citizen-complaint-cooldown:{incident.pk}'


def can_use_ai(incident: Incident) -> bool:
    if cache.get(_cooldown_key(incident)):
        return False
    return incident.api_calls_used < incident.api_quota_limit()


def consume_call(incident: Incident) -> None:
    """Reserve one AI/API call against the budget. Raises QuotaExceeded if
    the incident is out of quota. Does NOT check/set the cooldown — safe to
    call multiple times in a row within one already-user-triggered pipeline."""
    if incident.api_calls_used >= incident.api_quota_limit():
        raise QuotaExceeded(incident)

    Incident.objects.filter(pk=incident.pk).update(api_calls_used=F('api_calls_used') + 1)
    incident.refresh_from_db(fields=['api_calls_used'])


def consume_call_throttled(incident: Incident) -> None:
    """Like consume_call, but also enforces the cooldown. Use at the entry
    point of an action a user could rapidly re-trigger by clicking again."""
    if cache.get(_cooldown_key(incident)):
        raise AICallTooSoon(incident)
    consume_call(incident)
    cache.set(_cooldown_key(incident), True, _cooldown_seconds())


def upgrade_message(incident: Incident) -> str:
    return (
        f'This incident has used all {incident.api_quota_limit()} AI/API calls available '
        'for the Citizen Complaint Assistant. You can still review, edit, and send what\'s '
        'already been drafted — start a new incident for a different video.'
    )
