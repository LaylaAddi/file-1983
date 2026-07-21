from django.conf import settings as dj_settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import views as auth_views
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from .forms import RegisterForm, LoginForm, ProfileForm, CustomPasswordResetForm, CustomSetPasswordForm
from .models import SiteSettings, LegalDocument


# Caps signups per IP to slow down scripted account creation. axes already
# guards repeated login failures; this guards the registration form itself.
@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def register(request):
    settings_obj = SiteSettings.get_solo()
    if not settings_obj.registration_open:
        messages.error(request, 'Registration is currently closed.')
        return redirect('accounts:login')

    if request.user.is_authenticated:
        return redirect('documents:list')

    prefilled_ref = ''
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # If signup granted tester status via an auto-grants promo code,
            # stash the canonical code in session so the pay page's existing
            # `session['referral_code']` pre-fill picks it up at checkout.
            granted_code = getattr(form, '_granted_tester_code', '')
            if granted_code:
                request.session['referral_code'] = granted_code
            # User was created directly via form.save() rather than
            # authenticate(), so it has no .backend attribute. With axes
            # added to AUTHENTICATION_BACKENDS there's more than one backend
            # configured, so login() can no longer infer which one to use.
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            from .services.email_verification import send_verification_email
            send_verification_email(user, request)
            if user.is_tester:
                messages.success(
                    request,
                    f'Welcome, {user.get_full_name() or user.email}! Your tester access '
                    f'is active — you\'ll see example stories on the story page and your '
                    f'promo code is ready at checkout.',
                )
            else:
                messages.success(request, f'Welcome, {user.get_full_name() or user.email}!')
            return redirect('documents:list')
    else:
        prefilled_ref = (
            request.GET.get('ref')
            or request.session.get('referral_code', '')
            or ''
        ).strip()
        form = RegisterForm(initial={'referral_code': prefilled_ref})

    return render(request, 'accounts/register.html', {
        'form': form,
        'prefilled_ref': prefilled_ref,
    })


def user_login(request):
    if request.user.is_authenticated:
        return redirect('documents:list')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'documents:list')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


@require_POST
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('public_pages:home')


@login_required
def pricing(request):
    return render(request, 'accounts/pricing.html')


@login_required
def profile(request):
    from django.conf import settings as dj_settings
    from documents.models import PromoCode, PartnershipRequest

    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            next_url = request.POST.get('next', '')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    subscriptions = request.user.subscriptions.order_by('-created_at')
    packs = request.user.document_packs.order_by('-created_at')

    partner_codes = []
    pending_partnership_request = None
    if request.user.is_revenue_partner:
        partner_codes = list(
            PromoCode.objects.filter(created_by=request.user, is_active=True).order_by('-created_at')
        )
    else:
        pending_partnership_request = (
            PartnershipRequest.objects
            .filter(user=request.user, status='pending')
            .order_by('-created_at')
            .first()
        )

    return render(request, 'accounts/profile.html', {
        'form': form,
        'subscriptions': subscriptions,
        'packs': packs,
        'next': next_url,
        'profile_incomplete': not request.user.has_complete_profile(),
        'partner_codes': partner_codes,
        'pending_partnership_request': pending_partnership_request,
        'partner_cut_percent': getattr(dj_settings, 'PARTNER_CUT_PERCENT', 20),
    })


@login_required
@require_POST
def request_partnership(request):
    from django.core.mail import send_mail
    from django.urls import reverse
    from django.conf import settings
    from documents.models import PartnershipRequest

    if request.user.is_revenue_partner:
        messages.info(request, 'You are already a partner.')
        return redirect('accounts:profile')

    existing = PartnershipRequest.objects.filter(user=request.user, status='pending').first()
    if existing:
        messages.info(request, 'Your partnership request is already pending review.')
        return redirect('accounts:profile')

    requested_code = (request.POST.get('requested_code') or '').strip()[:30]
    message = (request.POST.get('message') or '').strip()

    pr = PartnershipRequest.objects.create(
        user=request.user,
        requested_code=requested_code,
        message=message,
    )

    notify_to = getattr(settings, 'PARTNER_PAYOUT_NOTIFY_EMAIL', '') or settings.DEFAULT_FROM_EMAIL
    if notify_to:
        admin_url = request.build_absolute_uri(
            reverse('admin:documents_partnershiprequest_change', args=[pr.pk])
        )
        try:
            send_mail(
                subject=f'[file1983] New partnership request from {request.user.email}',
                message=(
                    f'User: {request.user.get_full_name() or request.user.email} ({request.user.email})\n'
                    f'Requested code: {requested_code or "(none specified)"}\n'
                    f'Message: {message or "(none)"}\n\n'
                    f'Review in admin: {admin_url}\n'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notify_to],
                fail_silently=True,
            )
        except Exception:
            pass

    messages.success(request, 'Partnership request submitted. We\'ll review it and get back to you by email.')
    return redirect('accounts:profile')


