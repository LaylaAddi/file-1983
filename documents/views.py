import json
import pprint
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET

from .models import (
    Document, WizardSession, PlaintiffInfo, ExampleStory, IncidentOverview,
    Defendant, GovernmentEntity, ConstitutionalClaim, Evidence, Witness,
)


@login_required
def document_list(request):
    documents = Document.objects.filter(user=request.user).select_related('wizard_session')
    return render(request, 'documents/list.html', {'documents': documents})


@login_required
def document_create(request):
    user = request.user

    # Gate: require complete profile before starting a complaint
    if not user.has_complete_profile():
        messages.warning(
            request,
            'Please complete your profile — your name and address are required for the complaint.'
        )
        return redirect(f"{'/accounts/profile/'}?next={request.path}")

    # Create the Document, WizardSession, and pre-populate PlaintiffInfo from profile
    doc = Document.objects.create(user=user)
    WizardSession.objects.create(document=doc)
    PlaintiffInfo.objects.create(document=doc, **user.get_plaintiff_defaults())

    return redirect('documents:wizard_story', document_slug=doc.slug)


@login_required
def wizard_story(request, document_slug):
    doc = get_object_or_404(Document, slug=document_slug, user=request.user)
    session = doc.wizard_session

    if request.method == 'POST':
        story_text = request.POST.get('story_text', '').strip()
        action = request.POST.get('action', 'analyze')
        if story_text:
            session.story_text = story_text
            session.status = 'in_progress'
            session.save(update_fields=['story_text', 'status', 'updated_at'])
            if action == 'save':
                messages.success(request, 'Story saved. Come back any time to continue.')
                return redirect('documents:wizard_story', document_slug=doc.slug)
            else:
                _gpt_test(session)
                session.current_step = 1
                session.save(update_fields=['current_step', 'updated_at'])
                return redirect('documents:wizard_summary', document_slug=doc.slug)
        else:
            messages.error(request, 'Please enter your story before continuing.')

    # Example stories — only for staff or DEBUG mode
    example_stories = []
    example_stories_json = '{}'
    if request.user.is_staff or settings.DEBUG:
        stories_qs = ExampleStory.objects.filter(is_active=True)
        example_stories = stories_qs
        example_stories_json = json.dumps({
            str(s.pk): s.story_text for s in stories_qs
        })

    return render(request, 'documents/wizard_story.html', {
        'document': doc,
        'session': session,
        'example_stories': example_stories,
        'example_stories_json': example_stories_json,
    })


# ---------------------------------------------------------------------------
# Dev helper — remove once extraction is wired for real
# ---------------------------------------------------------------------------

def _gpt_test(session):
    """
    Calls GPT extraction, saves results to the DB, and prints everything
    to the terminal (runserver output) for inspection.
    """
    from documents.services.openai_service import extract_story

    SEP = '═' * 72

    print(f'\n{SEP}')
    print('GPT EXTRACTION  (saving to DB)')
    print(SEP)
    print(f'Story length: {len(session.story_text)} chars')
    print(f'Story preview: {session.story_text[:200]}…\n')

    ai_analysis, error = extract_story(session, dry_run=False)

    if error:
        print(f'ERROR: {error}')
        print(SEP + '\n')
        return

    SECTION_MODEL = {
        'document':              'Document',
        'plaintiff':             'PlaintiffInfo',
        'incident':              'IncidentOverview',
        'timeline':              'TimelineEntry (one row per entry)',
        'defendants':            'Defendant (one row per defendant)',
        'government_entity':     'GovernmentEntity',
        'constitutional_claims': 'ConstitutionalClaim (one row per claim)',
        'evidence':              'Evidence (one row per item)',
        'witnesses':             'Witness (one row per witness)',
        'damages':               'Damages',
        'relief':                'ReliefSought',
        'prior_complaints':      'PriorComplaints',
    }

    for section, model_label in SECTION_MODEL.items():
        data = ai_analysis.get(section)
        print(f'── {section.upper()}  →  {model_label}')
        if data is None:
            print('   (null — not extracted)')
        else:
            pprint.pprint(data, indent=3)
        print()

    print(SEP)
    print('END OF GPT OUTPUT — data saved to DB')
    print(SEP + '\n')


