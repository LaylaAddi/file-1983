import functools

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Incident, TargetAgency, Complaint
from .services import api_quota, rate_limit, video_intake, complaint_drafter, email_service, moderation


def feature_enabled(view_func):
    """
    Gates every view in this app behind SiteSettings.citizen_complaint_enabled.

    Hiding the nav links isn't enough on its own — a bookmarked or shared
    /citizen-complaint/ URL has to stop working too, or the feature is only
    cosmetically off. Raises 404 so a switched-off feature looks like it
    simply isn't there; note this project sets `handler404 =
    redirect_to_home` in config/urls.py, so what the visitor actually sees
    is a redirect to the homepage, same as any other unknown URL here.

    Staff are exempt: the point of the switch is to park the feature for
    users while it's being fixed, not to lock the developer out of testing
    it. Applied OUTSIDE @login_required so an anonymous visitor gets the
    same 404 as everyone else instead of a login redirect that would hint
    the URL is real.
    """
    @functools.wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        from accounts.models import SiteSettings

        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and user.is_staff:
            return view_func(request, *args, **kwargs)
        try:
            enabled = SiteSettings.get_solo().citizen_complaint_enabled
        except Exception:
            enabled = False  # fail closed
        if not enabled:
            raise Http404('Citizen Complaint Assistant is not currently available.')
        return view_func(request, *args, **kwargs)

    return _wrapped


@feature_enabled
def landing(request):
    """Public landing page. Anonymous visitors see a description of the
    feature + a CTA to register. Logged-in users get a link to their
    My Complaints list instead of a duplicate listing here."""
    return render(request, 'citizen_complaint/landing.html')


@feature_enabled
@login_required
def incident_list(request):
    """My Complaints — every incident this user has started, in progress or
    sent, with a Continue/View/Download action per row. The one place a user
    can come back to later to finish a draft or re-download a sent complaint."""
    incidents = Incident.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'citizen_complaint/list.html', {'incidents': incidents})


def _owned_incident_or_404(request, incident_slug):
    return get_object_or_404(Incident, slug=incident_slug, user=request.user)


@feature_enabled
@login_required
def incident_new(request):
    if request.method == 'POST':
        video_url = (request.POST.get('video_url') or '').strip()
        if not video_url:
            messages.error(request, 'Please paste a video URL.')
            return render(request, 'citizen_complaint/new.html')

        if not rate_limit.can_start_incident(request.user):
            messages.error(request, rate_limit.incident_daily_cap_message())
            return render(request, 'citizen_complaint/new.html')

        incident = Incident.objects.create(user=request.user, video_url=video_url)

        try:
            success, message = video_intake.run_intake(incident)
            if success:
                messages.success(request, message)
            else:
                messages.warning(request, message)
        except api_quota.QuotaExceeded:
            messages.error(request, api_quota.upgrade_message(incident))
        except api_quota.AICallTooSoon as exc:
            messages.error(request, f'Please wait a few seconds and try again ({exc.retry_after}s cooldown).')

        return redirect('citizen_complaint:agencies', incident_slug=incident.slug)

    return render(request, 'citizen_complaint/new.html')


@feature_enabled
@login_required
def incident_agencies(request, incident_slug):
    incident = _owned_incident_or_404(request, incident_slug)

    if request.method == 'POST':
        for ta in incident.target_agencies.all():
            if request.POST.get(f'delete_{ta.id}'):
                ta.delete()
                continue
            ta.confirmed = bool(request.POST.get(f'confirmed_{ta.id}'))
            ta.email = (request.POST.get(f'email_{ta.id}', ta.email) or '').strip()
            ta.role_description = (request.POST.get(f'role_{ta.id}', ta.role_description) or '').strip()
            ta.save()

        new_name = (request.POST.get('new_agency_name') or '').strip()
        if new_name:
            new_email = (request.POST.get('new_agency_email') or '').strip()
            new_role = (request.POST.get('new_agency_role') or '').strip()
            TargetAgency.objects.create(
                incident=incident, name=new_name, email=new_email,
                role_description=new_role, source='manual', confirmed=bool(new_email),
                order=incident.target_agencies.count(),
            )

        if request.POST.get('action') == 'continue':
            confirmed = incident.target_agencies.filter(confirmed=True).exclude(email='')
            if not confirmed.exists():
                messages.error(request, 'Select at least one agency and give it a valid email before continuing.')
                return redirect('citizen_complaint:agencies', incident_slug=incident.slug)
            incident.status = 'agencies_reviewed'
            incident.current_step = 2
            incident.save(update_fields=['status', 'current_step', 'updated_at'])
            return redirect('citizen_complaint:about_you', incident_slug=incident.slug)

        messages.success(request, 'Agencies updated.')
        return redirect('citizen_complaint:agencies', incident_slug=incident.slug)

    return render(request, 'citizen_complaint/agencies.html', {
        'incident': incident,
        'target_agencies': incident.target_agencies.all(),
    })