@login_required
@require_POST
def submit_feedback(request):
    from django.core.mail import send_mail
    from django.urls import reverse
    from django.conf import settings
    from documents.models import TesterFeedback

    message = (request.POST.get('message') or '').strip()
    category = request.POST.get('category') or 'other'
    if category not in dict(TesterFeedback.CATEGORY_CHOICES):
        category = 'other'
    page_url = (request.POST.get('page_url') or '').strip()[:500]
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'public_pages:home'

    if not message:
        messages.error(request, 'Please enter a message before submitting feedback.')
        return redirect(next_url)

    fb = TesterFeedback.objects.create(
        user=request.user,
        category=category,
        message=message,
        page_url=page_url,
    )

    notify_to = getattr(settings, 'PARTNER_PAYOUT_NOTIFY_EMAIL', '') or settings.DEFAULT_FROM_EMAIL
    if notify_to:
        admin_url = request.build_absolute_uri(
            reverse('admin:documents_testerfeedback_change', args=[fb.pk])
        )
        try:
            send_mail(
                subject=f'[file1983] New feedback ({fb.get_category_display()}) from {request.user.email}',
                message=(
                    f'User: {request.user.get_full_name() or request.user.email} ({request.user.email})\n'
                    f'Category: {fb.get_category_display()}\n'
                    f'Page: {page_url or "(unknown)"}\n\n'
                    f'{message}\n\n'
                    f'Review in admin: {admin_url}\n'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notify_to],
                fail_silently=True,
            )
        except Exception:
            pass

    messages.success(request, 'Thanks for the feedback — it\'s been sent to the team.')
    return redirect(next_url)


def verify_email(request, token):
    from .services.email_verification import verify_token, mark_verified

    user, error = verify_token(token)
    if error:
        messages.error(request, error)
        return redirect('accounts:profile' if request.user.is_authenticated else 'accounts:login')

    if not user.email_verified:
        mark_verified(user)
    messages.success(request, 'Email verified — you can now send Citizen Complaint Assistant emails.')
    return redirect('accounts:profile' if request.user.is_authenticated else 'accounts:login')


@login_required
@require_POST
@ratelimit(key='user', rate='5/h', method='POST', block=True)
def resend_verification(request):
    from .services.email_verification import send_verification_email

    if request.user.email_verified:
        messages.info(request, 'Your email is already verified.')
    else:
        send_verification_email(request.user, request)
        messages.success(request, f'Verification email sent to {request.user.email}.')
    next_url = request.POST.get('next') or 'accounts:profile'
    return redirect(next_url)


@login_required
@require_http_methods(['GET', 'POST'])
def accept_terms(request):
    """
    Re-acceptance gate. RequireLegalAcceptanceMiddleware redirects any
    authenticated user with stale tos/privacy versions here. Both checkboxes
    must be ticked to continue. On success we stamp the current timestamp +
    settings.TOS_VERSION / PRIVACY_VERSION onto the user.
    """
    user = request.user
    current_tos = getattr(dj_settings, 'TOS_VERSION', 'v1')
    current_privacy = getattr(dj_settings, 'PRIVACY_VERSION', 'v1')

    # If they're already up-to-date, don't keep them on this page.
    if not user.needs_legal_acceptance():
        return redirect('documents:list')

    tos_doc = LegalDocument.objects.filter(doc_type='terms').first()
    privacy_doc = LegalDocument.objects.filter(doc_type='privacy').first()

    error = ''
    if request.method == 'POST':
        tos_ok = bool(request.POST.get('tos_accepted'))
        privacy_ok = bool(request.POST.get('privacy_accepted'))
        if not (tos_ok and privacy_ok):
            error = 'You must check both boxes to continue.'
        else:
            now = timezone.now()
            user.tos_accepted_at = now
            user.tos_accepted_version = current_tos
            user.privacy_accepted_at = now
            user.privacy_accepted_version = current_privacy
            user.save(update_fields=[
                'tos_accepted_at', 'tos_accepted_version',
                'privacy_accepted_at', 'privacy_accepted_version',
            ])
            messages.success(request, 'Thank you. Your acceptance has been recorded.')
            return redirect('documents:list')

    # Distinguish first-time acceptance from re-acceptance for clearer copy.
    is_revision = bool(user.tos_accepted_version or user.privacy_accepted_version)

    return render(request, 'accounts/accept_terms.html', {
        'tos_doc': tos_doc,
        'privacy_doc': privacy_doc,
        'tos_version': current_tos,
        'privacy_version': current_privacy,
        'user_tos_version': user.tos_accepted_version,
        'user_privacy_version': user.privacy_accepted_version,
        'is_revision': is_revision,
        'error': error,
    })


@method_decorator(
    ratelimit(key='ip', rate='5/h', method='POST', block=True), name='dispatch'
)
class RateLimitedPasswordResetView(auth_views.PasswordResetView):
    """
    Password reset emails are easy to weaponize for mail-bombing or account
    enumeration timing if left unthrottled. Cap by IP.
    """


class LogoutOnPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Variant of Django's PasswordResetConfirmView that logs out the current
    user before showing the reset form. Avoids the confusing situation where
    a logged-in user clicks a reset link from email and ends up resetting
    a different account while still appearing as their own session.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return super().dispatch(request, *args, **kwargs)
