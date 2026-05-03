"""
documents/services/addendum_service.py

Story addendums — targeted, post-extraction additions.

After the initial story is analyzed, the user may want to add details about a
specific category (officers, evidence, location, damages, etc.) without
re-running the full extraction and risking losing edits they've already made.

Usage (from view):
    from documents.services.addendum_service import apply_addendum, ADDENDUM_CATEGORIES

    result, error = apply_addendum(session, 'defendants', "The other officer was
        Sergeant Smith, badge 4892, also Tampa PD.")

The service:
1. Snapshots the relevant category from the user's CURRENT model data
   (NOT from the original ai_analysis JSON — the user may have edited fields).
2. Sends GPT a category-scoped prompt: existing snapshot + addendum text.
3. Parses GPT's merged JSON back.
4. Merges into the related models NON-destructively:
   - OneToOne models: update fields where GPT returned a non-null value.
   - List models: match by key field; update if matched, create if new.
   - Existing rows are NEVER deleted.
5. Appends the snippet to WizardSession.story_addendums for audit.
6. Mirrors the merged data back into WizardSession.ai_analysis so future
   addendums see the latest snapshot.
"""

import json
import logging
from datetime import datetime, timezone

from django.conf import settings

from documents.services.openai_service import normalize_amendment, normalize_state

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category registry — drives the UI, the GPT prompt, and the merge logic
# ---------------------------------------------------------------------------

