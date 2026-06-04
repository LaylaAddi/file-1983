from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from .models import User, Subscription, DocumentPack, SiteSettings, LegalDocument


class PromoCodeUsageInline(admin.TabularInline):
    """Read-only view of promo codes this user redeemed (as a buyer)."""
    from documents.models import PromoCodeUsage as _PromoCodeUsage
    model = _PromoCodeUsage
    fk_name = 'user'
    extra = 0
    can_delete = False
    fields = ('promo_code', 'referrer_email', 'document', 'amount_dollars', 'used_at')
    readonly_fields = ('promo_code', 'referrer_email', 'document', 'amount_dollars', 'used_at')
    verbose_name = 'Promo code redeemed'
    verbose_name_plural = 'Promo codes redeemed'

    def has_add_permission(self, request, obj=None):
        return False

    def referrer_email(self, obj):
        return obj.promo_code.created_by.email if obj.promo_code and obj.promo_code.created_by else '—'
    referrer_email.short_description = 'Referrer'

    def amount_dollars(self, obj):
        return f'${(obj.amount_cents or 0) / 100:.2f}'
    amount_dollars.short_description = 'Paid'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'has_complete_profile', 'is_revenue_partner', 'is_tester', 'tos_accepted_version', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_revenue_partner', 'is_tester', 'tos_accepted_version', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = (
        'date_joined', 'referral_code',
        'tos_accepted_at', 'tos_accepted_version',
        'privacy_accepted_at', 'privacy_accepted_version',
        'tester_granted_at',
    )
    inlines = [PromoCodeUsageInline]
    actions = ['mark_as_tester', 'revoke_tester']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'user_type')}),
        ('Contact & Address', {
            'description': 'Used to pre-populate plaintiff information on new complaints.',
            'fields': ('phone', 'address', 'city', 'state', 'zip_code'),
        }),
        ('Referral', {'fields': ('referral_code', 'referred_by', 'is_revenue_partner')}),
        ('Tester Access', {
            'description': (
                'Grants test-mode features (example-stories autofill on the '
                'story page, "Test mode" badge in the navbar) without giving '
                'admin access. Use the bulk actions on the list view to '
                'mark/revoke a whole cohort after a testing round. '
                '`tester_granted_at` is auto-stamped when granted via the '
                'bulk action.'
            ),
            'fields': ('is_tester', 'tester_granted_at'),
        }),
        ('Legal Acceptance', {
            'description': (
                'Audit stamp of when this user agreed to the Terms of Service '
                'and Privacy Policy and which versions they agreed to. If the '
                'stored version is older than settings.TOS_VERSION / '
                'PRIVACY_VERSION the user is forced to re-accept on next visit.'
            ),
            'fields': (
                ('tos_accepted_at', 'tos_accepted_version'),
                ('privacy_accepted_at', 'privacy_accepted_version'),
            ),
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
    )

    @admin.action(description='Mark selected users as testers')
    def mark_as_tester(self, request, queryset):
        n = queryset.update(is_tester=True, tester_granted_at=timezone.now())
        self.message_user(request, f'Marked {n} user(s) as testers.')

    @admin.action(description='Revoke tester status from selected users')
    def revoke_tester(self, request, queryset):
        n = queryset.update(is_tester=False, tester_granted_at=None)
        self.message_user(request, f'Revoked tester status from {n} user(s).')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'user_type', 'is_staff'),
        }),
    )

    @admin.display(boolean=True, description='Profile complete?')
    def has_complete_profile(self, obj):
        return obj.has_complete_profile()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'current_period_end', 'created_at')
    list_filter = ('plan', 'status')
    search_fields = ('user__email', 'stripe_subscription_id')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(DocumentPack)
class DocumentPackAdmin(admin.ModelAdmin):
    list_display = ('user', 'pack_type', 'ai_uses_used', 'ai_uses_total', 'amount_paid', 'created_at')
    list_filter = ('pack_type',)
    search_fields = ('user__email', 'stripe_payment_intent_id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Branding', {'fields': ('app_name', 'header_app_name')}),
        ('Footer Contact', {
            'description': (
                'Email and phone shown in the site footer. Uncheck the '
                '"visible" box to hide a value site-wide without deleting it.'
            ),
            'fields': (
                ('contact_email', 'contact_email_visible'),
                ('contact_phone', 'contact_phone_visible'),
            ),
        }),
        ('Pricing', {'fields': ('price_single', 'price_3pack', 'price_monthly', 'price_annual')}),
        ('Feature Flags', {'fields': ('registration_open', 'stripe_live_mode', 'maintenance_mode', 'maintenance_message')}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ('doc_type', 'title', 'version', 'effective_date', 'updated_at')
    list_filter = ('doc_type',)
    readonly_fields = ('updated_at',)
    fieldsets = (
        (None, {
            'fields': ('doc_type', 'title', 'version', 'effective_date'),
            'description': (
                'Bump the version field whenever the content changes substantively. '
                'For terms / privacy, also update settings.TOS_VERSION / PRIVACY_VERSION '
                '(env vars on Render) so existing users are forced to re-accept on next visit.'
            ),
        }),
        ('Body (HTML)', {'fields': ('content',)}),
        ('Audit', {'fields': ('updated_at',)}),
    )