# ---------------------------------------------------------------------------
# Extraction Summary
# ---------------------------------------------------------------------------

@login_required
def wizard_extraction_summary(request, document_slug):
    doc = get_object_or_404(Document, slug=document_slug, user=request.user)
    session = doc.wizard_session

    if not session.ai_extraction_succeeded:
        return redirect('documents:wizard_story', document_slug=doc.slug)

    summary, critical_missing, warnings = _score_extraction(session.ai_analysis)

    return render(request, 'documents/wizard_summary.html', {
        'document': doc,
        'session': session,
        'summary': summary,
        'critical_missing': critical_missing,
        'warnings': warnings,
    })


def _score_extraction(ai):
    """
    Score GPT extraction results. Returns:
      summary        — list of dicts for display
      critical_missing — list of label strings (blocks are red)
      warnings         — list of label strings (yellow nudges)
    """
    summary = []
    critical_missing = []
    warnings = []

    def item(label, status, detail, critical=False, icon=None):
        summary.append({
            'label': label,
            'status': status,       # 'found' | 'partial' | 'missing'
            'detail': detail,
            'critical': critical,
            'icon': icon or ('check-circle-fill' if status == 'found'
                             else 'exclamation-circle-fill' if status == 'partial'
                             else 'x-circle-fill'),
        })
        if status == 'missing' and critical:
            critical_missing.append(label)
        elif status in ('missing', 'partial') and not critical:
            warnings.append(label)

    # Incident date
    inc = ai.get('incident') or {}
    if inc.get('incident_date'):
        item('Incident date', 'found', inc['incident_date'])
    else:
        item('Incident date', 'missing', 'Not found — you can add it in Step 2', critical=True)

    # Location
    city  = inc.get('city', '')
    state = inc.get('state', '')
    if city and state:
        item('Incident location', 'found', f'{city}, {state}')
    elif city or state:
        item('Incident location', 'partial', f'{city or state} — state or city missing')
        warnings.append('Incident location')
    else:
        item('Incident location', 'missing', 'Not found — needed for court lookup', critical=True)

    # Plaintiff activity
    if inc.get('plaintiff_activity'):
        item('What you were doing', 'found', inc['plaintiff_activity'][:80])
    else:
        item('What you were doing', 'missing', 'Not described — important for your claim')

    # Timeline
    timeline = ai.get('timeline') or []
    if len(timeline) >= 3:
        item('Timeline of events', 'found', f'{len(timeline)} events extracted')
    elif len(timeline) > 0:
        item('Timeline of events', 'partial', f'Only {len(timeline)} event(s) — more detail helps')
    else:
        item('Timeline of events', 'missing', 'No events extracted — describe the sequence of what happened')

    # Defendants
    defendants = ai.get('defendants') or []
    if len(defendants) >= 1:
        names = ', '.join(d.get('full_name') or 'Unknown' for d in defendants[:3])
        if len(defendants) > 3:
            names += f' +{len(defendants) - 3} more'
        item('Defendants / officers', 'found', names)
    else:
        item('Defendants / officers', 'missing',
             'No officers or defendants found — describe who confronted you', critical=True)

    # Constitutional claims
    claims = ai.get('constitutional_claims') or []
    if len(claims) >= 1:
        amendments = ', '.join(
            (c.get('amendment') or '') + ' Amendment'
            for c in claims if c.get('amendment')
        )
        item('Constitutional claims', 'found', amendments or f'{len(claims)} claim(s)')
    else:
        item('Constitutional claims', 'missing',
             'No rights violations identified — describe what rights were violated', critical=True)

    # Evidence
    evidence = ai.get('evidence') or []
    if len(evidence) >= 1:
        item('Evidence', 'found', f'{len(evidence)} item(s) — video, photos, documents, etc.')
    else:
        item('Evidence', 'missing', 'None mentioned — you can add it later in Step 5')

    # Witnesses
    witnesses = ai.get('witnesses') or []
    if len(witnesses) >= 1:
        item('Witnesses', 'found', f'{len(witnesses)} witness(es) identified')
    else:
        item('Witnesses', 'missing', 'None mentioned — you can add witnesses later in Step 5')

    # Damages
    dmg = ai.get('damages') or {}
    dmg_fields = [v for v in dmg.values() if v]
    if len(dmg_fields) >= 2:
        item('Damages', 'found', 'Physical, emotional, or financial harm described')
    elif len(dmg_fields) == 1:
        item('Damages', 'partial', 'Only some damage described — more detail strengthens your case')
    else:
        item('Damages', 'missing', 'No harm described — explain how this affected you')

    return summary, critical_missing, warnings


