"""
Documents app models — Section 1983 Complaint Wizard

WIZARD FLOW
-----------
Step 0 (Story):  User types or speaks their story on web or mobile.
                 Raw text stored in WizardSession.story_text.
                 AI parses it and writes structured output to WizardSession.ai_analysis (JSON).
                 That JSON is then used to pre-populate every model below.

Step 1:  Plaintiff Information      → PlaintiffInfo
Step 2:  Incident Overview          → IncidentOverview + TimelineEntry
Step 3:  Defendants                 → Defendant + GovernmentEntity
Step 4:  Constitutional Claims      → ConstitutionalClaim
Step 5:  Evidence & Witnesses       → Evidence + Witness
Step 6:  Damages & Relief           → Damages + ReliefSought
Step 7:  Review & Finalize

AI ANALYSIS JSON SHAPE (WizardSession.ai_analysis)
---------------------------------------------------
{
  "document": {
    "title": str,
    "jury_trial_demand": bool
  },
  "plaintiff": {
    "full_name": str, "address": str, "city": str, "state": str,
    "zip_code": str, "phone": str, "email": str,
    "filing_pro_se": bool,
    "attorney_name": str, "attorney_bar_number": str, "attorney_address": str
  },
  "incident": {
    "incident_date": "YYYY-MM-DD", "incident_time": "HH:MM",
    "address": str, "city": str, "state": str, "county": str,
    "location_description": str, "location_type": str,
    "is_public_forum": bool,
    "plaintiff_activity": str,
    "plaintiff_identified_themselves": bool, "identification_description": str,
    "force_used": bool, "equipment_seized_or_damaged": bool,
    "federal_district_court": str
  },
  "timeline": [
    {"order": int, "time_approximate": str, "actor": str, "action_description": str}
  ],
  "defendants": [
    {
      "full_name": str, "badge_number": str, "rank_title": str,
      "agency_name": str, "parent_government_entity": str, "agency_address": str,
      "capacity_sued": str, "acting_under_color_of_law": bool,
      "color_of_law_basis": str, "is_supervisor": bool
    }
  ],
  "government_entity": {
    "entity_name": str, "entity_address": str,
    "policy_or_custom_description": str
  },
  "constitutional_claims": [
    {"amendment": str, "how_violated": str}
  ],
  "evidence": [
    {
      "evidence_type": str, "description": str,
      "date_and_time": str, "recorded_by": str,
      "storage_location": str, "public_url": str,
      "defendant_aware_of_recording": bool
    }
  ],
  "witnesses": [
    {
      "full_name": str, "contact_info": str, "relationship_to_plaintiff": str,
      "what_they_witnessed": str, "has_video": bool, "willing_to_testify": bool
    }
  ],
  "damages": {
    "physical_injury_description": str, "emotional_distress_description": str,
    "lost_wages": str, "property_damage_amount": str, "punitive_basis": str
  },
  "relief": {
    "compensatory_damages": bool, "compensatory_amount": str,
    "punitive_damages": bool, "declaratory_judgment": bool,
    "injunctive_relief": bool, "attorney_fees": bool,
    "costs_of_suit": bool, "other_relief": str
  },
  "prior_complaints": {
    "filed_complaints": bool, "description": str, "outcomes": str
  }
}
"""

import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_document_slug():
    return secrets.token_urlsafe(6)


# ---------------------------------------------------------------------------
# Document — root record, owns the slug and payment state
# ---------------------------------------------------------------------------

