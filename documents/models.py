import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_document_slug():
    """Generate a short random slug, e.g. nP27cOkr. Collision-checked at save time."""
    return secrets.token_urlsafe(6)


# ---------------------------------------------------------------------------
# Document (root object)
# ---------------------------------------------------------------------------

class Document(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('finalized', 'Finalized'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    slug = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=255, blank=True)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='draft'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title or "Untitled"} ({self.slug})'

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = generate_document_slug()
            while Document.objects.filter(slug=slug).exists():
                slug = generate_document_slug()
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('documents:detail', kwargs={'document_slug': self.slug})


# ---------------------------------------------------------------------------
# WizardSession — tracks where the user is in the 7-step wizard
# ---------------------------------------------------------------------------

class WizardSession(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('analyzed', 'Analyzed'),
        ('completed', 'Completed'),
    ]

    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='wizard_session'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='not_started'
    )
    current_step = models.PositiveSmallIntegerField(default=1)
    story_text = models.TextField(blank=True, help_text='Raw story entered by user — AI parses this into fields')
    ai_analysis = models.JSONField(default=dict, blank=True, help_text='Parsed AI output from story analysis')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'WizardSession for {self.document.slug} — step {self.current_step} ({self.status})'


# ---------------------------------------------------------------------------
# Step 2 — Plaintiff Information
# ---------------------------------------------------------------------------

class PlaintiffInfo(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='plaintiff_info'
    )
    full_name = models.CharField(max_length=255, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return f'Plaintiff: {self.full_name or "Unknown"}'


# ---------------------------------------------------------------------------
# Step 3 — Incident Overview
# ---------------------------------------------------------------------------

class IncidentOverview(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='incident_overview'
    )
    incident_date = models.DateField(null=True, blank=True)
    incident_time = models.TimeField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    federal_district_court = models.CharField(max_length=255, blank=True)
    court_confirmed = models.BooleanField(
        default=False, help_text='True once user has confirmed the court lookup result'
    )

    def __str__(self):
        return f'Incident: {self.city}, {self.state} on {self.incident_date}'


# ---------------------------------------------------------------------------
# Step 4 — Defendants (multiple per document)
# ---------------------------------------------------------------------------

class Defendant(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='defendants'
    )
    name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True, help_text='e.g. Officer, Detective, Warden')
    agency = models.CharField(max_length=255, blank=True, help_text='e.g. NYPD, Rikers Island DOC')
    badge_number = models.CharField(max_length=50, blank=True)
    order = models.PositiveSmallIntegerField(default=0, help_text='Display order')

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.name or "Unknown"} ({self.agency})'


# ---------------------------------------------------------------------------
# Step 4 — Incident Narrative
# ---------------------------------------------------------------------------

class IncidentNarrative(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='incident_narrative'
    )
    narrative = models.TextField(blank=True, help_text='Detailed description of what happened')

    def __str__(self):
        return f'Narrative for {self.document.slug}'


# ---------------------------------------------------------------------------
# Step 5 — Rights Violated (multiple per document)
# ---------------------------------------------------------------------------

class RightsViolated(models.Model):
    """
    Each record is one constitutional right/amendment the plaintiff is asserting.
    The wizard presents a checklist; AI pre-selects based on story analysis.
    """
    AMENDMENT_CHOICES = [
        ('1st', 'First Amendment — Freedom of Speech, Religion, Assembly'),
        ('4th', 'Fourth Amendment — Unreasonable Search and Seizure'),
        ('5th', 'Fifth Amendment — Due Process / Self-Incrimination'),
        ('6th', 'Sixth Amendment — Right to Counsel / Fair Trial'),
        ('8th', 'Eighth Amendment — Cruel and Unusual Punishment'),
        ('14th_due_process', 'Fourteenth Amendment — Due Process'),
        ('14th_equal_protection', 'Fourteenth Amendment — Equal Protection'),
        ('other', 'Other'),
    ]

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='rights_violated'
    )
    amendment = models.CharField(max_length=30, choices=AMENDMENT_CHOICES)
    description = models.TextField(
        blank=True, help_text='Optional detail about how this right was violated'
    )

    class Meta:
        unique_together = [('document', 'amendment')]

    def __str__(self):
        return f'{self.get_amendment_display()} — {self.document.slug}'