# ---------------------------------------------------------------------------
# Step 1 — Incident Overview + Federal Jurisdiction
# ---------------------------------------------------------------------------

STATE_CHOICES = [
    ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
    ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
    ('DC', 'District of Columbia'), ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'),
    ('ID', 'Idaho'), ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'),
    ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'),
    ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'),
    ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'),
    ('NV', 'Nevada'), ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'),
    ('NY', 'New York'), ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'),
    ('OK', 'Oklahoma'), ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'),
    ('SC', 'South Carolina'), ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'),
    ('UT', 'Utah'), ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'),
    ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming'),
]


@login_required
def wizard_step1(request, document_slug):
    """Step 1 — Federal jurisdiction only. Confirm or override the court."""
    doc = get_object_or_404(Document, slug=document_slug, user=request.user)
    session = doc.wizard_session
    incident, _ = IncidentOverview.objects.get_or_create(document=doc)

    # Auto-run court lookup if we have city+state but no court yet
    if incident.city and incident.state and not incident.federal_district_court:
        try:
            from documents.services.court_lookup_service import CourtLookupService
            result = CourtLookupService.lookup_court_by_location(incident.city, incident.state)
            if result and result.get('court_name'):
                incident.federal_district_court = result['court_name']
                incident.save(update_fields=['federal_district_court'])
        except Exception:
            pass

    if request.method == 'POST':
        federal_district_court = request.POST.get('federal_district_court', '').strip()
        court_confirmed = request.POST.get('court_confirmed') == 'on'

        if not federal_district_court:
            messages.error(request, 'Please enter or look up the federal district court before continuing.')
            return redirect('documents:wizard_step1', document_slug=doc.slug)

        if not court_confirmed:
            messages.error(request, 'You must confirm the federal district court before continuing.')
            return redirect('documents:wizard_step1', document_slug=doc.slug)

        incident.federal_district_court = federal_district_court
        incident.court_confirmed = True
        incident.save(update_fields=['federal_district_court', 'court_confirmed'])

        if session.current_step < 2:
            session.current_step = 2
            session.save(update_fields=['current_step', 'updated_at'])

        messages.success(request, 'Jurisdiction confirmed.')
        return redirect('documents:wizard_step2', document_slug=doc.slug)

    return render(request, 'documents/wizard_step1.html', {
        'document': doc,
        'session': session,
        'incident': incident,
        'state_choices': STATE_CHOICES,
    })


def _parse_tristate(value):
    """Convert a form tristate (yes/no/blank) to True/False/None."""
    if value == 'yes':
        return True
    if value == 'no':
        return False
    return None


# ---------------------------------------------------------------------------
# Step 2 — Incident Details
# ---------------------------------------------------------------------------

