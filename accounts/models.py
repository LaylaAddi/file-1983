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
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # Referral
    referral_code = models.CharField(max_length=16, unique=True, blank=True)
    referred_by = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals'
    )

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
    app_name = models.CharField(max_length=100, default='File 1983')
    header_app_name = models.CharField(max_length=100, default='File 1983')

    # Pricing (displayed on pricing page — kept in sync with Stripe)
    price_single = models.DecimalField(max_digits=8, decimal_places=2, default=49.00)
    price_3pack = models.DecimalField(max_digits=8, decimal_places=2, default=99.00)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=29.00)
    price_annual = models.DecimalField(max_digits=8, decimal_places=2, default=249.00)

    # Feature flags
    registration_open = models.BooleanField(default=True)
    stripe_live_mode = models.BooleanField(default=False)
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
    ]

    doc_type = models.CharField(max_length=20, choices=DOC_TYPES, unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text='HTML content')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
