"""
Per-document AI quota enforcement.

Limit depends on payment status:
  - draft  -> AI_QUOTA_FREE  (default 3 calls)
  - paid   -> AI_QUOTA_PAID  (default 150 calls). Counter resets on payment.
  - finalized / locked -> always blocked

Counted call types: story extraction, draft regeneration, addendums.
Court lookup fallback (small, automatic) is intentionally NOT counted.
"""
from __future__ import annotations

from django.db.models import F

from documents.models import Document


class QuotaExceeded(Exception):
    """Raised when an AI call would exceed the per-document limit."""

    def __init__(self, document: Document, message: str = ''):
        self.document = document
        self.state = document.ai_quota_state()
        super().__init__(message or f'AI quota exhausted ({self.state["used"]}/{self.state["limit"]}).')


def can_use_ai(document: Document) -> bool:
    """Quick check — true if a fresh AI call is allowed right now."""
    if document.is_locked():
        return False
    return document.ai_calls_used < document.ai_quota_limit()


def consume_ai_call(document: Document) -> None:
    """
    Atomically reserve one AI call. Raises QuotaExceeded if not allowed.
    Refresh the in-memory counter so callers see the new value.
    """
    if document.is_locked():
        raise QuotaExceeded(document, 'Document is locked — AI calls disabled.')

    if document.ai_calls_used >= document.ai_quota_limit():
        raise QuotaExceeded(document)

    Document.objects.filter(pk=document.pk).update(ai_calls_used=F('ai_calls_used') + 1)
    document.refresh_from_db(fields=['ai_calls_used'])


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
