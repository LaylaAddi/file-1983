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

# Deliberately NOT the full set of categories OpenAI's `result.flagged` boolean
# considers. This app exists to describe violent/abusive government conduct —
# a legitimate complaint about excessive force will almost always trip the
# plain `violence` / `violence_graphic` categories just by describing what
# happened to the complainant. Blocking on those would break the feature for
# nearly every real complaint. We only block on categories that represent the
# SENDER threatening/targeting someone or otherwise-universally-inappropriate
# content that has no legitimate place in a complaint email — not a victim's
# factual account of violence they experienced.
BLOCKING_CATEGORIES = {
    'harassment_threatening',   # the actual "sending threats" signal the gate exists for
    'hate_threatening',
    'illicit_violent',          # instructions/advice for violent wrongdoing, not a victim account
    'self_harm',
    'self_harm_intent',
    'self_harm_instructions',
    'sexual_minors',
}


def check_content(text: str) -> tuple[bool, list, str]:
    """
    Returns (flagged, categories, error).
      flagged=True  -> do not send. Only True when a BLOCKING_CATEGORIES entry
                       tripped, not OpenAI's raw `flagged` (see module note).
      categories    -> ALL moderation categories that tripped, for admin/audit —
                       may include non-blocking ones like `violence` even when
                       flagged=False, so admins can still see it was noted.
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
        flagged = any(cat in BLOCKING_CATEGORIES for cat in categories)
        return flagged, categories, ''
    except Exception as exc:
        logger.exception('OpenAI moderation call failed')
        return True, [], str(exc)
