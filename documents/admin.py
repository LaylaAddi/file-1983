import csv
from django.conf import settings
from django.contrib import admin
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.utils import timezone
from .models import (
    Document, WizardSession, PlaintiffInfo, IncidentOverview,
    TimelineEntry, Defendant, GovernmentEntity, ConstitutionalClaim,
    Evidence, Witness, Damages, PriorComplaints, ReliefSought,
    AIPrompt, PromoCode, PromoCodeUsage, PayoutRequest, ExampleStory,
    CaseLaw, PdfBranding, PartnerAdjustment, PartnershipRequest,
)


class WizardSessionInline(admin.StackedInline):
    model = WizardSession
    extra = 0
    readonly_fields = ['ai_extraction_attempted', 'ai_extraction_succeeded', 'ai_extraction_error']


class PlaintiffInfoInline(admin.StackedInline):
    model = PlaintiffInfo
    extra = 0


class IncidentOverviewInline(admin.StackedInline):
    model = IncidentOverview
    extra = 0


class TimelineEntryInline(admin.TabularInline):
    model = TimelineEntry
    extra = 1
    ordering = ['order']


class DefendantInline(admin.TabularInline):
    model = Defendant
    extra = 1


class GovernmentEntityInline(admin.StackedInline):
    model = GovernmentEntity
    extra = 0


class ConstitutionalClaimInline(admin.TabularInline):
    model = ConstitutionalClaim
    extra = 0


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 0


class WitnessInline(admin.TabularInline):
    model = Witness
    extra = 0


class DamagesInline(admin.StackedInline):
    model = Damages
    extra = 0


class PriorComplaintsInline(admin.StackedInline):
    model = PriorComplaints
    extra = 0


class ReliefSoughtInline(admin.StackedInline):
    model = ReliefSought
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['slug', 'user', 'title', 'payment_status', 'jury_trial_demand', 'created_at']
    list_filter = ['payment_status']
    search_fields = ['slug', 'user__email', 'title']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    inlines = [
        WizardSessionInline,
        PlaintiffInfoInline,
        IncidentOverviewInline,
        TimelineEntryInline,
        DefendantInline,
        GovernmentEntityInline,
        ConstitutionalClaimInline,
        EvidenceInline,
        WitnessInline,
        DamagesInline,
        PriorComplaintsInline,
        ReliefSoughtInline,
    ]


@admin.register(WizardSession)
class WizardSessionAdmin(admin.ModelAdmin):
    list_display = ['document', 'status', 'current_step', 'ai_extraction_succeeded', 'updated_at']
    list_filter = ['status', 'ai_extraction_succeeded']
    readonly_fields = ['ai_extraction_attempted', 'created_at', 'updated_at']
    search_fields = ['document__slug', 'document__user__email']


@admin.register(AIPrompt)
class AIPromptAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'is_active', 'updated_at']
    list_filter = ['is_active']


