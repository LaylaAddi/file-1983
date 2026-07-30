"""
Email verification for User accounts.

Only gate that depends on this today: sending a Citizen Complaint Assistant
email (agency inboxes are the abuse surface we're protecting). Login,
registration, and the §1983 wizard do not require a verified email.

Uses Django's signed, timestamped tokens (no extra model/table needed) —
the token embeds the user's pk + a hash of their current email, so it
naturally invalidates if the user changes their email address.
"""
import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

SALT = 'accounts.email_verification'
MAX_AGE_SECONDS = 60 * 60 * 24 * 3  # 3 days


def _signer():
    return signing.TimestampSigner(salt=SALT)


def make_token(user):
    return _signer().sign(f'{user.pk}:{user.email}')


def verify_token(token):
    """
    Returns (user, error) — user is None and error is a user-facing message
    on any failure (expired, tampered, unknown user, email changed since).
    """
    from ..models import User

    try:
        value = _signer().unsign(token, max_age=MAX_AGE_SECONDS)
    except signing.SignatureExpired:
        return None, 'This verification link has expired. Request a new one below.'
    except signing.BadSignature:
        return None, 'This verification link is invalid.'

    try:
        pk_str, email = value.split(':', 1)
        user = User.objects.get(pk=int(pk_str))
    except (ValueError, User.DoesNotExist):
        return None, 'This verification link is invalid.'

    if user.email != email:
        return None, 'This link was issued for a different email address. Request a new one below.'

    return user, None


def send_verification_email(user, request):
    """Send (or re-send) the verification email to `user`. Never raises up to
    the caller (mirrors the other transactional-notice sends in this app —
    partnership requests, feedback, payout requests), but DOES log the actual
    SMTP error to the `documents`/`django` logger so a "no email arrived"
    report is diagnosable from Render logs instead of vanishing silently."""
    token = make_token(user)
    path = reverse('accounts:verify_email', kwargs={'token': token})
    verify_url = request.build_absolute_uri(path)

    body = render_to_string('accounts/emails/verify_email.txt', {
        'user': user,
        'verify_url': verify_url,
    })
    try:
        send_mail(
            subject='Verify your email — AuditFile 1983',
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Failed to send verification email to %s', user.email)


def mark_verified(user):
    user.email_verified = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=['email_verified', 'email_verified_at'])
