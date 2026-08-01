"""
citizen_complaint — Citizen Complaint Assistant

Free feature: paste a video URL (YouTube, Rumble, etc.) documenting an
encounter with a government agency, and the app helps identify the
agencies involved, drafts a factual complaint email per agency, and sends
it after the user reviews and confirms every recipient and every draft.

WIZARD FLOW
-----------
Step 0 (intake):    video URL -> metadata + transcript + AI extraction -> Incident
Step 1 (agencies):  review/confirm/edit detected + looked-up + manually-added TargetAgency rows
Step 2 (about you): privacy level, optional contact info, personal note, tone
Step 3 (drafts):    one AI-drafted, user-editable Complaint per confirmed agency
Step 4 (send):      final confirm + send; Complaint rows flip to 'sent'

No parallel systems: reuses accounts.User, the existing login/registration
flow, and the same slug-per-record pattern documents.Document uses.
"""

import secrets

from django.conf import settings
from django.db import models


def generate_incident_slug():
    return secrets.token_urlsafe(6)


class Incident(models.Model):
    STATUS_CHOICES = [
        ('intake', 'Intake'),
        ('agencies_reviewed', 'Agencies Reviewed'),
        ('info_collected', 'Info Collected'),
        ('drafted', 'Drafted'),
        ('sent', 'Sent'),
    ]
    PLATFORM_CHOICES = [
        ('youtube', 'YouTube'),
        ('rumble', 'Rumble'),
        ('other', 'Other'),
    ]
    PRIVACY_CHOICES = [
        ('full_name', 'Include my full name'),
        ('first_name', 'First name only'),
        ('anonymous', 'Anonymous / concerned citizen'),
    ]
    TONE_CHOICES = [
        ('factual', 'Factual / Neutral'),
        ('firm', 'Firm / Direct'),
        ('concerned', 'Concerned Citizen'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='incidents',
    )
    slug = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='intake')
    current_step = models.PositiveSmallIntegerField(default=0)

    # Step 0 — video intake
    video_url = models.URLField(max_length=500)
    video_platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='other')
    video_title = models.CharField(max_length=500, blank=True)
    video_channel_name = models.CharField(max_length=255, blank=True)
    video_description = models.TextField(blank=True)
    metadata_json = models.JSONField(
        default=dict, blank=True,
        help_text='Raw metadata fetched from the platform (title, description, channel, etc.)',
    )
    transcript = models.TextField(
        blank=True,
        help_text='Auto-caption transcript fetched via Supadata, when available.',
    )
    extracted_data = models.JSONField(
        default=dict, blank=True,
        help_text=(
            'AI-extracted structured data. Shape: {"agencies": [str], '
            '"location": str, "incident_date": str, "contacts": [str], '
            '"summary": str, "agency_contacts": {agency_name: [{"name", "title", '
            '"email"}, ...]}, "regex": {...}}. agency_contacts is only populated '
            'for named officials whose email was regex-verified against the raw '
            'description/transcript text.'
        ),
    )
    extraction_error = models.TextField(blank=True)

    # Step 2 — user info & privacy
    privacy_level = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='full_name')
    user_city = models.CharField(max_length=100, blank=True)
    user_state = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(
        blank=True,
        help_text='Optional — where the agency can reply. Left blank (and omitted from '
                  'the email entirely) if privacy_level is anonymous.',
    )
    personal_note = models.TextField(
        blank=True,
        help_text='Optional free-text note injected into every draft so complaints vary '
                  'person-to-person instead of reading like an identical form letter.',
    )
    tone = models.CharField(max_length=20, choices=TONE_CHOICES, default='factual')

    # Abuse guardrails
    api_calls_used = models.PositiveIntegerField(
        default=0,
        help_text='Counts every paid/external call this incident has triggered — transcript '
                  'fetch, metadata fetch, GPT extraction, agency search, per-agency drafts.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.video_title or self.video_url} ({self.slug})'

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = generate_incident_slug()
            while Incident.objects.filter(slug=slug).exists():
                slug = generate_incident_slug()
            self.slug = slug
        super().save(*args, **kwargs)

    def api_quota_limit(self):
        return getattr(settings, 'CITIZEN_COMPLAINT_AI_QUOTA_PER_INCIDENT', 10)

    def api_calls_remaining(self):
        return max(0, self.api_quota_limit() - self.api_calls_used)

    def is_sent(self):
        return self.status == 'sent'

    def next_step_url_name(self):
        """Which wizard step a 'Continue' link on the My Complaints list
        should route to, based on how far this incident has gotten."""
        if self.status == 'sent':
            return 'citizen_complaint:sent'
        return {
            0: 'citizen_complaint:agencies',
            1: 'citizen_complaint:agencies',
            2: 'citizen_complaint:about_you',
            3: 'citizen_complaint:drafts',
            4: 'citizen_complaint:send',
        }.get(self.current_step, 'citizen_complaint:agencies')

    def display_name(self):
        """How the user identifies themselves in the drafted emails."""
        if self.privacy_level == 'anonymous':
            return 'A concerned citizen'
        if self.privacy_level == 'first_name':
            return self.user.first_name or 'A concerned citizen'
        return self.user.get_full_name()


class Agency(models.Model):
    """
    Curated agency directory, checked first before falling back to AI-assisted
    web lookup for a TargetAgency. Admin-managed, similar in spirit to
    documents.CaseLaw — a trusted dataset that beats an AI guess.
    """
    name = models.CharField(max_length=255)
    jurisdiction = models.CharField(
        max_length=255, blank=True,
        help_text='e.g. "Saint Louis, MO" or "Missouri" or "National"',
    )
    complaint_email = models.EmailField()
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Agencies'

    def __str__(self):
        return f'{self.name} ({self.jurisdiction})' if self.jurisdiction else self.name


class TargetAgency(models.Model):
    SOURCE_CHOICES = [
        ('detected', 'Detected from video'),
        ('db_match', 'Matched curated Agency DB'),
        ('description', 'Found in video description'),
        ('ai_lookup', 'AI-assisted web lookup'),
        ('manual', 'Manually added by user'),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='target_agencies')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    contact_name = models.CharField(
        max_length=255, blank=True,
        help_text='Named official this row targets (e.g. "Joseph A. Farrow"), when the video '
                  'description named a specific person rather than a general agency line.',
    )
    contact_title = models.CharField(
        max_length=255, blank=True,
        help_text='Title of contact_name (e.g. "Chief of Police"), as written in the source.',
    )
    role_description = models.CharField(
        max_length=255, blank=True,
        help_text='How this agency relates to the incident, e.g. "Venue — policy violation" '
                  'or "Responding police department — unlawful detention". Tailors the draft.',
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    confirmed = models.BooleanField(
        default=False,
        help_text='User has checked the send box and reviewed this recipient. '
                  'Never auto-sent without this.',
    )
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = 'Target agencies'

    def __str__(self):
        who = f'{self.name} ({self.contact_name})' if self.contact_name else self.name
        return f'{who} <{self.email or "no email"}> — {self.incident.slug}'

    def is_unverified(self):
        return self.source in ('detected', 'ai_lookup')

    def display_label(self):
        """Agency name plus, when present, the specific named official this row targets."""
        if self.contact_name:
            title = f', {self.contact_title}' if self.contact_title else ''
            return f'{self.contact_name}{title} — {self.name}'
        return self.name


class Complaint(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='complaints')
    target_agency = models.OneToOneField(TargetAgency, on_delete=models.CASCADE, related_name='complaint')
    body = models.TextField(blank=True, help_text='AI-drafted, user-editable complaint email body.')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    viewed_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Set the first time the user opens this draft for review. Send is '
                  'blocked until every selected draft has been viewed.',
    )
    recipient_email_snapshot = models.EmailField(
        blank=True,
        help_text='Email address actually used at send time — kept even if TargetAgency.email '
                  'is edited afterward, for an accurate audit trail.',
    )
    moderation_checked_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When this body was last screened by the OpenAI Moderation API before send.',
    )
    moderation_flagged = models.BooleanField(
        default=False,
        help_text='True if the last moderation check blocked this from sending '
                  '(threats/violence/harassment, or the check itself failed).',
    )
    moderation_categories = models.JSONField(
        default=list, blank=True,
        help_text='OpenAI moderation categories that were flagged, if any — for admin review.',
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'Complaint to {self.target_agency.name} — {self.incident.slug} ({self.status})'

    def is_sent(self):
        return self.status == 'sent'

    def has_been_viewed(self):
        return self.viewed_at is not None