class Document(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('finalized', 'Finalized'),
        ('expired', 'Expired'),
    ]

    CASELAW_STRATEGY_CHOICES = [
        ('none', 'No case law — pleads facts only'),
        ('inline', 'Light inline citations within the complaint'),
        ('memorandum', 'Separate memorandum of supporting authority'),
        ('appendix', 'Appendix attached to the complaint'),
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
    jury_trial_demand = models.BooleanField(
        default=True,
        help_text='Whether to include a jury trial demand in the complaint'
    )
    caselaw_strategy = models.CharField(
        max_length=20, choices=CASELAW_STRATEGY_CHOICES, default='none',
        help_text='How (if at all) supporting case law should appear in the final document'
    )
    factual_allegations_json = models.JSONField(
        default=dict, blank=True,
        help_text='AI-drafted (and user-edited) numbered factual allegations. '
                  'Shape: {"paragraphs": ["...", "..."]}.'
    )
    factual_allegations_drafted_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When the factual allegations were last (re)drafted or saved. '
                  'Compared against wizard_session.updated_at to detect stale drafts.'
    )
    previous_factual_allegations_json = models.JSONField(
        default=dict, blank=True,
        help_text='Snapshot of factual_allegations_json captured immediately '
                  'before the most recent regenerate, so users can undo. '
                  'Empty dict means no undo available.'
    )
    previous_factual_allegations_drafted_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When the snapshot in previous_factual_allegations_json was originally drafted.'
    )
    stripe_session_id = models.CharField(
        max_length=200, blank=True, default='', db_index=True,
        help_text='Stripe Checkout Session ID — set when payment lands. Used for webhook idempotency.'
    )
    paid_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When payment was confirmed by the Stripe webhook.'
    )
    ai_calls_used = models.PositiveIntegerField(
        default=0,
        help_text=(
            'AI quota used on this document (story extraction + draft '
            'regeneration + addendums). Resets to 0 on payment so paid '
            'users get a fresh AI_QUOTA_PAID budget.'
        )
    )
    locked_at = models.DateTimeField(
        null=True, blank=True,
        help_text=(
            'Set when the user clicks Finalize & Download. Locked '
            'documents are read-only — no wizard edits, no AI calls. '
            'Re-download is still allowed.'
        )
    )
    finalize_acknowledged_at = models.DateTimeField(
        null=True, blank=True,
        help_text=(
            'Audit stamp: when the user explicitly checked the '
            '"complete + understand editing will lock" box on the '
            'finalize confirmation page. Set together with locked_at.'
        )
    )
    download_disclaimer_acknowledged_at = models.DateTimeField(
        null=True, blank=True,
        help_text=(
            'Audit stamp: when the user explicitly checked the AI / not-a-lawyer '
            'disclaimer box on the finalize page. Mirrors the signup TOS checkbox '
            'so we have a per-document agreement on file at the moment the clean '
            'PDF is released.'
        )
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

    def is_locked(self):
        return self.locked_at is not None

    def ai_quota_limit(self):
        from django.conf import settings
        if self.payment_status in ('paid', 'finalized'):
            return settings.AI_QUOTA_PAID
        return settings.AI_QUOTA_FREE

    def ai_calls_remaining(self):
        return max(0, self.ai_quota_limit() - self.ai_calls_used)

    def ai_quota_state(self):
        used = self.ai_calls_used or 0
        limit = self.ai_quota_limit()
        return {
            'used': used,
            'limit': limit,
            'remaining': max(0, limit - used),
            'exhausted': used >= limit,
            'is_paid': self.payment_status in ('paid', 'finalized'),
        }

    def has_undo(self):
        """True when there's a previous draft snapshot the user could restore."""
        prev = (self.previous_factual_allegations_json or {}).get('paragraphs') or []
        return bool(prev)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('documents:detail', kwargs={'document_slug': self.slug})


# ---------------------------------------------------------------------------
# WizardSession — story input, AI output, step tracking
# ---------------------------------------------------------------------------

class WizardSession(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('analyzed', 'Analyzed'),     # AI has parsed story, fields pre-filled
        ('completed', 'Completed'),
    ]

    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='wizard_session'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='not_started'
    )
    current_step = models.PositiveSmallIntegerField(default=0)  # 0 = story input

    # Step 0: user's raw story (typed or transcribed from voice)
    story_text = models.TextField(
        blank=True,
        help_text='Raw story entered or dictated by user — AI parses this to pre-fill all wizard steps'
    )

    # AI extraction output — structured JSON matching the shape documented at top of file.
    # After AI runs, each wizard step reads from this to pre-populate its form.
    # User edits are saved directly to the related models, not back into this JSON.
    ai_analysis = models.JSONField(
        default=dict, blank=True,
        help_text='Structured data extracted by AI from story_text — used to pre-fill wizard steps'
    )

    # Story addendums — targeted snippets the user adds after the initial analysis
    # to fill in a specific category (officers, evidence, location, etc.). Each
    # entry is `{"category": str, "text": str, "applied_at": isoformat, "error": str}`.
    # Stored for audit; merging happens immediately into the related models.
    story_addendums = models.JSONField(
        default=list, blank=True,
        help_text='Per-category snippets the user dictated/typed after the initial analysis'
    )

    # Track whether AI extraction has run and succeeded
    ai_extraction_attempted = models.BooleanField(default=False)
    ai_extraction_succeeded = models.BooleanField(default=False)
    ai_extraction_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'WizardSession for {self.document.slug} — step {self.current_step} ({self.status})'


