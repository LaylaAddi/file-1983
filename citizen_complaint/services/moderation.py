"""
Safety gate — checks a complaint body for threats/violence/harassment via
OpenAI's Moderation API immediately before send. This is a safety check, not
a cost-control feature, so two rules that differ from the rest of this app's
AI calls:

  - It is NEVER gated by the per-incident AI/API quota (services.api_quota).
    Letting a quota-exhausted incident skip moderation would turn "burn your
    quota on purpose" into a way to bypass the safety check.
  - It fails CLOSED. If the moderation call itself errors out (missing key,
    OpenAI outage, network failure), the send is blocked rather than let
    through unchecked. OPENAI_API_KEY is already required for drafting, so
    this doesn't introduce a new single point of failure — it's consistent
    with one that already exists.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def check_content(text: str) -> tuple[bool, list, str]:
    """
    Returns (flagged, categories, error).
      flagged=True  -> do not send.
      categories    -> which OpenAI moderation categories tripped (for admin/audit).
      error         -> non-empty if the check itself failed (also treated as flagged
                       by the caller, since we fail closed).
    """
    if not text or not text.strip():
        return False, [], ''

    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        logger.error('OPENAI_API_KEY not configured — content moderation cannot run.')
        return True, [], 'Moderation is not configured.'

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.moderations.create(model='omni-moderation-latest', input=text)
        result = response.results[0]
        categories = [name for name, is_flagged in result.categories.model_dump().items() if is_flagged]
        return bool(result.flagged), categories, ''
    except Exception as exc:
        logger.exception('OpenAI moderation call failed')
        return True, [], str(exc)
