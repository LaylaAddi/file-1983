import secrets
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = [
        ('plaintiff', 'Plaintiff / Self-Represented'),
        ('attorney', 'Attorney'),
    ]

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # User type — plaintiff (self-represented) or attorney (future)
    user_type = models.CharField(
        max_length=20, choices=USER_TYPE_CHOICES, default='plaintiff'
    )

    # Contact / address — used to pre-populate PlaintiffInfo on new complaints
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)

    # Referral
    referral_code = models.CharField(max_length=16, unique=True, blank=True)
    referred_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals'
    )
    is_revenue_partner = models.BooleanField(
        default=False,
        help_text='Grants access to the /partner/ dashboard to view sales and request payouts.',
    )

    # Beta-tester flag. Toggled by admin (single click or bulk action) to grant
    # podcast volunteers and other invited testers access to the example-stories
    # autofill dropdown on the story page, without giving them is_staff (which
    # would also unlock the Django admin and the per-row Delete buttons).
    # `tester_granted_at` is auto-stamped by the admin action so you can sort
    # the user list by "granted in the last week" and revoke a cohort at once.
    is_tester = models.BooleanField(
        default=False,
        help_text='Grants test-mode features (example-stories autofill, "Test mode" navbar badge). '
                  'Lower-privilege than is_staff — safe to grant to recruited testers.',
    )
    tester_granted_at = models.DateTimeField(null=True, blank=True)

    # Legal acceptance audit trail. Versions are checked against the current
    # settings.TOS_VERSION / PRIVACY_VERSION; a mismatch forces re-acceptance
    # at /accounts/accept-terms/ before the user can use the app.
    tos_accepted_at = models.DateTimeField(null=True, blank=True)
    tos_accepted_version = models.CharField(max_length=20, blank=True)
    privacy_accepted_at = models.DateTimeField(null=True, blank=True)
    privacy_accepted_version = models.CharField(max_length=20, blank=True)

    # Email verification — required before a user can send a Citizen Complaint
    # Assistant email (agency inboxes are a spam-abuse surface). Not required
    # anywhere else in the app today.
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    def get_full_name(self):
        full = f'{self.first_name} {self.last_name}'.strip()
        return full or self.email

    def get_plaintiff_defaults(self):
        """
        Returns a dict that maps directly onto PlaintiffInfo fields.
        Called when creating a new Document to pre-populate Step 1 of the wizard.
        """
        return {
            'full_name': self.get_full_name(),
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'email': self.email,
            'filing_pro_se': self.user_type == 'plaintiff',
        }

    def has_complete_profile(self):
        """Returns True if the user has filled in enough info to start a complaint."""
        return bool(self.first_name and self.last_name and self.address and self.city and self.state)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = secrets.token_urlsafe(10)[:16]
        super().save(*args, **kwargs)

    # ---- Access helpers ----

    def has_active_subscription(self):
        return self.subscriptions.filter(
            status='active',
            current_period_end__gt=timezone.now()
        ).exists()

    def has_unlimited_access(self):
        return self.is_staff or self.is_superuser or self.has_active_subscription()

    def get_ai_uses_remaining(self):
        if self.has_unlimited_access():
            return 999
        used = sum(
            p.ai_uses_used for p in self.document_packs.filter(ai_uses_used__lt=models.F('ai_uses_total'))
        )
        total = self.document_packs.aggregate(t=models.Sum('ai_uses_total'))['t'] or 0
        used_total = self.document_packs.aggregate(u=models.Sum('ai_uses_used'))['u'] or 0
        return max(0, total - used_total)

    def can_create_document(self):
        if self.has_unlimited_access():
            return True
        return self.document_packs.filter(
            ai_uses_used__lt=models.F('ai_uses_total')
        ).exists()

    # ---- Legal acceptance ----

    def needs_legal_acceptance(self):
        """
        True when the user has never accepted the Terms or Privacy Policy, or
        when their last-accepted version is older than the current setting.
        Drives the re-acceptance gate middleware.
        """
        from django.conf import settings as dj_settings
        current_tos = getattr(dj_settings, 'TOS_VERSION', 'v1')
        current_privacy = getattr(dj_settings, 'PRIVACY_VERSION', 'v1')
        return (
            self.tos_accepted_version != current_tos
            or self.privacy_accepted_version != current_privacy
        )


class Subscription(models.Model):
    PLAN_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    stripe_subscription_id = models.CharField(max_length=100, unique=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='incomplete')
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.plan} ({self.status})'

    def is_active(self):
        return (
            self.status == 'active'
            and self.current_period_end
            and self.current_period_end > timezone.now()
        )


class DocumentPack(models.Model):
    PACK_CHOICES = [
        ('single', 'Single Document'),
        ('3pack', '3-Pack'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_packs')
    pack_type = models.CharField(max_length=20, choices=PACK_CHOICES)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_session_id = models.CharField(max_length=200, blank=True)
    ai_uses_total = models.PositiveIntegerField(default=1)
    ai_uses_used = models.PositiveIntegerField(default=0)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.pack_type} ({self.ai_uses_used}/{self.ai_uses_total} used)'

    def has_uses_remaining(self):
        return self.ai_uses_used < self.ai_uses_total


class SiteSettings(models.Model):
    """Singleton — use SiteSettings.get_solo()"""
    app_name = models.CharField(max_length=100, default='AuditFile 1983')
    header_app_name = models.CharField(max_length=100, default='AuditFile 1983')

    # Pricing (displayed on pricing page — kept in sync with Stripe)
    price_single = models.DecimalField(max_digits=8, decimal_places=2, default=49.00)
    price_3pack = models.DecimalField(max_digits=8, decimal_places=2, default=99.00)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=29.00)
    price_annual = models.DecimalField(max_digits=8, decimal_places=2, default=249.00)

    # Public contact info (rendered in the site footer)
    contact_email = models.EmailField(default='rights@auditfile1983.com', blank=True)
    contact_email_visible = models.BooleanField(default=True)
    contact_phone = models.CharField(max_length=40, default='555-555-1212', blank=True)
    contact_phone_visible = models.BooleanField(default=True)

    # Feature flags
    registration_open = models.BooleanField(default=True)
    stripe_live_mode = models.BooleanField(default=False)
    citizen_complaint_enabled = models.BooleanField(
        default=True,
        verbose_name='Citizen Complaint Assistant enabled',
        help_text=(
            'Uncheck to hide the Citizen Complaint Assistant from users: its nav '
            'links disappear and every /citizen-complaint/ URL returns 404. Nothing '
            'is deleted — existing incidents, drafts and sent complaints stay in the '
            'database untouched, and re-checking this restores the feature exactly '
            'as it was. Staff accounts can still reach the feature while it is off, '
            'so you can test before re-enabling it for everyone.'
        ),
    )
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return 'Site Settings'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class LegalDocument(models.Model):
    DOC_TYPES = [
        ('terms', 'Terms of Service'),
        ('privacy', 'Privacy Policy'),
        ('disclaimer', 'Legal Disclaimer'),
        ('cookies', 'Cookie Policy'),
    ]

    doc_type = models.CharField(max_length=20, choices=DOC_TYPES, unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text='HTML content')
    version = models.CharField(
        max_length=20,
        default='v1',
        help_text=(
            'Version label shown to users and stamped onto each acceptance. '
            'Bump this whenever the document changes substantively. For Terms '
            'and Privacy, also update settings.TOS_VERSION / PRIVACY_VERSION '
            'so existing users are forced to re-accept on next visit.'
        ),
    )
    effective_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.title} ({self.version})'