# ---------------------------------------------------------------------------
# Step 1 — Plaintiff Information
# ---------------------------------------------------------------------------

class PlaintiffInfo(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='plaintiff_info'
    )
    full_name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    # Pro se or represented
    filing_pro_se = models.BooleanField(
        default=True,
        help_text='Filing without an attorney'
    )
    attorney_name = models.CharField(max_length=255, blank=True)
    attorney_bar_number = models.CharField(max_length=100, blank=True)
    attorney_address = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f'Plaintiff: {self.full_name or "Unknown"}'


# ---------------------------------------------------------------------------
# Step 2 — Incident Overview
# ---------------------------------------------------------------------------

class IncidentOverview(models.Model):
    LOCATION_TYPE_CHOICES = [
        # Public outdoor spaces (traditional public forums)
        ('public_sidewalk', 'Public Sidewalk'),
        ('public_park', 'Public Park'),
        ('public_plaza', 'Public Plaza / Square'),
        ('public_parking_lot', 'Public Parking Lot'),
        ('roadway', 'Roadway / Highway'),
        ('traffic_stop', 'Traffic Stop (roadside)'),
        # Government buildings
        ('police_station', 'Police Station / Lobby'),
        ('sheriff_office', "Sheriff's Office / Lobby"),
        ('courthouse', 'Courthouse / Lobby'),
        ('city_hall', 'City / Town Hall'),
        ('county_building', 'County Government Building'),
        ('federal_building', 'Federal Building'),
        ('dmv', 'DMV / Motor Vehicle Office'),
        ('post_office', 'Post Office'),
        ('government_office', 'Other Government Office / Building'),
        # Public institutions
        ('public_school', 'Public School'),
        ('public_library', 'Public Library'),
        ('public_hospital', 'Public Hospital / Clinic'),
        ('jail', 'Jail / Detention Center'),
        ('prison', 'Prison / Correctional Facility'),
        # Transportation
        ('airport', 'Airport / Terminal'),
        ('transit_station', 'Train / Bus Station'),
        ('transit_vehicle', 'Bus / Train / Transit Vehicle'),
        ('personal_vehicle', 'Personal Vehicle'),
        # Private property
        ('private_residence', 'Private Residence'),
        ('private_business', 'Private Business / Store'),
        # Fallback
        ('other', 'Other'),
    ]

    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='incident_overview'
    )
    incident_date = models.DateField(null=True, blank=True)
    incident_time = models.TimeField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    location_description = models.TextField(blank=True)
    location_type = models.CharField(
        max_length=30, choices=LOCATION_TYPE_CHOICES, blank=True
    )
    is_public_forum = models.BooleanField(
        null=True, blank=True,
        help_text='Relevant to First Amendment forum analysis'
    )

    # What the plaintiff was doing — key for 1st Amendment and 4th Amendment framing
    plaintiff_activity = models.TextField(
        blank=True,
        help_text='What was the plaintiff doing at the time of the incident?'
    )
    plaintiff_identified_themselves = models.BooleanField(null=True, blank=True)
    identification_description = models.TextField(blank=True)

    # Force / property
    force_used = models.BooleanField(null=True, blank=True)
    equipment_seized_or_damaged = models.BooleanField(null=True, blank=True)

    # Court — populated via court lookup service or AI fallback
    federal_district_court = models.CharField(max_length=255, blank=True)
    court_confirmed = models.BooleanField(
        default=False,
        help_text='True once user has confirmed the court lookup result'
    )

    def __str__(self):
        return f'Incident: {self.city}, {self.state} on {self.incident_date}'


# ---------------------------------------------------------------------------
# Step 2 — Timeline Entries (ordered sequence of events)
# ---------------------------------------------------------------------------