@login_required
def wizard_step2(request, document_slug):
    """Step 2 — Review/edit incident details extracted by GPT."""
    doc = get_object_or_404(Document, slug=document_slug, user=request.user)
    session = doc.wizard_session
    incident, _ = IncidentOverview.objects.get_or_create(document=doc)

    if request.method == 'POST':
        # Parse date
        date_str = request.POST.get('incident_date', '').strip()
        incident.incident_date = date_str or None

        # Parse time
        time_str = request.POST.get('incident_time', '').strip()
        incident.incident_time = time_str or None

        # Location fields
        new_city = request.POST.get('city', '').strip()
        new_state = request.POST.get('state', '').strip()
        city_or_state_changed = (
            new_city.lower() != (incident.city or '').lower()
            or new_state != (incident.state or '')
        )

        incident.address = request.POST.get('address', '').strip()
        incident.city = new_city
        incident.state = new_state
        incident.county = request.POST.get('county', '').strip()
        incident.location_description = request.POST.get('location_description', '').strip()
        incident.location_type = request.POST.get('location_type', '').strip()
        incident.is_public_forum = _parse_tristate(request.POST.get('is_public_forum', ''))

        # Activity & force
        incident.plaintiff_activity = request.POST.get('plaintiff_activity', '').strip()
        incident.force_used = _parse_tristate(request.POST.get('force_used', ''))
        incident.equipment_seized_or_damaged = _parse_tristate(
            request.POST.get('equipment_seized_or_damaged', '')
        )

        # If city or state changed, clear court so Step 1 re-runs
        if city_or_state_changed:
            incident.federal_district_court = ''
            incident.court_confirmed = False

        incident.save()

        # Advance wizard
        if session.current_step < 3:
            session.current_step = 3
            session.save(update_fields=['current_step', 'updated_at'])

        messages.success(request, 'Incident details saved.')

        # If court was cleared, send user back to Step 1 to re-confirm
        if city_or_state_changed and not incident.court_confirmed:
            messages.info(
                request,
                'The city or state changed — please re-confirm the federal district court.'
            )
            return redirect('documents:wizard_step1', document_slug=doc.slug)

        return redirect('documents:wizard_step3', document_slug=doc.slug)

    return render(request, 'documents/wizard_step2.html', {
        'document': doc,
        'session': session,
        'incident': incident,
        'state_choices': STATE_CHOICES,
        'location_type_groups': LOCATION_TYPE_GROUPS,
    })


# Grouped location types — used to render an <optgroup> dropdown in Step 2.
# Keys must match IncidentOverview.LOCATION_TYPE_CHOICES.
LOCATION_TYPE_GROUPS = [
    ('Public Outdoor', [
        ('public_sidewalk', 'Public Sidewalk'),
        ('public_park', 'Public Park'),
        ('public_plaza', 'Public Plaza / Square'),
        ('public_parking_lot', 'Public Parking Lot'),
        ('roadway', 'Roadway / Highway'),
        ('traffic_stop', 'Traffic Stop (roadside)'),
    ]),
    ('Government Buildings', [
        ('police_station', 'Police Station / Lobby'),
        ('sheriff_office', "Sheriff's Office / Lobby"),
        ('courthouse', 'Courthouse / Lobby'),
        ('city_hall', 'City / Town Hall'),
        ('county_building', 'County Government Building'),
        ('federal_building', 'Federal Building'),
        ('dmv', 'DMV / Motor Vehicle Office'),
        ('post_office', 'Post Office'),
        ('government_office', 'Other Government Office / Building'),
    ]),
    ('Public Institutions', [
        ('public_school', 'Public School'),
        ('public_library', 'Public Library'),
        ('public_hospital', 'Public Hospital / Clinic'),
        ('jail', 'Jail / Detention Center'),
        ('prison', 'Prison / Correctional Facility'),
    ]),
    ('Transportation', [
        ('airport', 'Airport / Terminal'),
        ('transit_station', 'Train / Bus Station'),
        ('transit_vehicle', 'Bus / Train / Transit Vehicle'),
        ('personal_vehicle', 'Personal Vehicle'),
    ]),
    ('Private Property', [
        ('private_residence', 'Private Residence'),
        ('private_business', 'Private Business / Store'),
    ]),
    ('Other', [
        ('other', 'Other'),
    ]),
]


