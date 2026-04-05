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
                # Call GPT in dry-run mode — nothing is saved, output goes to terminal
                _gpt_test(session)
                session.current_step = 1
                session.save(update_fields=['current_step', 'updated_at'])
                messages.success(request, 'Story analyzed. Review the federal court below.')
                return redirect('documents:wizard_step1', document_slug=doc.slug)
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
        incident.federal_district_court = request.POST.get('federal_district_court', '').strip()
        incident.court_confirmed = request.POST.get('court_confirmed') == 'on'
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
