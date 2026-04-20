"""
documents/services/openai_service.py

GPT-4 story extraction service for the Section 1983 wizard.

Usage (from view):
    from documents.services.openai_service import extract_story

    result = extract_story(session)          # saves to DB, returns (ai_analysis_dict, error_str)
    result = extract_story(session, dry_run=True)  # returns same but does NOT save anything

The service:
1. Loads the active 'story_parse' AIPrompt from DB (falls back to hardcoded default).
2. Calls GPT-4o with the story text.
3. Parses the JSON response.
4. If dry_run=False, populates all wizard-step models via update_or_create.
5. Returns (parsed_dict, None) on success or (None, error_message) on failure.
"""

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default system prompt (used if no active AIPrompt row exists in DB)
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """
You are a legal document assistant helping build a Section 1983 civil rights complaint.

Your job is to extract structured information from the user's narrative and return it as a
single valid JSON object — no prose, no markdown, no code fences, just raw JSON.

Rules:
- Use null for any field not explicitly mentioned in the story.
- Do NOT invent or infer details that are not present in the story.
- For constitutional_claims, identify which amendments were likely violated based on the facts.
  Common choices: "First", "Fourth", "Fifth", "Eighth", "Fourteenth".
- For the timeline, break events into discrete chronological steps with one action per entry.
- incident.location_type choices: public_sidewalk, public_park, public_plaza,
  public_parking_lot, roadway, traffic_stop, police_station, sheriff_office,
  courthouse, city_hall, county_building, federal_building, dmv, post_office,
  government_office, public_school, public_library, public_hospital, jail,
  prison, airport, transit_station, transit_vehicle, personal_vehicle,
  private_residence, private_business, other.
- defendants[].capacity_sued choices: individual, official, both.
- evidence[].evidence_type choices: video, photo, document, audio, physical, other.
- witnesses[].relationship_to_plaintiff choices: bystander, friend, family, co-plaintiff, other.

Return ONLY the JSON object matching this exact schema:

{
  "document": {"title": str, "jury_trial_demand": bool},
  "plaintiff": {
    "full_name": str, "address": str, "city": str, "state": str,
    "zip_code": str, "phone": str, "email": str,
    "filing_pro_se": bool,
    "attorney_name": str, "attorney_bar_number": str, "attorney_address": str
  },
  "incident": {
    "incident_date": "YYYY-MM-DD", "incident_time": "HH:MM",
    "address": str, "city": str, "state": str, "county": str,
    "location_description": str, "location_type": str,
    "is_public_forum": bool,
    "plaintiff_activity": str,
    "plaintiff_identified_themselves": bool, "identification_description": str,
    "force_used": bool, "equipment_seized_or_damaged": bool,
    "federal_district_court": str
  },
  "timeline": [
    {"order": int, "time_approximate": str, "actor": str, "action_description": str}
  ],
  "defendants": [
    {
      "full_name": str, "badge_number": str, "rank_title": str,
      "agency_name": str, "parent_government_entity": str, "agency_address": str,
      "capacity_sued": str, "acting_under_color_of_law": bool,
      "color_of_law_basis": str, "is_supervisor": bool
    }
  ],
  "government_entity": {
    "entity_name": str, "entity_address": str,
    "policy_or_custom_description": str
  },
  "constitutional_claims": [
    {"amendment": str, "how_violated": str}
  ],
  "evidence": [
    {
      "evidence_type": str, "description": str,
      "date_and_time": str, "recorded_by": str,
      "storage_location": str, "public_url": str,
      "defendant_aware_of_recording": bool
    }
  ],
  "witnesses": [
    {
      "full_name": str, "contact_info": str, "relationship_to_plaintiff": str,
      "what_they_witnessed": str, "has_video": bool, "willing_to_testify": bool
    }
  ],
  "damages": {
    "physical_injury_description": str, "emotional_distress_description": str,
    "lost_wages": str, "property_damage_amount": str, "punitive_basis": str
  },
  "relief": {
    "compensatory_damages": bool, "compensatory_amount": str,
    "punitive_damages": bool, "declaratory_judgment": bool,
    "injunctive_relief": bool, "attorney_fees": bool,
    "costs_of_suit": bool, "other_relief": str
  },
  "prior_complaints": {
    "filed_complaints": bool, "description": str, "outcomes": str
  }
}
""".strip()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_story(session, dry_run=False):
    """
    Extract structured data from session.story_text using GPT.

    Args:
        session:   WizardSession instance with .story_text populated.
        dry_run:   If True, returns parsed JSON but does NOT write to DB.

    Returns:
        (ai_analysis dict, None)   on success
        (None, error_string)       on failure
    """
    if not session.story_text:
        return None, 'No story text to analyze.'

    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        return None, 'OPENAI_API_KEY is not configured.'

    # Load prompt from DB; fall back to hardcoded default
    system_prompt, user_template = _load_prompt()

    user_message = user_template.format(story=session.story_text)

    # Call GPT
    raw_response, call_error = _call_openai(api_key, system_prompt, user_message)
    if call_error:
        if not dry_run:
            session.ai_extraction_attempted = True
            session.ai_extraction_succeeded = False
            session.ai_extraction_error = call_error
            session.save(update_fields=[
                'ai_extraction_attempted', 'ai_extraction_succeeded', 'ai_extraction_error', 'updated_at'
            ])
        return None, call_error

    # Parse JSON
    ai_analysis, parse_error = _parse_json(raw_response)
    if parse_error:
        if not dry_run:
            session.ai_extraction_attempted = True
            session.ai_extraction_succeeded = False
            session.ai_extraction_error = f'JSON parse error: {parse_error}\n\nRaw: {raw_response[:500]}'
            session.save(update_fields=[
                'ai_extraction_attempted', 'ai_extraction_succeeded', 'ai_extraction_error', 'updated_at'
            ])
        return None, parse_error

    if dry_run:
        return ai_analysis, None

    # Save to DB
    _populate_models(session, ai_analysis)

    session.ai_analysis = ai_analysis
    session.ai_extraction_attempted = True
    session.ai_extraction_succeeded = True
    session.ai_extraction_error = ''
    session.status = 'analyzed'
    session.current_step = 1
    session.save(update_fields=[
        'ai_analysis', 'ai_extraction_attempted', 'ai_extraction_succeeded',
        'ai_extraction_error', 'status', 'current_step', 'updated_at'
    ])

    return ai_analysis, None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_prompt():
    """Return (system_prompt, user_prompt_template). Falls back to hardcoded defaults."""
    try:
        from documents.models import AIPrompt
        prompt_obj = AIPrompt.objects.filter(task_name='story_parse', is_active=True).first()
        if prompt_obj:
            return prompt_obj.system_prompt, prompt_obj.user_prompt_template
    except Exception:
        pass

    default_user_template = (
        "Here is the user's story. Extract all available information and return only JSON:\n\n{story}"
    )
    return DEFAULT_SYSTEM_PROMPT, default_user_template