@feature_enabled
@login_required
def incident_about_you(request, incident_slug):
    incident = _owned_incident_or_404(request, incident_slug)

    if request.method == 'POST':
        incident.privacy_level = request.POST.get('privacy_level', incident.privacy_level)
        incident.user_city = (request.POST.get('user_city') or '').strip()
        incident.user_state = (request.POST.get('user_state') or '').strip()
        incident.contact_email = (request.POST.get('contact_email') or '').strip()
        incident.personal_note = (request.POST.get('personal_note') or '').strip()
        incident.tone = request.POST.get('tone', incident.tone)
        incident.status = 'info_collected'
        incident.current_step = 3
        incident.save()
        return redirect('citizen_complaint:drafts', incident_slug=incident.slug)

    confirmed_agency_names = list(
        incident.target_agencies.filter(confirmed=True).exclude(email='').values_list('name', flat=True)
    )
    return render(request, 'citizen_complaint/about_you.html', {
        'incident': incident,
        'confirmed_agency_names': confirmed_agency_names,
    })


@feature_enabled
@login_required
def incident_drafts(request, incident_slug):
    incident = _owned_incident_or_404(request, incident_slug)
    confirmed_agencies = incident.target_agencies.filter(confirmed=True).exclude(email='')

    if not confirmed_agencies.exists():
        messages.error(request, 'Go back and confirm at least one agency first.')
        return redirect('citizen_complaint:agencies', incident_slug=incident.slug)

    if request.method == 'POST':
        for ta in confirmed_agencies:
            complaint = getattr(ta, 'complaint', None)
            if complaint is None:
                continue
            field = f'body_{complaint.id}'
            if field in request.POST:
                complaint.body = request.POST.get(field, '')
                complaint.save(update_fields=['body', 'updated_at'])

            if request.POST.get(f'regenerate_{complaint.id}'):
                try:
                    api_quota.consume_call_throttled(incident)
                    body, error = complaint_drafter.generate_draft(incident, ta)
                    if body:
                        complaint.body = body
                        complaint.save(update_fields=['body', 'updated_at'])
                    else:
                        messages.error(request, f'Could not regenerate draft for {ta.name}: {error}')
                except api_quota.QuotaExceeded:
                    messages.error(request, api_quota.upgrade_message(incident))
                except api_quota.AICallTooSoon as exc:
                    messages.error(request, f'Please wait {exc.retry_after}s before regenerating another draft.')

        if request.POST.get('action') == 'continue':
            incident.status = 'drafted'
            incident.current_step = 4
            incident.save(update_fields=['status', 'current_step', 'updated_at'])
            return redirect('citizen_complaint:send', incident_slug=incident.slug)

        messages.success(request, 'Drafts saved.')
        return redirect('citizen_complaint:drafts', incident_slug=incident.slug)

    # Ensure every confirmed agency has a Complaint row, drafting one if quota allows.
    for ta in confirmed_agencies:
        complaint, created = Complaint.objects.get_or_create(incident=incident, target_agency=ta)
        if not complaint.body:
            try:
                api_quota.consume_call(incident)
                body, error = complaint_drafter.generate_draft(incident, ta)
                if body:
                    complaint.body = body
                    complaint.save(update_fields=['body', 'updated_at'])
            except (api_quota.QuotaExceeded, api_quota.AICallTooSoon):
                pass
        if not complaint.viewed_at:
            complaint.viewed_at = timezone.now()
            complaint.save(update_fields=['viewed_at'])

    return render(request, 'citizen_complaint/drafts.html', {
        'incident': incident,
        'complaints': Complaint.objects.filter(target_agency__in=confirmed_agencies).select_related('target_agency'),
    })


