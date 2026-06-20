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
# Amendment normalization — maps loose AI values to canonical model keys.
# Used both during extraction and when rendering existing data that may have
# been stored with older, looser values.
# ---------------------------------------------------------------------------

_VALID_AMENDMENT_KEYS = {
    '1st', '1st_retaliation', '1st_prior_restraint', '1st_viewpoint',
    '4th_search', '4th_seizure', '4th_property', '4th_excessive_force',
    '5th_due_process', '5th_self_incrimination',
    '6th_counsel', '8th_cruel',
    '14th_due_process', '14th_equal_protection', 'other',
}


def normalize_amendment(value):
    """
    Map loose amendment values (e.g. "First", "1st Amendment", "Fourth Amendment —
    Excessive Force") to the canonical keys used by ConstitutionalClaim.AMENDMENT_CHOICES.
    Returns '' if the value is empty, 'other' if it cannot be mapped.
    """
    if not value:
        return ''
    raw = str(value).strip()
    # Already a canonical key
    if raw in _VALID_AMENDMENT_KEYS:
        return raw

    v = raw.lower()

    # First Amendment variants
    if v.startswith('1st') or v.startswith('first') or '1st amendment' in v or 'first amendment' in v:
        if 'retaliat' in v:
            return '1st_retaliation'
        if 'prior restraint' in v or 'prior_restraint' in v:
            return '1st_prior_restraint'
        if 'viewpoint' in v:
            return '1st_viewpoint'
        return '1st'

    # Fourth Amendment variants
    if v.startswith('4th') or v.startswith('fourth') or '4th amendment' in v or 'fourth amendment' in v:
        if 'force' in v:
            return '4th_excessive_force'
        if 'search' in v:
            return '4th_search'
        if 'propert' in v:
            return '4th_property'
        return '4th_seizure'

    # Fifth Amendment variants
    if v.startswith('5th') or v.startswith('fifth'):
        if 'self' in v or 'miranda' in v or 'incriminat' in v:
            return '5th_self_incrimination'
        return '5th_due_process'

    # Sixth / Eighth
    if v.startswith('6th') or v.startswith('sixth'):
        return '6th_counsel'
    if v.startswith('8th') or v.startswith('eighth'):
        return '8th_cruel'

    # Fourteenth Amendment variants
    if v.startswith('14th') or v.startswith('fourteenth'):
        if 'equal' in v:
            return '14th_equal_protection'
        return '14th_due_process'

    return 'other'


# ---------------------------------------------------------------------------
# State normalization — maps full state names ("Florida") to 2-letter codes
# ("FL") so the Step 2 dropdown pre-selects correctly. The dropdown options
# use 2-letter codes as values.
# ---------------------------------------------------------------------------

def normalize_state(value):
    """Convert a state name or code to its 2-letter uppercase code."""
    if not value:
        return ''
    from documents.services.court_lookup_service import CourtLookupService
    s = str(value).strip().upper()
    # Already a 2-letter code
    if len(s) == 2 and s.isalpha():
        return s
    return CourtLookupService.STATE_NAME_TO_CODE.get(s, value)


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
- constitutional_claims[].amendment MUST be one of these exact keys (pick the MOST SPECIFIC):
  1st                  — First Amendment general (speech, assembly, press)
  1st_retaliation      — First Amendment retaliation (use this for arrests/citations after filming police, speaking out, or filing complaints — most auditor cases fall here)
  1st_prior_restraint  — prior restraint (orders to stop speech before it happens)
  1st_viewpoint        — viewpoint discrimination
  4th_search           — unreasonable search
  4th_seizure          — unreasonable seizure of person (arrest or detention without probable cause/reasonable suspicion)
  4th_property         — seizure or destruction of property (phone, camera, belongings)
  4th_excessive_force  — excessive force during seizure/arrest
  5th_due_process      — Fifth Amendment due process (federal actors only)
  5th_self_incrimination — Miranda / compelled statements
  6th_counsel          — right to counsel
  8th_cruel            — cruel and unusual punishment (post-conviction inmates)
  14th_due_process     — Fourteenth Amendment due process (state/local actors — common alongside 4th claims)
  14th_equal_protection — selective enforcement based on race/religion/etc
  other                — anything else
  If the story describes being arrested after filming police, include BOTH 1st_retaliation AND 4th_seizure.
  If force was used, also include 4th_excessive_force.
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
    if p.get('state'):
        p['state'] = normalize_state(p['state'])
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
        if defaults.get('state'):
            defaults['state'] = normalize_state(defaults['state'])
        defaults['federal_district_court'] = ''
        defaults['court_confirmed'] = False
        # GPT's county guess from the story text alone has no real data
        # behind it and is unreliable, especially for small/obscure towns
        # or when GPT misattributes the state. Trust the static city/state
        # lookup instead — if it can't verify the county, leave the field
        # blank rather than show a confident-looking but unverified guess.
        if defaults.get('city') and defaults.get('state'):
            from documents.services.county_lookup_service import CountyLookupService
            defaults['county'] = CountyLookupService.lookup_county(defaults['city'], defaults['state']) or ''
        else:
            defaults['county'] = ''
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

    # Step 4 — ConstitutionalClaims (clear old, re-insert).
    # Normalize amendment values so stored keys match AMENDMENT_CHOICES; dedupe
    # on (doc, amendment) since ConstitutionalClaim has a unique_together constraint.
    ConstitutionalClaim.objects.filter(document=doc).delete()
    seen_amendments = set()
    for claim in (ai_analysis.get('constitutional_claims') or []):
        data = {k: v for k, v in claim.items() if v is not None}
        amendment = normalize_amendment(data.get('amendment', ''))
        if not amendment or amendment in seen_amendments:
            continue
        data['amendment'] = amendment
        seen_amendments.add(amendment)
        ConstitutionalClaim.objects.create(document=doc, **data)

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
