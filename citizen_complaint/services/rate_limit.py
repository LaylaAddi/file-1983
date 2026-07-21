"""
Daily send/creation caps for the Citizen Complaint Assistant — separate from
the per-incident AI quota in api_quota.py. These guard two different abuse
shapes:

  - a user starting many new incidents without ever sending (still burns
    Supadata/OpenAI/Search credits per incident)
  - a user (or coordinated group) flooding one specific agency's inbox
"""
from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from citizen_complaint.models import Complaint, Incident


def _today_start():
    now = timezone.now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def incidents_started_today(user) -> int:
    return Incident.objects.filter(user=user, created_at__gte=_today_start()).count()


def can_start_incident(user) -> bool:
    limit = getattr(settings, 'CITIZEN_COMPLAINT_INCIDENTS_PER_USER_PER_DAY', 5)
    return incidents_started_today(user) < limit


def sends_today(user) -> int:
    return Complaint.objects.filter(
        target_agency__incident__user=user, status='sent', sent_at__gte=_today_start(),
    ).count()


def can_send(user) -> bool:
    limit = getattr(settings, 'CITIZEN_COMPLAINT_SENDS_PER_USER_PER_DAY', 5)
    return sends_today(user) < limit


def agency_sends_today(email: str) -> int:
    return Complaint.objects.filter(
        recipient_email_snapshot__iexact=email, status='sent', sent_at__gte=_today_start(),
    ).count()


def can_send_to_agency(email: str) -> bool:
    limit = getattr(settings, 'CITIZEN_COMPLAINT_AGENCY_SENDS_PER_DAY', 20)
    return agency_sends_today(email) < limit


def user_daily_cap_message():
    limit = getattr(settings, 'CITIZEN_COMPLAINT_SENDS_PER_USER_PER_DAY', 5)
    return f'You\'ve reached today\'s limit of {limit} complaints sent. Try again tomorrow.'


def incident_daily_cap_message():
    limit = getattr(settings, 'CITIZEN_COMPLAINT_INCIDENTS_PER_USER_PER_DAY', 5)
    return f'You\'ve reached today\'s limit of {limit} new incidents. Try again tomorrow.'


def agency_daily_cap_message(name: str):
    return (
        f'{name} has received the maximum number of complaints through this app today. '
        'Please try again tomorrow.'
    )
