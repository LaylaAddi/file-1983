"""
Per-document AI quota enforcement.

Limit depends on payment status:
  - draft  -> AI_QUOTA_FREE  (default 3 calls)
  - paid   -> AI_QUOTA_PAID  (default 150 calls). Counter resets on payment.
  - finalized / locked -> always blocked

Counted call types: story extraction, draft regeneration, addendums.
Court lookup fallback (small, automatic) is intentionally NOT counted.

A short per-document cooldown (AI_CALL_COOLDOWN_SECONDS) also guards against
a user mashing Analyze/Re-draft/Add repeatedly — each click is a real OpenAI
API call, so without this a fast clicker could burn through their quota (or
just rack up API cost while under quota) in a couple of seconds.
"""
from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.db.models import F

from documents.models import Document

AI_CALL_COOLDOWN_SECONDS = getattr(settings, 'AI_CALL_COOLDOWN_SECONDS', 8)


class QuotaExceeded(Exception):
    """Raised when an AI call would exceed the per-document limit."""

    def __init__(self, document: Document, message: str = ''):
        self.document = document
        self.state = document.ai_quota_state()
        super().__init__(message or f'AI quota exhausted ({self.state["used"]}/{self.state["limit"]}).')


class AICallTooSoon(Exception):
    """Raised when a document made an AI call within the cooldown window."""

    def __init__(self, document: Document, retry_after: int = AI_CALL_COOLDOWN_SECONDS):
        self.document = document
        self.retry_after = retry_after
        super().__init__(f'AI call cooldown active — retry in {retry_after}s.')


def _cooldown_key(document: Document) -> str:
    return f'ai-call-cooldown:{document.pk}'


def can_use_ai(document: Document) -> bool:
    """Quick check — true if a fresh AI call is allowed right now."""
    if document.is_locked():
        return False
    if cache.get(_cooldown_key(document)):
        return False
    return document.ai_calls_used < document.ai_quota_limit()


def consume_ai_call(document: Document) -> None:
    """
    Atomically reserve one AI call. Raises QuotaExceeded if not allowed, or
    AICallTooSoon if the document is still in its post-call cooldown window.
    Refresh the in-memory counter so callers see the new value.
    """
    if document.is_locked():
        raise QuotaExceeded(document, 'Document is locked — AI calls disabled.')

    if cache.get(_cooldown_key(document)):
        raise AICallTooSoon(document)

    if document.ai_calls_used >= document.ai_quota_limit():
        raise QuotaExceeded(document)

    Document.objects.filter(pk=document.pk).update(ai_calls_used=F('ai_calls_used') + 1)
    document.refresh_from_db(fields=['ai_calls_used'])
    cache.set(_cooldown_key(document), True, AI_CALL_COOLDOWN_SECONDS)


def upgrade_message(document: Document) -> str:
    """User-facing message when quota is exhausted."""
    state = document.ai_quota_state()
    if state['is_paid']:
        return (
            f'You\'ve reached the {state["limit"]}-call AI editing limit for this document. '
            'Finalize & download to use it, or contact support if you need more.'
        )
    return (
        f'You\'ve used all {state["limit"]} free AI calls for this document. '
        'Pay $149 to unlock 150 more AI edits and remove the watermark.'
    )
