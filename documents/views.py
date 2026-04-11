import json
import pprint
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET

from .models import Document, WizardSession, PlaintiffInfo, ExampleStory, IncidentOverview


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

        # TODO: redirect to step 2 once built
        messages.success(request, 'Jurisdiction confirmed.')
        return redirect('documents:wizard_step1', document_slug=doc.slug)

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