class TimelineEntry(models.Model):
    """
    Ordered list of what happened. AI extracts these from the story.
    User can add, edit, reorder in the wizard.
    These become the factual allegations section of the complaint.
    """
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='timeline_entries'
    )
    order = models.PositiveSmallIntegerField(default=0)
    time_approximate = models.CharField(
        max_length=100, blank=True,
        help_text='e.g. "approximately 2:30 PM" or "after the arrest"'
    )
    actor = models.CharField(
        max_length=255, blank=True,
        help_text='Who performed this action — defendant name, "officers", "plaintiff", etc.'
    )
    action_description = models.TextField(
        help_text='What happened — one discrete event per entry'
    )

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'[{self.order}] {self.actor}: {self.action_description[:60]}'


# ---------------------------------------------------------------------------
# Step 3 — Defendants (multiple per document)
# ---------------------------------------------------------------------------

class Defendant(models.Model):
    CAPACITY_CHOICES = [
        ('individual', 'Individual Capacity'),
        ('official', 'Official Capacity'),
        ('both', 'Both Individual and Official Capacity'),
    ]

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='defendants'
    )
    full_name = models.CharField(max_length=255, blank=True)
    badge_number = models.CharField(max_length=50, blank=True)
    rank_title = models.CharField(
        max_length=255, blank=True,
        help_text='e.g. Officer, Detective, Sergeant, Warden'
    )
    agency_name = models.CharField(
        max_length=255, blank=True,
        help_text='e.g. NYPD, Rikers Island DOC'
    )
    parent_government_entity = models.CharField(
        max_length=255, blank=True,
        help_text='e.g. City of New York, Cook County'
    )
    agency_address = models.CharField(max_length=500, blank=True)

    # Legal capacity and color-of-law basis
    capacity_sued = models.CharField(
        max_length=20, choices=CAPACITY_CHOICES, default='both'
    )
    acting_under_color_of_law = models.BooleanField(
        default=True,
        help_text='The central element of a 1983 claim — defendant acted under state authority'
    )
    color_of_law_basis = models.TextField(
        blank=True,
        help_text='How this defendant was acting under color of law'
    )
    is_supervisor = models.BooleanField(
        default=False,
        help_text='Supervisor liability — knew of and failed to prevent subordinate violations'
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.full_name or "Unknown"} — {self.agency_name}'


# ---------------------------------------------------------------------------
# Step 3 — Government Entity (Monell claim)
# ---------------------------------------------------------------------------

class GovernmentEntity(models.Model):
    """
    Monell v. Department of Social Services — municipal liability.
    Plaintiff must show the constitutional violation resulted from
    an official policy, custom, or practice of the government entity.
    """
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='government_entity'
    )
    entity_name = models.CharField(
        max_length=255, blank=True,
        help_text='e.g. City of Chicago, Los Angeles County Sheriff\'s Department'
    )
    entity_address = models.CharField(max_length=500, blank=True)
    policy_or_custom_description = models.TextField(
        blank=True,
        help_text='Describe the policy, custom, or practice that caused the violation'
    )

    class Meta:
        verbose_name = 'Government Entity (Monell)'
        verbose_name_plural = 'Government Entities (Monell)'

    def __str__(self):
        return f'Gov Entity: {self.entity_name or "Unknown"}'


# ---------------------------------------------------------------------------
# Step 4 — Constitutional Claims (multiple per document)
# ---------------------------------------------------------------------------

class ConstitutionalClaim(models.Model):
    AMENDMENT_CHOICES = [
        ('1st', 'First Amendment — Freedom of Speech, Religion, Assembly, Press'),
        ('1st_retaliation', 'First Amendment — Retaliation for Protected Activity'),
        ('1st_prior_restraint', 'First Amendment — Prior Restraint'),
        ('1st_viewpoint', 'First Amendment — Viewpoint Discrimination'),
        ('4th_search', 'Fourth Amendment — Unreasonable Search'),
        ('4th_seizure', 'Fourth Amendment — Unreasonable Seizure of Person'),
        ('4th_property', 'Fourth Amendment — Unreasonable Seizure of Property'),
        ('4th_excessive_force', 'Fourth Amendment — Excessive Force'),
        ('5th_due_process', 'Fifth Amendment — Due Process'),
        ('5th_self_incrimination', 'Fifth Amendment — Self-Incrimination'),
        ('6th_counsel', 'Sixth Amendment — Right to Counsel'),
        ('8th_cruel', 'Eighth Amendment — Cruel and Unusual Punishment'),
        ('14th_due_process', 'Fourteenth Amendment — Due Process'),
        ('14th_equal_protection', 'Fourteenth Amendment — Equal Protection'),
        ('other', 'Other'),
    ]

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='constitutional_claims'
    )
    amendment = models.CharField(max_length=30, choices=AMENDMENT_CHOICES)
    how_violated = models.TextField(
        blank=True,
        help_text='Describe specifically how this right was violated'
    )

    class Meta:
        unique_together = [('document', 'amendment')]

    def __str__(self):
        return f'{self.get_amendment_display()} — {self.document.slug}'