# Plain-English guidance for Step 4 (Constitutional Claims).
# Keys must match ConstitutionalClaim.AMENDMENT_CHOICES.
# Used to help pro se users understand what each amendment protects.
AMENDMENT_INFO = {
    '1st': {
        'description': 'Protects freedom of speech, religion, assembly, and the press from government restriction.',
        'examples': [
            'Being silenced or threatened for speaking in a public forum',
            'A protest or assembly shut down without valid reason',
            'Religious expression restricted by government officials',
        ],
    },
    '1st_retaliation': {
        'description': 'Protects you from being punished by government officials for exercising your constitutional rights.',
        'examples': [
            'Being arrested or cited after filming police in public',
            'Being targeted for filing a complaint against an officer',
            'Being harassed for political speech or expression',
        ],
    },
    '1st_prior_restraint': {
        'description': 'Forbids the government from preventing speech or publication before it occurs.',
        'examples': [
            'Being ordered to stop filming before any violation occurred',
            'Being prohibited from distributing materials in a public space',
        ],
    },
    '1st_viewpoint': {
        'description': "Forbids the government from favoring or silencing speech based on the speaker's viewpoint.",
        'examples': [
            'Being allowed to express one political view but not another in the same forum',
            'Being singled out for a specific message while others are permitted to speak',
        ],
    },
    '4th_search': {
        'description': 'Protects against unreasonable searches of your person, property, or belongings by the government.',
        'examples': [
            'Officers searching your phone, car, or home without a warrant or valid exception',
            'Being patted down without reasonable suspicion you are armed',
        ],
    },
    '4th_seizure': {
        'description': 'Protects against unreasonable detention or arrest without legal justification.',
        'examples': [
            'Being arrested without probable cause',
            'Being detained far longer than necessary for a brief investigative stop',
            'Being stopped when you were free to leave and no reasonable suspicion existed',
        ],
    },
    '4th_property': {
        'description': 'Protects your personal property from unreasonable seizure or destruction by the government.',
        'examples': [
            'Phone or camera seized or destroyed by an officer',
            'Personal belongings taken without a warrant or justification',
        ],
    },
    '4th_excessive_force': {
        'description': 'Protects you from police force that is objectively unreasonable given the circumstances.',
        'examples': [
            'Being struck, tackled, or tasered when offering no resistance',
            'Handcuffs applied so tightly they cause injury',
            'Deadly force used against someone posing no threat',
        ],
    },
    '5th_due_process': {
        'description': 'Protects against deprivation of life, liberty, or property without fair legal procedure by federal officials.',
        'examples': [
            'Property taken by federal agents without fair process',
            'Federal charges brought with no procedural safeguards',
        ],
    },
    '5th_self_incrimination': {
        'description': 'Protects you from being forced to testify against yourself in a criminal matter.',
        'examples': [
            'Being compelled or coerced into a statement during custodial interrogation',
            'Miranda rights violated during questioning',
        ],
    },
    '6th_counsel': {
        'description': 'Guarantees the right to an attorney during criminal proceedings.',
        'examples': [
            'Being denied a lawyer after formal criminal proceedings begin',
            'Counsel interfered with during critical stages of prosecution',
        ],
    },
    '8th_cruel': {
        'description': 'Protects against cruel and unusual punishment — most relevant after a criminal conviction (inmates and detainees).',
        'examples': [
            'Deliberate indifference to serious medical needs in jail or prison',
            'Excessive force by corrections officers on a convicted inmate',
        ],
    },
    '14th_due_process': {
        'description': 'Extends due process protections to state and local government actions — the most common basis for 1983 claims beyond the Fourth Amendment.',
        'examples': [
            'Property taken by state or local officials without fair procedure',
            'Government action depriving you of liberty without due process',
        ],
    },
    '14th_equal_protection': {
        'description': 'Forbids state and local governments from treating similarly-situated people differently without legal justification.',
        'examples': [
            'Being singled out by police because of race, religion, or other protected characteristic',
            'Selective enforcement of the law against you while similarly-situated people are left alone',
        ],
    },
    'other': {
        'description': 'Use this if your claim does not fit the categories above. Describe the right and how it was violated in the text field below.',
        'examples': [],
    },
}