ADDENDUM_CATEGORIES = {
    'incident': {
        'label': 'Incident location & details',
        'icon': 'geo-alt',
        'placeholder': "e.g. It happened on the public sidewalk in front of "
                       "the police station at 1320 Main Street, Tampa FL, "
                       "around 4 PM on March 3, 2024. I was livestreaming.",
        'json_keys': ['incident'],
        'guidance': (
            "Update the 'incident' object. Fields: address, city, state, "
            "county, location_description, location_type, incident_date "
            "(YYYY-MM-DD), incident_time (HH:MM), plaintiff_activity, "
            "plaintiff_identified_themselves, identification_description, "
            "force_used, equipment_seized_or_damaged. Use null for any "
            "field neither in the existing data nor in the addendum."
        ),
    },
    'defendants': {
        'label': 'Officers / defendants',
        'icon': 'person-badge',
        'placeholder': "e.g. The second officer was Sergeant Maria Smith, "
                       "badge 4892, also Tampa PD. She is a supervisor.",
        'json_keys': ['defendants', 'government_entity'],
        'guidance': (
            "Update or extend the 'defendants' array AND the "
            "'government_entity' object. For each defendant: full_name, "
            "badge_number, rank_title, agency_name, parent_government_entity, "
            "agency_address, capacity_sued (individual|official|both), "
            "acting_under_color_of_law (bool), color_of_law_basis, "
            "is_supervisor (bool). When an addendum describes someone the "
            "existing list already names, KEEP that entry's full_name and "
            "fill in or correct other fields. Add new entries for newly "
            "named defendants. For 'government_entity': entity_name, "
            "entity_address, policy_or_custom_description."
        ),
    },
    'claims': {
        'label': 'Constitutional claims',
        'icon': 'shield-check',
        'placeholder': "e.g. They also seized my phone and refused to "
                       "return it for two days — that's a Fourth "
                       "Amendment property seizure.",
        'json_keys': ['constitutional_claims'],
        'guidance': (
            "Update or extend the 'constitutional_claims' array. Each entry: "
            "amendment (one of: 1st, 1st_retaliation, 1st_prior_restraint, "
            "1st_viewpoint, 4th_search, 4th_seizure, 4th_property, "
            "4th_excessive_force, 5th_due_process, 5th_self_incrimination, "
            "6th_counsel, 8th_cruel, 14th_due_process, "
            "14th_equal_protection, other), how_violated. Match by "
            "amendment key (one entry per amendment max)."
        ),
    },
    'evidence': {
        'label': 'Evidence',
        'icon': 'collection-play',
        'placeholder': "e.g. There's a YouTube video at "
                       "https://youtu.be/abc123 — the arrest happens at "
                       "the 4 minute mark. I also have body cam footage "
                       "I requested via FOIA.",
        'json_keys': ['evidence'],
        'guidance': (
            "Update or extend the 'evidence' array. Each entry: "
            "evidence_type (video|photo|police_report|body_cam|"
            "foia_request|citation|medical_record|physical|document|"
            "other), description, date_and_time, recorded_by, "
            "storage_location, public_url, key_timestamp (HH:MM:SS into "
            "the recording for the key moment), "
            "defendant_aware_of_recording. Match by public_url when "
            "set, otherwise by (evidence_type + first 60 chars of "
            "description)."
        ),
    },
    'witnesses': {
        'label': 'Witnesses',
        'icon': 'people',
        'placeholder': "e.g. My friend Carlos Diaz was filming from "
                       "across the street. His phone is 555-1212.",
        'json_keys': ['witnesses'],
        'guidance': (
            "Update or extend the 'witnesses' array. Each entry: "
            "full_name, contact_info, relationship_to_plaintiff "
            "(bystander|friend|family|co-plaintiff|other), "
            "what_they_witnessed, has_video, willing_to_testify. "
            "Match by full_name (case-insensitive)."
        ),
    },
    'damages': {
        'label': 'Damages / how it affected you',
        'icon': 'bandaid',
        'placeholder': "e.g. I sprained my wrist when they cuffed me; "
                       "I missed three shifts at work, about $450 lost. "
                       "Phone screen was cracked, $200 to replace.",
        'json_keys': ['damages'],
        'guidance': (
            "Update the 'damages' object. Fields: "
            "physical_injury_description, emotional_distress_description, "
            "lost_wages (free-text description, e.g. '3 shifts, ~$450'), "
            "property_damage_amount (free-text), punitive_basis."
        ),
    },
    'plaintiff': {
        'label': 'Your contact info',
        'icon': 'person-vcard',
        'placeholder': "e.g. My address is 24 Oak Street, Tampa FL "
                       "33602. Phone 555-0123.",
        'json_keys': ['plaintiff'],
        'guidance': (
            "Update the 'plaintiff' object. Fields: full_name, address, "
            "city, state, zip_code, phone, email, filing_pro_se."
        ),
    },
    'relief': {
        'label': 'Relief / what you want',
        'icon': 'cash-stack',
        'placeholder': "e.g. I want $50,000 in compensatory damages and "
                       "punitive damages too. I also want a court order "
                       "stopping them from doing this again.",
        'json_keys': ['relief'],
        'guidance': (
            "Update the 'relief' object. Fields (booleans unless noted): "
            "compensatory_damages, compensatory_amount (string number, "
            "e.g. '50000'), punitive_damages, declaratory_judgment, "
            "injunctive_relief, attorney_fees, costs_of_suit, "
            "other_relief (free text)."
        ),
    },
    'prior': {
        'label': 'Prior complaints',
        'icon': 'archive',
        'placeholder': "e.g. I filed an Internal Affairs complaint last "
                       "month — IA case #2024-117. They closed it as "
                       "unfounded.",
        'json_keys': ['prior_complaints'],
        'guidance': (
            "Update the 'prior_complaints' object. Fields: "
            "filed_complaints (bool), description, outcomes."
        ),
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_addendum(session, category, addendum_text):
    """
    Apply a category-scoped addendum to an already-analyzed session.

    Returns (merged_data_dict, None) on success or (None, error_string).
    """
    if category not in ADDENDUM_CATEGORIES:
        return None, f'Unknown category: {category}'

    addendum_text = (addendum_text or '').strip()
    if not addendum_text:
        return None, 'Please describe what you want to add.'

    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key:
        return None, 'OPENAI_API_KEY is not configured.'

    cfg = ADDENDUM_CATEGORIES[category]

    existing = _snapshot_category(session, cfg['json_keys'])

    system_prompt = _build_system_prompt(cfg)
    user_message = _build_user_message(existing, addendum_text)

    raw, call_error = _call_openai(api_key, system_prompt, user_message)
    if call_error:
        _record_addendum(session, category, addendum_text, error=call_error)
        return None, call_error

    data, parse_error = _parse_json(raw)
    if parse_error:
        _record_addendum(session, category, addendum_text, error=parse_error)
        return None, parse_error

    _merge_into_models(session, cfg, data)

    # Mirror the merged section into ai_analysis so subsequent addendums see it
    ai = dict(session.ai_analysis or {})
    for key in cfg['json_keys']:
        if key in data:
            ai[key] = data[key]
    session.ai_analysis = ai
    session.save(update_fields=['ai_analysis', 'updated_at'])

    _record_addendum(session, category, addendum_text)
    return data, None


# ---------------------------------------------------------------------------
# Snapshot — pull current model state into the same JSON shape GPT expects
# ---------------------------------------------------------------------------

def _snapshot_category(session, json_keys):
    """Build a JSON snapshot of the requested categories from current models."""
    doc = session.document
    snap = {}
    for key in json_keys:
        if key == 'incident':
            snap['incident'] = _snap_incident(doc)
        elif key == 'plaintiff':
            snap['plaintiff'] = _snap_plaintiff(doc)
        elif key == 'defendants':
            snap['defendants'] = _snap_defendants(doc)
        elif key == 'government_entity':
            snap['government_entity'] = _snap_government_entity(doc)
        elif key == 'constitutional_claims':
            snap['constitutional_claims'] = _snap_claims(doc)
        elif key == 'evidence':
            snap['evidence'] = _snap_evidence(doc)
        elif key == 'witnesses':
            snap['witnesses'] = _snap_witnesses(doc)
        elif key == 'damages':
            snap['damages'] = _snap_damages(doc)
        elif key == 'relief':
            snap['relief'] = _snap_relief(doc)
        elif key == 'prior_complaints':
            snap['prior_complaints'] = _snap_prior(doc)
    return snap


def _snap_incident(doc):
    inc = getattr(doc, 'incident_overview', None)
    if not inc:
        return {}
    return {
        'incident_date': inc.incident_date.isoformat() if inc.incident_date else '',
        'incident_time': inc.incident_time.strftime('%H:%M') if inc.incident_time else '',
        'address': inc.address, 'city': inc.city, 'state': inc.state,
        'county': inc.county, 'location_description': inc.location_description,
        'location_type': inc.location_type,
        'is_public_forum': inc.is_public_forum,
        'plaintiff_activity': inc.plaintiff_activity,
        'plaintiff_identified_themselves': inc.plaintiff_identified_themselves,
        'identification_description': inc.identification_description,
        'force_used': inc.force_used,
        'equipment_seized_or_damaged': inc.equipment_seized_or_damaged,
    }


def _snap_plaintiff(doc):
    p = getattr(doc, 'plaintiff_info', None)
    if not p:
        return {}
    return {
        'full_name': p.full_name, 'address': p.address, 'city': p.city,
        'state': p.state, 'zip_code': p.zip_code, 'phone': p.phone,
        'email': p.email, 'filing_pro_se': p.filing_pro_se,
    }


def _snap_defendants(doc):
    return [{
        'full_name': d.full_name, 'badge_number': d.badge_number,
        'rank_title': d.rank_title, 'agency_name': d.agency_name,
        'parent_government_entity': d.parent_government_entity,
        'agency_address': d.agency_address,
        'capacity_sued': d.capacity_sued,
        'acting_under_color_of_law': d.acting_under_color_of_law,
        'color_of_law_basis': d.color_of_law_basis,
        'is_supervisor': d.is_supervisor,
    } for d in doc.defendants.all()]


def _snap_government_entity(doc):
    ge = getattr(doc, 'government_entity', None)
    if not ge:
        return {}
    return {
        'entity_name': ge.entity_name,
        'entity_address': ge.entity_address,
        'policy_or_custom_description': ge.policy_or_custom_description,
    }


def _snap_claims(doc):
    return [{
        'amendment': c.amendment, 'how_violated': c.how_violated,
    } for c in doc.constitutional_claims.all()]


def _snap_evidence(doc):
    return [{
        'evidence_type': e.evidence_type, 'description': e.description,
        'date_and_time': e.date_and_time, 'recorded_by': e.recorded_by,
        'storage_location': e.storage_location, 'public_url': e.public_url,
        'key_timestamp': e.key_timestamp,
        'defendant_aware_of_recording': e.defendant_aware_of_recording,
    } for e in doc.evidence.all()]


def _snap_witnesses(doc):
    return [{
        'full_name': w.full_name, 'contact_info': w.contact_info,
        'relationship_to_plaintiff': w.relationship_to_plaintiff,
        'what_they_witnessed': w.what_they_witnessed,
        'has_video': w.has_video, 'willing_to_testify': w.willing_to_testify,
    } for w in doc.witnesses.all()]


def _snap_damages(doc):
    d = getattr(doc, 'damages', None)
    if not d:
        return {}
    return {
        'physical_injury_description': d.physical_injury_description,
        'emotional_distress_description': d.emotional_distress_description,
        'lost_wages': d.lost_wages,
        'property_damage_amount': d.property_damage_amount,
        'punitive_basis': d.punitive_basis,
    }


def _snap_relief(doc):
    r = getattr(doc, 'relief_sought', None)
    if not r:
        return {}
    return {
        'compensatory_damages': r.compensatory_damages,
        'compensatory_amount': str(r.compensatory_amount) if r.compensatory_amount else '',
        'punitive_damages': r.punitive_damages,
        'declaratory_judgment': r.declaratory_judgment,
        'injunctive_relief': r.injunctive_relief,
        'attorney_fees': r.attorney_fees,
        'costs_of_suit': r.costs_of_suit,
        'other_relief': r.other_relief,
    }


def _snap_prior(doc):
    p = getattr(doc, 'prior_complaints', None)
    if not p:
        return {}
    return {
        'filed_complaints': p.filed_complaints,
        'description': p.description, 'outcomes': p.outcomes,
    }


# ---------------------------------------------------------------------------
# GPT prompts
# ---------------------------------------------------------------------------

_SYSTEM_PREAMBLE = (
    "You are a legal-document assistant maintaining a Section 1983 civil "
    "rights complaint. The user already analyzed their full story; you are "
    "now adding ONE category of additional detail. Return a single JSON "
    "object — no prose, no markdown, no code fences. Merge the user's "
    "addendum into the existing data and return the updated value for "
    "the requested keys. Preserve existing values when the addendum does "
    "not contradict or extend them. Do NOT invent facts."
)


def _build_system_prompt(cfg):
    keys = ', '.join(repr(k) for k in cfg['json_keys'])
    return (
        f"{_SYSTEM_PREAMBLE}\n\n"
        f"Return JSON with the top-level keys: {keys}.\n"
        f"{cfg['guidance']}"
    )


def _build_user_message(existing, addendum_text):
    return (
        "Existing data for these keys:\n"
        f"{json.dumps(existing, indent=2)}\n\n"
        "Addendum from the user:\n"
        f"{addendum_text}\n\n"
        "Return the updated JSON object."
    )


# ---------------------------------------------------------------------------
# OpenAI call + JSON parsing
# ---------------------------------------------------------------------------

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
            temperature=0.1,
            response_format={'type': 'json_object'},
        )
        return response.choices[0].message.content, None
    except Exception as exc:
        logger.exception('Addendum OpenAI call failed')
        return None, str(exc)


def _parse_json(raw):
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f'Could not parse JSON: {exc}'


# ---------------------------------------------------------------------------
# Merge — non-destructive update of related models
# ---------------------------------------------------------------------------

def _merge_into_models(session, cfg, data):
    doc = session.document
    for key in cfg['json_keys']:
        section = data.get(key)
        if section is None:
            continue
        merger = _MERGERS.get(key)
        if merger:
            merger(doc, section)


def _filled(value):
    """True if a GPT-returned value is meaningful (non-null, non-empty)."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == '':
        return False
    return True


def _merge_one_to_one(model_cls, doc, data, related_name, *,
                      transform=None, skip_fields=()):
    """
    Update fields on a OneToOne-related row where GPT returned a meaningful
    value. Creates the row if missing. `skip_fields` are user-controlled
    fields we never overwrite from an addendum (e.g. court_confirmed).
    """
    if not isinstance(data, dict):
        return
    if transform:
        data = transform(dict(data))
    instance, _ = model_cls.objects.get_or_create(document=doc)
    fields = {f.name for f in model_cls._meta.get_fields() if not f.is_relation}
    changed = []
    for key, value in data.items():
        if key in skip_fields or key not in fields:
            continue
        if _filled(value):
            setattr(instance, key, value)
            changed.append(key)
    if changed:
        instance.save()


def _merge_incident(doc, data):
    from documents.models import IncidentOverview

    def _transform(d):
        if d.get('state'):
            d['state'] = normalize_state(d['state'])
        return d

    _merge_one_to_one(
        IncidentOverview, doc, data, 'incident_overview',
        transform=_transform,
        skip_fields={'court_confirmed', 'federal_district_court'},
    )


def _merge_plaintiff(doc, data):
    from documents.models import PlaintiffInfo

    def _transform(d):
        if d.get('state'):
            d['state'] = normalize_state(d['state'])
        return d

    _merge_one_to_one(PlaintiffInfo, doc, data, 'plaintiff_info', transform=_transform)


def _merge_government_entity(doc, data):
    from documents.models import GovernmentEntity
    _merge_one_to_one(GovernmentEntity, doc, data, 'government_entity')


def _merge_damages(doc, data):
    from documents.models import Damages
    _merge_one_to_one(Damages, doc, data, 'damages')


def _merge_relief(doc, data):
    from documents.models import ReliefSought

    def _transform(d):
        # compensatory_amount is a Decimal field; coerce common GPT shapes
        amt = d.get('compensatory_amount')
        if amt is not None and not isinstance(amt, (int, float)):
            try:
                d['compensatory_amount'] = float(str(amt).replace(',', '').replace('$', '').strip())
            except (ValueError, TypeError):
                d['compensatory_amount'] = None
        return d

    _merge_one_to_one(ReliefSought, doc, data, 'relief_sought', transform=_transform)


def _merge_prior_complaints(doc, data):
    from documents.models import PriorComplaints
    _merge_one_to_one(PriorComplaints, doc, data, 'prior_complaints')


def _merge_defendants(doc, items):
    """Match by case-insensitive full_name; update if matched, create if new."""
    from documents.models import Defendant
    if not isinstance(items, list):
        return
    existing_by_name = {
        (d.full_name or '').strip().lower(): d
        for d in doc.defendants.all() if d.full_name
    }
    fields = {f.name for f in Defendant._meta.get_fields() if not f.is_relation}
    for raw in items:
        if not isinstance(raw, dict):
            continue
        name = (raw.get('full_name') or '').strip()
        match = existing_by_name.get(name.lower()) if name else None
        if match:
            changed = False
            for key, value in raw.items():
                if key in fields and _filled(value):
                    setattr(match, key, value)
                    changed = True
            if changed:
                match.save()
        else:
            data = {k: v for k, v in raw.items() if k in fields and _filled(v)}
            if data:
                Defendant.objects.create(document=doc, **data)


def _merge_claims(doc, items):
    """Match by normalized amendment key (unique_together)."""
    from documents.models import ConstitutionalClaim
    if not isinstance(items, list):
        return
    for raw in items:
        if not isinstance(raw, dict):
            continue
        amendment = normalize_amendment(raw.get('amendment'))
        if not amendment:
            continue
        defaults = {}
        if _filled(raw.get('how_violated')):
            defaults['how_violated'] = raw['how_violated']
        ConstitutionalClaim.objects.update_or_create(
            document=doc, amendment=amendment, defaults=defaults,
        )


def _merge_evidence(doc, items):
    """Match by public_url or (evidence_type + first 60 chars of description)."""
    from documents.models import Evidence
    if not isinstance(items, list):
        return
    fields = {f.name for f in Evidence._meta.get_fields() if not f.is_relation}
    existing = list(doc.evidence.all())

    def _match(raw):
        url = (raw.get('public_url') or '').strip()
        if url:
            for e in existing:
                if (e.public_url or '').strip() == url:
                    return e
        et = raw.get('evidence_type')
        desc_prefix = (raw.get('description') or '').strip()[:60].lower()
        if et and desc_prefix:
            for e in existing:
                if e.evidence_type == et and (e.description or '')[:60].lower() == desc_prefix:
                    return e
        return None

    for raw in items:
        if not isinstance(raw, dict):
            continue
        match = _match(raw)
        if match:
            changed = False
            for key, value in raw.items():
                if key in fields and _filled(value):
                    setattr(match, key, value)
                    changed = True
            if changed:
                match.save()
        else:
            data = {k: v for k, v in raw.items() if k in fields and _filled(v)}
            if data:
                Evidence.objects.create(document=doc, **data)


def _merge_witnesses(doc, items):
    """Match by case-insensitive full_name."""
    from documents.models import Witness
    if not isinstance(items, list):
        return
    existing_by_name = {
        (w.full_name or '').strip().lower(): w
        for w in doc.witnesses.all() if w.full_name
    }
    fields = {f.name for f in Witness._meta.get_fields() if not f.is_relation}
    for raw in items:
        if not isinstance(raw, dict):
            continue
        name = (raw.get('full_name') or '').strip()
        match = existing_by_name.get(name.lower()) if name else None
        if match:
            changed = False
            for key, value in raw.items():
                if key in fields and _filled(value):
                    setattr(match, key, value)
                    changed = True
            if changed:
                match.save()
        else:
            data = {k: v for k, v in raw.items() if k in fields and _filled(v)}
            if data:
                Witness.objects.create(document=doc, **data)


_MERGERS = {
    'incident': _merge_incident,
    'plaintiff': _merge_plaintiff,
    'government_entity': _merge_government_entity,
    'damages': _merge_damages,
    'relief': _merge_relief,
    'prior_complaints': _merge_prior_complaints,
    'defendants': _merge_defendants,
    'constitutional_claims': _merge_claims,
    'evidence': _merge_evidence,
    'witnesses': _merge_witnesses,
}


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def _record_addendum(session, category, text, error=''):
    entries = list(session.story_addendums or [])
    entries.append({
        'category': category,
        'text': text,
        'applied_at': datetime.now(timezone.utc).isoformat(),
        'error': error,
    })
    session.story_addendums = entries
    session.save(update_fields=['story_addendums', 'updated_at'])