def _call_openai(api_key, system_prompt, user_message):
    """
    Call OpenAI chat completions. Returns (raw_text, error) tuple.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message},
            ],
            temperature=0.1,
            response_format={'type': 'json_object'},
        )
        content = response.choices[0].message.content
        return content, None
    except Exception as exc:
        logger.exception('OpenAI API call failed')
        return None, str(exc)


def _parse_json(raw_text):
    """Parse GPT response as JSON. Returns (dict, error)."""
    try:
        data = json.loads(raw_text)
        return data, None
    except json.JSONDecodeError as exc:
        return None, f'Could not parse JSON: {exc}'


def _populate_models(session, ai_analysis):
    """Write extracted data into all wizard-step Django models."""
    from documents.models import (
        PlaintiffInfo, IncidentOverview, TimelineEntry,
        Defendant, GovernmentEntity, ConstitutionalClaim,
        Evidence, Witness, Damages, ReliefSought, PriorComplaints,
    )
    doc = session.document

    # Document-level fields
    doc_data = ai_analysis.get('document') or {}
    if doc_data.get('title'):
        doc.title = doc_data['title']
    if doc_data.get('jury_trial_demand') is not None:
        doc.jury_trial_demand = doc_data['jury_trial_demand']
    doc.save(update_fields=['title', 'jury_trial_demand'])

    # Step 1 — PlaintiffInfo (only overwrite fields GPT found; keep profile defaults)
    p = ai_analysis.get('plaintiff') or {}
    pi, _ = PlaintiffInfo.objects.get_or_create(document=doc)
    for field in ['full_name', 'address', 'city', 'state', 'zip_code', 'phone', 'email',
                  'attorney_name', 'attorney_bar_number', 'attorney_address']:
        if p.get(field):
            setattr(pi, field, p[field])
    if p.get('filing_pro_se') is not None:
        pi.filing_pro_se = p['filing_pro_se']
    pi.save()

    # Step 2a — IncidentOverview
    # Always reset court fields so step 1 re-runs the lookup for the new city/state
    inc = ai_analysis.get('incident') or {}
    if inc:
        defaults = {k: v for k, v in inc.items() if v is not None}
        defaults['federal_district_court'] = ''
        defaults['court_confirmed'] = False
        IncidentOverview.objects.update_or_create(
            document=doc,
            defaults=defaults,
        )

    # Step 2b — TimelineEntry (clear old, re-insert)
    TimelineEntry.objects.filter(document=doc).delete()
    for entry in (ai_analysis.get('timeline') or []):
        TimelineEntry.objects.create(document=doc, **{k: v for k, v in entry.items() if v is not None})

    # Step 3a — Defendants (clear old, re-insert)
    Defendant.objects.filter(document=doc).delete()
    for d in (ai_analysis.get('defendants') or []):
        Defendant.objects.create(document=doc, **{k: v for k, v in d.items() if v is not None})

    # Step 3b — GovernmentEntity
    ge = ai_analysis.get('government_entity') or {}
    if ge:
        GovernmentEntity.objects.update_or_create(
            document=doc,
            defaults={k: v for k, v in ge.items() if v is not None},
        )

    # Step 4 — ConstitutionalClaims (clear old, re-insert)
    ConstitutionalClaim.objects.filter(document=doc).delete()
    for claim in (ai_analysis.get('constitutional_claims') or []):
        ConstitutionalClaim.objects.create(document=doc, **{k: v for k, v in claim.items() if v is not None})

    # Step 5a — Evidence (clear old, re-insert)
    Evidence.objects.filter(document=doc).delete()
    for ev in (ai_analysis.get('evidence') or []):
        Evidence.objects.create(document=doc, **{k: v for k, v in ev.items() if v is not None})

    # Step 5b — Witnesses (clear old, re-insert)
    Witness.objects.filter(document=doc).delete()
    for w in (ai_analysis.get('witnesses') or []):
        Witness.objects.create(document=doc, **{k: v for k, v in w.items() if v is not None})

    # Step 6a — Damages
    dmg = ai_analysis.get('damages') or {}
    if dmg:
        Damages.objects.update_or_create(
            document=doc,
            defaults={k: v for k, v in dmg.items() if v is not None},
        )

    # Step 6b — PriorComplaints
    prior = ai_analysis.get('prior_complaints') or {}
    if prior:
        PriorComplaints.objects.update_or_create(
            document=doc,
            defaults={k: v for k, v in prior.items() if v is not None},
        )

    # Step 6c — ReliefSought
    relief = ai_analysis.get('relief') or {}
    if relief:
        ReliefSought.objects.update_or_create(
            document=doc,
            defaults={k: v for k, v in relief.items() if v is not None},
        )