# ---------------------------------------------------------------------------
# Step 3 — Defendants
# ---------------------------------------------------------------------------

@login_required
def wizard_step3(request, document_slug):
    """Step 3 — Add/edit/delete defendants + government entity (Monell)."""
    doc = get_object_or_404(Document, slug=document_slug, user=request.user)
    session = doc.wizard_session
    gov_entity, _ = GovernmentEntity.objects.get_or_create(document=doc)

    if request.method == 'POST':
        # --- Parse defendants from indexed POST fields ---
        defendant_count = int(request.POST.get('defendant_count', 0))
        existing_defendants = {d.pk: d for d in doc.defendants.all()}
        seen_pks = set()

        for i in range(defendant_count):
            prefix = f'def_{i}_'
            full_name = request.POST.get(f'{prefix}full_name', '').strip()
            if not full_name:
                continue

            pk_str = request.POST.get(f'{prefix}pk', '')
            pk = int(pk_str) if pk_str else None

            defaults = {
                'full_name': full_name,
                'badge_number': request.POST.get(f'{prefix}badge_number', '').strip(),
                'rank_title': request.POST.get(f'{prefix}rank_title', '').strip(),
                'agency_name': request.POST.get(f'{prefix}agency_name', '').strip(),
                'capacity_sued': request.POST.get(f'{prefix}capacity_sued', 'both').strip(),
                'acting_under_color_of_law': request.POST.get(f'{prefix}acting_under_color_of_law') == 'on',
                'is_supervisor': request.POST.get(f'{prefix}is_supervisor') == 'on',
                'order': i,
            }

            if pk and pk in existing_defendants:
                obj = existing_defendants[pk]
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save()
                seen_pks.add(pk)
            else:
                obj = Defendant.objects.create(document=doc, **defaults)
                seen_pks.add(obj.pk)

        # Delete defendants that were removed by the user
        for pk, obj in existing_defendants.items():
            if pk not in seen_pks:
                obj.delete()

        # --- Government Entity ---
        gov_entity.entity_name = request.POST.get('entity_name', '').strip()
        gov_entity.entity_address = request.POST.get('entity_address', '').strip()
        gov_entity.policy_or_custom_description = request.POST.get(
            'policy_or_custom_description', ''
        ).strip()
        gov_entity.save()

        # Advance wizard
        if session.current_step < 4:
            session.current_step = 4
            session.save(update_fields=['current_step', 'updated_at'])

        messages.success(request, 'Defendants saved.')
        return redirect('documents:wizard_step4', document_slug=doc.slug)

    defendants = list(doc.defendants.all().values(
        'pk', 'full_name', 'badge_number', 'rank_title', 'agency_name',
        'capacity_sued', 'acting_under_color_of_law', 'is_supervisor', 'order',
    ))

    return render(request, 'documents/wizard_step3.html', {
        'document': doc,
        'session': session,
        'defendants_json': json.dumps(defendants),
        'defendant_count': len(defendants),
        'gov_entity': gov_entity,
        'capacity_choices': Defendant.CAPACITY_CHOICES,
    })


# ---------------------------------------------------------------------------
# Step 4 — Constitutional Claims
# ---------------------------------------------------------------------------

