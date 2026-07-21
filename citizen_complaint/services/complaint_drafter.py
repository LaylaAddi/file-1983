"""
Step 4 — Complaint generation.

generate_draft(incident, target_agency) -> (body_text, error)

One draft per selected agency, tailored to that agency's role_description
(e.g. a library gets a venue/policy-violation framing, a police department
gets an unlawful-detention framing). Higher temperature + the user's
optional personal note are used deliberately so drafts vary person-to-person
instead of reading like an identical form letter (a known trigger for spam
filters when many people file about the same viral video).
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You draft a factual complaint email from a private citizen to a government \
agency, based on a video the citizen recorded/witnessed. The citizen is not \
a lawyer and is not making a legal filing — this is a complaint requesting \
review and a response, not a lawsuit.

VOICE RULES:
- First-person citizen voice, factual and respectful, not hostile.
- Cite the video link as the source of the events described.
- Reference the specific agency's role (given below) — tailor the framing \
to what THIS agency is responsible for, not a generic complaint.
- Request that the agency review the matter and respond.
- Do NOT state legal conclusions as fact (no "this violated my rights", no \
"this was illegal" — describe the conduct and let the agency draw conclusions).
- Do NOT invent facts beyond what's given in the incident summary/transcript.
- Weave in the citizen's personal note naturally if one is provided, so the \
letter reads like it was written by a specific person, not a form template.
- Sign off using the identification the citizen chose (full name, first \
name only, or "a concerned citizen") — never guess or embellish who they are.
- Plain English, no legal jargon, no citations to statutes or case law.

OUTPUT: Return ONLY the email body text (no subject line, no JSON, no \
markdown formatting) — plain text ready to send, starting with a greeting \
and ending with the citizen's chosen sign-off."""


def _build_user_message(incident, target_agency):
    lines = [
        f'Agency being contacted: {target_agency.name}',
        f'Agency\'s role in this incident: {target_agency.role_description or "Not specified — use best judgment from the summary."}',
        f'Video link: {incident.video_url}',
        f'Video title: {incident.video_title}',
        f'Incident summary: {incident.extracted_data.get("summary", "")}',
        f'Location: {incident.extracted_data.get("location", "") or f"{incident.user_city}, {incident.user_state}".strip(", ")}',
        f'Incident date (if known): {incident.extracted_data.get("incident_date", "")}',
        f'Tone requested: {incident.get_tone_display()}',
        f'Citizen sign-off: {incident.display_name()}',
    ]
    if incident.personal_note:
        lines.append(f'Personal note from the citizen to weave in naturally: {incident.personal_note}')
    if incident.privacy_level == 'anonymous':
        lines.append('The citizen wishes to remain anonymous — do not include their name anywhere.')
    return '\n'.join(lines)


def generate_draft(incident, target_agency) -> tuple[str, str]:
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        return '', 'OPENAI_API_KEY is not configured.'

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': _build_user_message(incident, target_agency)},
            ],
            # Higher than the deterministic-extraction calls elsewhere in this
            # app — deliberate, so many citizens filing about the same viral
            # video don't all produce near-identical text.
            temperature=0.8,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as exc:
        logger.exception('Complaint draft generation failed')
        return '', str(exc)