# ---------------------------------------------------------------------------
# Case Law Library — curated real cases (admin-managed)
# ---------------------------------------------------------------------------

class CaseLaw(models.Model):
    """
    Curated database of real federal cases supporting Section 1983 claims.
    Admin-managed; seeded via fixture. Only real, verified citations — no
    AI-generated case law (hallucinated citations carry serious legal risk).
    Intended use: Step 4 will let users browse relevant cases per claim and
    select which to include as supporting authority in their complaint.
    """
    CATEGORY_CHOICES = [
        ('1st_recording', 'First Amendment — Right to Record Police'),
        ('1st_retaliation', 'First Amendment — Retaliation'),
        ('1st_general', 'First Amendment — General'),
        ('4th_excessive_force', 'Fourth Amendment — Excessive Force'),
        ('4th_seizure', 'Fourth Amendment — Seizure / Arrest'),
        ('4th_search', 'Fourth Amendment — Search'),
        ('14th_due_process', 'Fourteenth Amendment — Due Process'),
        ('14th_equal_protection', 'Fourteenth Amendment — Equal Protection'),
        ('qualified_immunity', 'Qualified Immunity'),
        ('monell', 'Monell / Municipal Liability'),
        ('section_1983_general', 'Section 1983 — General Principles'),
    ]

    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    case_name = models.CharField(
        max_length=255,
        help_text='e.g. "Glik v. Cunniffe"'
    )
    citation = models.CharField(
        max_length=255,
        help_text='e.g. "655 F.3d 78 (1st Cir. 2011)"'
    )
    court = models.CharField(
        max_length=255, blank=True,
        help_text='e.g. "U.S. Court of Appeals for the First Circuit"'
    )
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    holding_summary = models.TextField(
        help_text='Plain-English summary of what the case held'
    )
    why_it_matters = models.TextField(
        help_text='Why this matters for 1983 plaintiffs (especially auditors)'
    )
    key_quote = models.TextField(
        blank=True,
        help_text='Direct quote from the opinion (optional)'
    )
    jurisdiction_notes = models.TextField(
        blank=True,
        help_text='e.g. "Controlling in 1st Circuit; persuasive elsewhere"'
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'order', '-year']
        verbose_name = 'Case Law'
        verbose_name_plural = 'Case Law'

    def __str__(self):
        return f'{self.case_name}, {self.citation}'


# ---------------------------------------------------------------------------
# Step 5 — Evidence (multiple per document)
# ---------------------------------------------------------------------------