@login_required
def wizard_step4(request, document_slug):
    """Step 4 — Add/edit/delete constitutional claims."""
    doc = get_object_or_404(Document, slug=document_slug, user=request.user)
    session = doc.wizard_session

    if request.method == 'POST':
        claim_count = int(request.POST.get('claim_count', 0))
        existing_claims = {c.pk: c for c in doc.constitutional_claims.all()}
        seen_pks = set()
        seen_amendments = set()
        duplicate_warning = False

        for i in range(claim_count):
            prefix = f'claim_{i}_'
            amendment = request.POST.get(f'{prefix}amendment', '').strip()
            if not amendment:
                continue

            # Enforce unique_together(document, amendment) at the view layer
            if amendment in seen_amendments:
                duplicate_warning = True
                continue
            seen_amendments.add(amendment)

            pk_str = request.POST.get(f'{prefix}pk', '')
            pk = int(pk_str) if pk_str else None

            defaults = {
                'amendment': amendment,
                'how_violated': request.POST.get(f'{prefix}how_violated', '').strip(),
            }

            if pk and pk in existing_claims:
                obj = existing_claims[pk]
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save()
                seen_pks.add(pk)
            else:
                obj, _ = ConstitutionalClaim.objects.update_or_create(
                    document=doc, amendment=amendment,
                    defaults={'how_violated': defaults['how_violated']},
                )
                seen_pks.add(obj.pk)

        # Delete claims that were removed
        for pk, obj in existing_claims.items():
            if pk not in seen_pks:
                obj.delete()

        # Advance wizard
        if session.current_step < 5:
            session.current_step = 5
            session.save(update_fields=['current_step', 'updated_at'])

        if duplicate_warning:
            messages.warning(
                request,
                'Duplicate amendment selections were skipped — each amendment can only be used once.'
            )
        messages.success(request, 'Constitutional claims saved.')
        return redirect('documents:wizard_step5', document_slug=doc.slug)

    # Normalize existing amendment values (in case they were stored with older,
    # loose values like "First" instead of "1st_retaliation") so the dropdown
    # pre-selects correctly. The normalized value is saved back to the DB on
    # the next form submission.
    from documents.services.openai_service import normalize_amendment
    claims = []
    for c in doc.constitutional_claims.all().values('pk', 'amendment', 'how_violated'):
        c['amendment'] = normalize_amendment(c['amendment'])
        claims.append(c)

    return render(request, 'documents/wizard_step4.html', {
        'document': doc,
        'session': session,
        'claims_json': json.dumps(claims),
        'amendment_choices': ConstitutionalClaim.AMENDMENT_CHOICES,
        'amendment_labels_json': json.dumps(dict(ConstitutionalClaim.AMENDMENT_CHOICES)),
        'amendment_info_json': json.dumps(AMENDMENT_INFO),
    })


# ---------------------------------------------------------------------------
# Step 5 — Evidence & Witnesses
# ---------------------------------------------------------------------------

