"""
Step 5 — Send.

Reuses the app's existing SMTP setup (same DEFAULT_FROM_EMAIL /
EMAIL_HOST_* settings the §1983 wizard and partner-payout notices already
use) — no new email provider.

Privacy rule: the user's logged-in account email must never appear in a
header the recipient agency can see. It always gets a private BCC copy;
Reply-To is only ever the user's separate, optional contact email, and is
omitted entirely when they chose to file anonymously.

From display name is "<how the citizen chose to identify themselves> via
AuditFile 1983" (e.g. "Jane Doe via AuditFile 1983", or "A concerned
citizen via AuditFile 1983" if filed anonymously) so it reads to the
recipient like it's from a constituent, not generic platform support mail —
the underlying address is unchanged (same DEFAULT_FROM_EMAIL as every other
transactional email in this app).
"""
from email.utils import formataddr, parseaddr

from django.conf import settings
from django.core.mail import EmailMessage


def _from_header(incident) -> str:
    raw_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1] or settings.DEFAULT_FROM_EMAIL
    display_name = f'{incident.display_name()} via AuditFile 1983'
    return formataddr((display_name, raw_address))


def send_complaint(incident, target_agency, complaint) -> tuple[bool, str, dict]:
    """
    Returns (ok, error, sent) where `sent` describes what actually went out.

    The third element is read back off the EmailMessage after a successful
    send rather than rebuilt by the caller, so the archived copy can't drift
    from the message the mailer used. Callers persist it onto the
    Complaint's sent_*_snapshot fields; it's empty on failure.
    """
    subject = f'Citizen Complaint — {target_agency.name} — {incident.video_title or incident.video_url}'

    email = EmailMessage(
        subject=subject,
        body=complaint.body,
        from_email=_from_header(incident),
        to=[target_agency.email],
        bcc=[incident.user.email],
    )
    if incident.privacy_level != 'anonymous' and incident.contact_email:
        email.reply_to = [incident.contact_email]

    try:
        email.send(fail_silently=False)
    except Exception as exc:
        return False, str(exc), {}

    return True, '', {
        'subject': email.subject,
        'body': email.body,
        'from_email': email.from_email,
        'to': ', '.join(email.to),
        'reply_to': ', '.join(email.reply_to or []),
        'bcc': ', '.join(email.bcc or []),
    }