# ---------------------------------------------------------------------------
# Step 6 — Witnesses (multiple per document)
# ---------------------------------------------------------------------------

class Witness(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='witnesses'
    )
    name = models.CharField(max_length=255, blank=True)
    contact_info = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, help_text='What did this witness observe?')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'Witness: {self.name or "Unknown"}'


# ---------------------------------------------------------------------------
# Step 6 — Evidence (multiple per document)
# ---------------------------------------------------------------------------

class Evidence(models.Model):
    EVIDENCE_TYPE_CHOICES = [
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('medical_record', 'Medical Record'),
        ('other', 'Other'),
    ]

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='evidence'
    )
    evidence_type = models.CharField(max_length=30, choices=EVIDENCE_TYPE_CHOICES, default='other')
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='evidence/', blank=True, null=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = 'Evidence'

    def __str__(self):
        return f'{self.get_evidence_type_display()} — {self.document.slug}'


# ---------------------------------------------------------------------------
# Step 7 — Damages
# ---------------------------------------------------------------------------

class Damages(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='damages'
    )
    physical_injuries = models.TextField(blank=True)
    emotional_distress = models.TextField(blank=True)
    financial_losses = models.TextField(blank=True)
    other_damages = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Damages'

    def __str__(self):
        return f'Damages for {self.document.slug}'


# ---------------------------------------------------------------------------
# Step 7 — Prior Complaints
# ---------------------------------------------------------------------------

class PriorComplaints(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='prior_complaints'
    )
    filed_complaints = models.BooleanField(
        default=False, help_text='Has the plaintiff previously filed complaints about this or related incidents?'
    )
    description = models.TextField(blank=True, help_text='Describe prior complaints filed')
    outcomes = models.TextField(blank=True, help_text='What were the outcomes?')

    class Meta:
        verbose_name_plural = 'Prior Complaints'

    def __str__(self):
        return f'Prior Complaints for {self.document.slug}'


# ---------------------------------------------------------------------------
# Step 7 — Relief Sought
# ---------------------------------------------------------------------------

class ReliefSought(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='relief_sought'
    )
    monetary_damages = models.BooleanField(default=False)
    injunctive_relief = models.BooleanField(default=False)
    declaratory_relief = models.BooleanField(default=False)
    attorney_fees = models.BooleanField(default=False)
    other_relief = models.TextField(blank=True, help_text='Any additional relief requested')

    def __str__(self):
        return f'Relief Sought for {self.document.slug}'


# ---------------------------------------------------------------------------
# Admin-managed AI Prompts
# ---------------------------------------------------------------------------

class AIPrompt(models.Model):
    TASK_CHOICES = [
        ('story_parse', 'Story Parsing — extract fields from user story'),
        ('narrative_gen', 'Narrative Generation'),
        ('rights_analysis', 'Rights Violated Analysis'),
        ('damages_gen', 'Damages Section Generation'),
        ('relief_gen', 'Relief Sought Generation'),
        ('court_lookup', 'Federal Court Lookup Fallback'),
        ('section_gen', 'Generic Section Generation'),
    ]

    task_name = models.CharField(max_length=50, choices=TASK_CHOICES, unique=True)
    system_prompt = models.TextField()
    user_prompt_template = models.TextField(
        help_text='Use {placeholders} for dynamic values injected at runtime'
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'AIPrompt: {self.get_task_name_display()}'


# ---------------------------------------------------------------------------
# Promo Codes / Referral System
# ---------------------------------------------------------------------------

class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage Off'),
        ('fixed', 'Fixed Amount Off'),
        ('free', 'Free Access'),
    ]

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text='Percentage (0-100) or fixed dollar amount'
    )
    max_uses = models.PositiveIntegerField(default=0, help_text='0 = unlimited')
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='created_promo_codes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'PromoCode: {self.code}'

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_uses > 0 and self.times_used >= self.max_uses:
            return False
        return True


class PromoCodeUsage(models.Model):
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='promo_code_usages'
    )
    document = models.ForeignKey(
        Document, null=True, blank=True, on_delete=models.SET_NULL, related_name='promo_usages'
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('promo_code', 'user')]

    def __str__(self):
        return f'{self.user.email} used {self.promo_code.code}'


class PayoutRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('denied', 'Denied'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payout_requests'
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Payout {self.amount} for {self.user.email} ({self.status})'