@login_required
def wizard_step5(request, document_slug):
    """Step 5 — Add/edit/delete evidence items and witnesses."""
    doc = get_object_or_404(Document, slug=document_slug, user=request.user)
    session = doc.wizard_session

    if request.method == 'POST':
        # --- Parse evidence from indexed POST fields ---
        evidence_count = int(request.POST.get('evidence_count', 0))
        existing_evidence = {e.pk: e for e in doc.evidence.all()}
        seen_evidence_pks = set()

        for i in range(evidence_count):
            prefix = f'ev_{i}_'
            description = request.POST.get(f'{prefix}description', '').strip()
            evidence_type = request.POST.get(f'{prefix}evidence_type', '').strip()
            public_url = request.POST.get(f'{prefix}public_url', '').strip()
            # Skip rows with no meaningful content
            if not description and not public_url:
                continue

            pk_str = request.POST.get(f'{prefix}pk', '')
            pk = int(pk_str) if pk_str else None

            defaults = {
                'evidence_type': evidence_type or 'other',
                'description': description,
                'date_and_time': request.POST.get(f'{prefix}date_and_time', '').strip(),
                'recorded_by': request.POST.get(f'{prefix}recorded_by', '').strip(),
                'public_url': public_url,
                'defendant_aware_of_recording': _parse_tristate(
                    request.POST.get(f'{prefix}defendant_aware_of_recording', '')
                ),
                'order': i,
            }

            if pk and pk in existing_evidence:
                obj = existing_evidence[pk]
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save()
                seen_evidence_pks.add(pk)
            else:
                obj = Evidence.objects.create(document=doc, **defaults)
                seen_evidence_pks.add(obj.pk)

        for pk, obj in existing_evidence.items():
            if pk not in seen_evidence_pks:
                obj.delete()

        # --- Parse witnesses from indexed POST fields ---
        witness_count = int(request.POST.get('witness_count', 0))
        existing_witnesses = {w.pk: w for w in doc.witnesses.all()}
        seen_witness_pks = set()

        for i in range(witness_count):
            prefix = f'wit_{i}_'
            full_name = request.POST.get(f'{prefix}full_name', '').strip()
            what_they_witnessed = request.POST.get(f'{prefix}what_they_witnessed', '').strip()
            # Skip completely empty rows
            if not full_name and not what_they_witnessed:
                continue

            pk_str = request.POST.get(f'{prefix}pk', '')
            pk = int(pk_str) if pk_str else None

            defaults = {
                'full_name': full_name,
                'contact_info': request.POST.get(f'{prefix}contact_info', '').strip(),
                'relationship_to_plaintiff': request.POST.get(
                    f'{prefix}relationship_to_plaintiff', ''
                ).strip(),
                'what_they_witnessed': what_they_witnessed,
                'has_video': _parse_tristate(request.POST.get(f'{prefix}has_video', '')),
                'willing_to_testify': _parse_tristate(
                    request.POST.get(f'{prefix}willing_to_testify', '')
                ),
                'order': i,
            }

            if pk and pk in existing_witnesses:
                obj = existing_witnesses[pk]
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save()
                seen_witness_pks.add(pk)
            else:
                obj = Witness.objects.create(document=doc, **defaults)
                seen_witness_pks.add(obj.pk)

        for pk, obj in existing_witnesses.items():
            if pk not in seen_witness_pks:
                obj.delete()

        if session.current_step < 6:
            session.current_step = 6
            session.save(update_fields=['current_step', 'updated_at'])

        messages.success(request, 'Evidence and witnesses saved.')
        # TODO: redirect to Step 6 once built
        return redirect('documents:wizard_step5', document_slug=doc.slug)

    evidence = list(doc.evidence.all().values(
        'pk', 'evidence_type', 'description', 'date_and_time', 'recorded_by',
        'public_url', 'defendant_aware_of_recording', 'order',
    ))
    witnesses = list(doc.witnesses.all().values(
        'pk', 'full_name', 'contact_info', 'relationship_to_plaintiff',
        'what_they_witnessed', 'has_video', 'willing_to_testify', 'order',
    ))

    return render(request, 'documents/wizard_step5.html', {
        'document': doc,
        'session': session,
        'evidence_json': json.dumps(evidence),
        'witnesses_json': json.dumps(witnesses),
        'evidence_count': len(evidence),
        'witness_count': len(witnesses),
        'evidence_type_choices': Evidence.EVIDENCE_TYPE_CHOICES,
    })


@require_GET
@login_required
def lookup_district_court(request):
    """AJAX: return the federal district court for a given city + state."""
    city = request.GET.get('city', '').strip()
    state = request.GET.get('state', '').strip().upper()

    if not city or not state:
        return JsonResponse({'success': False, 'error': 'City and state are required.'})

    try:
        from documents.services.court_lookup_service import CourtLookupService
        result = CourtLookupService.lookup_court_by_location(city, state)
        if result:
            return JsonResponse({
                'success': True,
                'court_name': result.get('court_name', ''),
                'confidence': result.get('confidence', 'low'),
                'district': result.get('district', ''),
                'method': result.get('method', ''),
            })
        return JsonResponse({
            'success': False,
            'error': f'Could not find federal district court for {city}, {state}.',
        })
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})