@feature_enabled
@login_required
def incident_send(request, incident_slug):
    incident = _owned_incident_or_404(request, incident_slug)
    complaints = Complaint.objects.filter(
        incident=incident, target_agency__confirmed=True, status='draft',
    ).exclude(target_agency__email='').select_related('target_agency')

    if not complaints.exists():
        messages.error(request, 'Nothing ready to send yet — draft your complaints first.')
        return redirect('citizen_complaint:drafts', incident_slug=incident.slug)

    if request.method == 'POST':
        if not request.user.email_verified:
            messages.error(request, 'Verify your email before sending — check your inbox or resend the link from your profile.')
            return redirect('citizen_complaint:send', incident_slug=incident.slug)

        if not rate_limit.can_send(request.user):
            messages.error(request, rate_limit.user_daily_cap_message())
            return redirect('citizen_complaint:send', incident_slug=incident.slug)

        sent_any = False
        for complaint in complaints:
            ta = complaint.target_agency
            if not request.POST.get(f'send_{complaint.id}'):
                continue
            if not rate_limit.can_send_to_agency(ta.email):
                messages.warning(request, rate_limit.agency_daily_cap_message(ta.name))
                continue
            if not rate_limit.can_send(request.user):
                messages.warning(request, rate_limit.user_daily_cap_message())
                break

            flagged, categories, mod_error = moderation.check_content(complaint.body)
            complaint.moderation_checked_at = timezone.now()
            complaint.moderation_flagged = flagged
            complaint.moderation_categories = categories
            complaint.save(update_fields=['moderation_checked_at', 'moderation_flagged', 'moderation_categories', 'updated_at'])
            if flagged:
                if mod_error:
                    messages.error(request, f'Could not verify the draft to {ta.name} is safe to send right now — try again shortly.')
                else:
                    messages.error(request, f'The draft to {ta.name} was blocked — it appears to contain threatening or violent content. Edit it and try again.')
                continue

            ok, error = email_service.send_complaint(incident, ta, complaint)
            if ok:
                complaint.status = 'sent'
                complaint.sent_at = timezone.now()
                complaint.recipient_email_snapshot = ta.email
                complaint.save(update_fields=['status', 'sent_at', 'recipient_email_snapshot', 'updated_at'])
                sent_any = True
            else:
                messages.error(request, f'Failed to send to {ta.name}: {error}')

        if sent_any:
            if not incident.complaints.filter(status='draft').exists():
                incident.status = 'sent'
                incident.save(update_fields=['status', 'updated_at'])
            return redirect('citizen_complaint:sent', incident_slug=incident.slug)

        messages.error(request, 'Nothing was sent — select at least one recipient.')
        return redirect('citizen_complaint:send', incident_slug=incident.slug)

    return render(request, 'citizen_complaint/send_confirm.html', {
        'incident': incident,
        'complaints': complaints,
    })


@feature_enabled
@login_required
def incident_sent(request, incident_slug):
    incident = _owned_incident_or_404(request, incident_slug)
    sent_complaints = incident.complaints.filter(status='sent').select_related('target_agency')
    return render(request, 'citizen_complaint/sent.html', {
        'incident': incident,
        'complaints': sent_complaints,
    })


@feature_enabled
@login_required
def incident_pdf(request, incident_slug):
    incident = _owned_incident_or_404(request, incident_slug)
    complaints = incident.complaints.exclude(body='').select_related('target_agency')
    if not complaints.exists():
        messages.warning(request, 'Nothing drafted yet to export.')
        return redirect('citizen_complaint:drafts', incident_slug=incident.slug)

    html_string = render_to_string('citizen_complaint/pdf/complaint_packet.html', {
        'incident': incident,
        'complaints': complaints,
    }, request=request)

    from weasyprint import HTML
    pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="citizen_complaint_{incident.slug}.pdf"'
    return response