class Evidence(models.Model):
    EVIDENCE_TYPE_CHOICES = [
        ('video', 'Video'),
        ('photo', 'Photo'),
        ('police_report', 'Police Report'),
        ('body_cam', 'Body Camera Footage'),
        ('foia_request', 'FOIA Request / Response'),
        ('citation', 'Citation / Summons'),
        ('medical_record', 'Medical Record'),
        ('physical', 'Physical Evidence'),
        ('document', 'Document'),
        ('other', 'Other'),
    ]

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='evidence'
    )
    evidence_type = models.CharField(
        max_length=30, choices=EVIDENCE_TYPE_CHOICES, default='other'
    )
    description = models.TextField(blank=True)
    date_and_time = models.CharField(
        max_length=100, blank=True,
        help_text='Approximate date/time this evidence was created or captured'
    )
    recorded_by = models.CharField(max_length=255, blank=True)
    storage_location = models.CharField(
        max_length=500, blank=True,
        help_text='Where is this evidence stored? e.g. phone, cloud, attorney office'
    )
    public_url = models.URLField(
        blank=True,
        help_text='Public URL if evidence is accessible online (e.g. YouTube)'
    )
    key_timestamp = models.CharField(
        max_length=20, blank=True,
        help_text='HH:MM:SS timestamp into the recording where the key moment '
                  'happens — so the judge knows when to start watching.'
    )
    defendant_aware_of_recording = models.BooleanField(
        null=True, blank=True,
        help_text='Relevant to First Amendment retaliation claims'
    )
    file = models.FileField(upload_to='evidence/', blank=True, null=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = 'Evidence'

    def __str__(self):
        return f'{self.get_evidence_type_display()} — {self.document.slug}'


# ---------------------------------------------------------------------------
# Step 5 — Witnesses (multiple per document)
# ---------------------------------------------------------------------------

class Witness(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='witnesses'
    )
    full_name = models.CharField(max_length=255, blank=True)
    contact_info = models.CharField(max_length=255, blank=True)
    relationship_to_plaintiff = models.CharField(
        max_length=255, blank=True,
        help_text='e.g. bystander, friend, fellow protestor, coworker'
    )
    what_they_witnessed = models.TextField(blank=True)
    has_video = models.BooleanField(
        null=True, blank=True,
        help_text='Did this witness capture video of the incident?'
    )
    willing_to_testify = models.BooleanField(null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'Witness: {self.full_name or "Unknown"}'


# ---------------------------------------------------------------------------
# Step 6 — Damages
# ---------------------------------------------------------------------------

class Damages(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='damages'
    )
    physical_injury_description = models.TextField(blank=True)
    emotional_distress_description = models.TextField(blank=True)
    lost_wages = models.TextField(
        blank=True,
        help_text='Description of lost wages or income, e.g. "Missed 2 work shifts, approx $300"'
    )
    property_damage_amount = models.TextField(
        blank=True,
        help_text='Description of property damage, e.g. "Phone screen cracked, replacement ~$200"'
    )
    punitive_basis = models.TextField(
        blank=True,
        help_text='Basis for punitive damages — describe the malicious or reckless conduct'
    )

    class Meta:
        verbose_name_plural = 'Damages'

    def __str__(self):
        return f'Damages for {self.document.slug}'


# ---------------------------------------------------------------------------
# Step 6 — Prior Complaints
# ---------------------------------------------------------------------------

class PriorComplaints(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='prior_complaints'
    )
    filed_complaints = models.BooleanField(
        default=False,
        help_text='Has the plaintiff previously filed complaints about this or related incidents?'
    )
    description = models.TextField(blank=True)
    outcomes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Prior Complaints'

    def __str__(self):
        return f'Prior Complaints for {self.document.slug}'


# ---------------------------------------------------------------------------
# Step 6 — Relief Sought
# ---------------------------------------------------------------------------

class ReliefSought(models.Model):
    document = models.OneToOneField(
        Document, on_delete=models.CASCADE, related_name='relief_sought'
    )
    compensatory_damages = models.BooleanField(default=False)
    compensatory_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    punitive_damages = models.BooleanField(default=False)
    declaratory_judgment = models.BooleanField(default=False)
    injunctive_relief = models.BooleanField(default=False)
    attorney_fees = models.BooleanField(default=False)
    costs_of_suit = models.BooleanField(default=False)
    other_relief = models.TextField(blank=True)

    def __str__(self):
        return f'Relief Sought for {self.document.slug}'


# ---------------------------------------------------------------------------
# Admin-managed AI Prompts
# ---------------------------------------------------------------------------

class AIPrompt(models.Model):
    TASK_CHOICES = [
        ('story_parse', 'Story Parsing — extract all fields from user story'),
        ('narrative_gen', 'Narrative / Factual Allegations Generation'),
        ('claims_analysis', 'Constitutional Claims Analysis'),
        ('damages_gen', 'Damages Section Generation'),
        ('relief_gen', 'Relief Sought Generation'),
        ('court_lookup', 'Federal Court Lookup Fallback'),
        ('monell_gen', 'Monell / Government Entity Section Generation'),
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
# Promo Codes / Referral / Payouts
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
    amount_cents = models.PositiveIntegerField(
        default=0,
        help_text='Final price the buyer paid (in cents) — captured for partner-cut accounting.'
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

    PROCESSOR_CHOICES = [
        ('paypal', 'PayPal'),
        ('venmo', 'Venmo'),
        ('zelle', 'Zelle'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payout_requests'
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_processor = models.CharField(
        max_length=20, choices=PROCESSOR_CHOICES, blank=True,
        help_text='How the partner wants to be paid.',
    )
    payment_method_details = models.TextField(
        blank=True,
        help_text='Partner-supplied destination — PayPal email, Venmo handle, Zelle phone/email, mailing address for check, etc.',
    )
    payment_reference = models.CharField(
        max_length=120, blank=True,
        help_text='Admin-recorded transaction ID, check number, or confirmation reference once paid.',
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text='Partner-facing note left at request time.')
    admin_notes = models.TextField(blank=True, help_text='Internal admin notes; not shown to the partner.')
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'Payout {self.amount} for {self.user.email} ({self.status})'


class PartnerAdjustment(models.Model):
    """
    Admin-created credit/debit on a partner's balance. Positive amounts add to
    the unpaid balance (bonus, correction); negative amounts subtract (refund
    clawback, error correction). Sums into partner_stats.cut_cents.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partner_adjustments'
    )
    amount_cents = models.IntegerField(
        help_text='Positive to add, negative to subtract. Stored in cents.'
    )
    reason = models.CharField(
        max_length=255,
        help_text='Short visible reason (the partner will see this label).',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='created_partner_adjustments',
        help_text='Admin who created this adjustment.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount_cents >= 0 else ''
        return f'{sign}${self.amount_cents / 100:.2f} for {self.user.email} ({self.reason})'


class PartnershipRequest(models.Model):
    """
    A user-submitted request to become a revenue partner. Includes the code
    they want assigned (subject to admin approval / availability).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partnership_requests'
    )
    requested_code = models.CharField(
        max_length=30, blank=True,
        help_text='Code the user wants for their referral branding.',
    )
    message = models.TextField(blank=True, help_text='Optional message from the user.')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} → "{self.requested_code or "(no code)"}" ({self.status})'


# ---------------------------------------------------------------------------
# Example Stories — for testing/demo (staff-only dropdown in wizard)
# ---------------------------------------------------------------------------

class ExampleStory(models.Model):
    """
    Pre-written auditor scenarios shown as a dropdown on the story input step.
    Only visible to staff users and in DEBUG mode — for testing the AI extraction
    pipeline without having to type a story every time.
    Admin-managed so new scenarios can be added without a code deploy.
    """
    title = models.CharField(max_length=200, help_text='Short label shown in the dropdown')
    story_text = models.TextField(help_text='Full story text — loaded into the story textarea when selected')
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Example Story'
        verbose_name_plural = 'Example Stories'

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# PDF Branding — admin-editable watermark + footer text shown on draft PDFs
# ---------------------------------------------------------------------------

class PdfBranding(models.Model):
    """
    Admin-editable copy used on draft (unpaid) PDF complaints. Singleton-style:
    only the row marked is_active=True is read at render time. If no active row
    exists, the model's defaults are used.
    """
    name = models.CharField(
        max_length=50, default='default', unique=True,
        help_text='Internal label so you can keep multiple drafts and toggle '
                  '`is_active` to swap between them.'
    )
    watermark_text = models.TextField(
        default='DRAFT\nNOT FOR FILING',
        help_text='Diagonal watermark stamped across every page of unpaid PDFs. '
                  'Newlines render as line breaks so the text wraps cleanly.'
    )
    footer_text = models.CharField(
        max_length=255,
        default='Draft preview — upgrade at www.file1983.com to download a clean copy.',
        help_text='Footer line shown at the bottom of every page of unpaid PDFs.'
    )
    website_url = models.CharField(
        max_length=255,
        default='www.file1983.com',
        help_text='Site URL shown alongside the watermark/footer.'
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'PDF Branding'
        verbose_name_plural = 'PDF Branding'

    def __str__(self):
        return f'PDF Branding ({self.name})'

    @classmethod
    def get_active(cls):
        """Return the active branding row, or an unsaved default if none exist."""
        obj = cls.objects.filter(is_active=True).order_by('-updated_at').first()
        return obj or cls(name='default')