def _format_cents(c):
    return f'${(c or 0) / 100:.2f}'


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'assigned_to', 'discount_type', 'discount_value',
        'sales_count', 'total_revenue', 'partner_cut',
        'is_active', 'expires_at',
    ]
    list_filter = ['is_active', 'discount_type', 'created_by']
    search_fields = ['code', 'created_by__email']
    readonly_fields = ['times_used', 'created_at']
    actions = ['export_codes_csv']

    def assigned_to(self, obj):
        return obj.created_by.email if obj.created_by else '—'
    assigned_to.short_description = 'Assigned to'
    assigned_to.admin_order_field = 'created_by__email'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _sales_count=Count('usages'),
            _total_revenue=Sum('usages__amount_cents'),
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'created_by':
            from django.db.models import Q
            User = db_field.related_model
            kwargs['queryset'] = User.objects.filter(
                Q(is_revenue_partner=True) | Q(is_staff=True)
            ).order_by('email')
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
            formfield.label = 'Assign code to'
            formfield.help_text = 'Only users marked Is revenue partner (or staff) appear here.'
            return formfield
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def sales_count(self, obj):
        return obj._sales_count
    sales_count.short_description = 'Sales'
    sales_count.admin_order_field = '_sales_count'

    def total_revenue(self, obj):
        return _format_cents(obj._total_revenue)
    total_revenue.short_description = 'Total revenue'
    total_revenue.admin_order_field = '_total_revenue'

    def partner_cut(self, obj):
        cents = (obj._total_revenue or 0) * settings.PARTNER_CUT_PERCENT // 100
        return _format_cents(cents)
    partner_cut.short_description = f'Partner cut'

    def export_codes_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        response['Content-Disposition'] = f'attachment; filename="promo_codes_{ts}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Code', 'Created by', 'Discount type', 'Discount value',
            'Sales', 'Total revenue ($)', f'Partner cut {settings.PARTNER_CUT_PERCENT}% ($)',
            'Active', 'Created at',
        ])
        qs = queryset.annotate(
            _sales_count=Count('usages'),
            _total_revenue=Sum('usages__amount_cents'),
        )
        for pc in qs:
            revenue_cents = pc._total_revenue or 0
            cut_cents = revenue_cents * settings.PARTNER_CUT_PERCENT // 100
            writer.writerow([
                pc.code,
                pc.created_by.email if pc.created_by else '',
                pc.discount_type,
                pc.discount_value,
                pc._sales_count or 0,
                f'{revenue_cents / 100:.2f}',
                f'{cut_cents / 100:.2f}',
                'yes' if pc.is_active else 'no',
                pc.created_at.strftime('%Y-%m-%d') if pc.created_at else '',
            ])
        return response
    export_codes_csv.short_description = 'Export selected codes to CSV (with revenue + partner cut)'


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = ['used_at', 'promo_code', 'referrer', 'user', 'document_link', 'amount_paid', 'cut_owed']
    list_filter = ['promo_code', 'promo_code__created_by', 'used_at']
    search_fields = ['user__email', 'promo_code__code', 'document__slug']
    date_hierarchy = 'used_at'
    readonly_fields = ['used_at']
    actions = ['export_usages_csv']

    def referrer(self, obj):
        return obj.promo_code.created_by.email if obj.promo_code.created_by else '—'
    referrer.short_description = 'Referrer'
    referrer.admin_order_field = 'promo_code__created_by__email'

    def document_link(self, obj):
        return obj.document.slug if obj.document else '—'
    document_link.short_description = 'Document'

    def amount_paid(self, obj):
        return _format_cents(obj.amount_cents)
    amount_paid.short_description = 'Paid'
    amount_paid.admin_order_field = 'amount_cents'

    def cut_owed(self, obj):
        cents = (obj.amount_cents or 0) * settings.PARTNER_CUT_PERCENT // 100
        return _format_cents(cents)
    cut_owed.short_description = f'Partner cut'

    def export_usages_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        ts = timezone.now().strftime('%Y%m%d_%H%M')
        response['Content-Disposition'] = f'attachment; filename="promo_usages_{ts}.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'Used at', 'Code', 'Referrer', 'Buyer', 'Document slug',
            'Amount paid ($)', f'Partner cut {settings.PARTNER_CUT_PERCENT}% ($)',
        ])
        for u in queryset.select_related('promo_code', 'promo_code__created_by', 'user', 'document'):
            cut_cents = (u.amount_cents or 0) * settings.PARTNER_CUT_PERCENT // 100
            writer.writerow([
                u.used_at.strftime('%Y-%m-%d %H:%M'),
                u.promo_code.code,
                u.promo_code.created_by.email if u.promo_code.created_by else '',
                u.user.email,
                u.document.slug if u.document else '',
                f'{(u.amount_cents or 0) / 100:.2f}',
                f'{cut_cents / 100:.2f}',
            ])
        return response
    export_usages_csv.short_description = 'Export selected usages to CSV'


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'payment_processor', 'requested_at', 'paid_at']
    list_filter = ['status', 'payment_processor']
    search_fields = ['user__email', 'payment_reference']
    readonly_fields = ['requested_at', 'resolved_at', 'paid_at']
    date_hierarchy = 'requested_at'
    fieldsets = (
        ('Request', {
            'fields': ('user', 'amount', 'status', 'notes', 'requested_at'),
        }),
        ('Partner payment destination', {
            'description': 'Where the partner asked to be paid.',
            'fields': ('payment_processor', 'payment_method_details'),
        }),
        ('Admin payment record', {
            'description': 'Fill in once payment is sent. Saving with status=Paid will stamp paid_at automatically.',
            'fields': ('payment_reference', 'paid_at', 'admin_notes', 'resolved_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.status == 'paid' and obj.paid_at is None:
            obj.paid_at = timezone.now()
        if obj.status in ('paid', 'denied') and obj.resolved_at is None:
            obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(ExampleStory)
class ExampleStoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['title']


@admin.register(CaseLaw)
class CaseLawAdmin(admin.ModelAdmin):
    list_display = ['case_name', 'citation', 'category', 'year', 'is_active', 'order']
    list_filter = ['category', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['case_name', 'citation', 'holding_summary', 'why_it_matters']
    fieldsets = [
        ('Case Identification', {
            'fields': ['category', 'case_name', 'citation', 'court', 'year'],
        }),
        ('Content', {
            'fields': ['holding_summary', 'why_it_matters', 'key_quote', 'jurisdiction_notes'],
        }),
        ('Display', {
            'fields': ['is_active', 'order'],
        }),
    ]


@admin.register(PdfBranding)
class PdfBrandingAdmin(admin.ModelAdmin):
    list_display = ['name', 'watermark_text', 'website_url', 'is_active', 'updated_at']
    list_editable = ['is_active']
    fieldsets = [
        ('Identification', {
            'fields': ['name', 'is_active'],
            'description': 'Only one row should be active at a time. The active row is used '
                           'for every draft (unpaid) PDF. Edit the text below to change what '
                           'appears across the watermark and footer.',
        }),
        ('Watermark + Footer Text', {
            'fields': ['watermark_text', 'footer_text', 'website_url'],
        }),
    ]


@admin.register(PartnerAdjustment)
class PartnerAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount_dollars', 'reason', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'reason']
    readonly_fields = ['created_by', 'created_at']
    autocomplete_fields = ['user']

    def amount_dollars(self, obj):
        sign = '+' if obj.amount_cents >= 0 else '-'
        return f'{sign}${abs(obj.amount_cents) / 100:.2f}'
    amount_dollars.short_description = 'Amount'
    amount_dollars.admin_order_field = 'amount_cents'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            from django.db.models import Q
            User = db_field.related_model
            kwargs['queryset'] = User.objects.filter(
                Q(is_revenue_partner=True) | Q(is_staff=True)
            ).order_by('email')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.pk and obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PartnershipRequest)
class PartnershipRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'requested_code', 'status', 'created_at', 'resolved_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'requested_code']
    readonly_fields = ['user', 'requested_code', 'message', 'created_at', 'resolved_at']
    fieldsets = (
        ('Request', {
            'fields': ('user', 'requested_code', 'message', 'created_at'),
        }),
        ('Decision', {
            'fields': ('status', 'admin_notes', 'resolved_at'),
            'description': 'Setting status to Approved will automatically: '
                           '(1) flip the user\'s "Is revenue partner" flag, and '
                           '(2) create an active PromoCode assigned to them using the requested code '
                           '(or a unique fallback if that code is taken). '
                           'Discount: $50 fixed off (matches the $99 discounted price).',
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.status in ('approved', 'denied') and obj.resolved_at is None:
            obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)

        if obj.status == 'approved':
            self._grant_partnership(request, obj)

    def _grant_partnership(self, request, obj):
        from django.contrib import messages as admin_messages

        user = obj.user
        flipped = False
        if not user.is_revenue_partner:
            user.is_revenue_partner = True
            user.save(update_fields=['is_revenue_partner'])
            flipped = True

        code_value = self._unique_promo_code(obj.requested_code, user)
        existing = PromoCode.objects.filter(created_by=user, is_active=True).first()
        if existing:
            admin_messages.info(
                request,
                f'{user.email} already has active code "{existing.code}". No new code created.',
            )
        elif code_value:
            PromoCode.objects.create(
                code=code_value,
                discount_type='fixed',
                discount_value=50,
                is_active=True,
                created_by=user,
            )
            admin_messages.success(
                request,
                f'Created PromoCode "{code_value}" for {user.email} ($50 off, fixed).',
            )

        if flipped:
            admin_messages.success(request, f'Granted partner status to {user.email}.')

    def _unique_promo_code(self, requested, user):
        base = (requested or '').strip().upper()
        if not base:
            base = (user.email.split('@')[0] or 'PARTNER').upper()[:20]
        base = ''.join(c for c in base if c.isalnum() or c in ('_', '-'))[:25] or 'PARTNER'

        if not PromoCode.objects.filter(code__iexact=base).exists():
            return base
        for n in range(2, 100):
            candidate = f'{base}{n}'[:30]
            if not PromoCode.objects.filter(code__iexact=candidate).exists():
                return candidate
        return None
