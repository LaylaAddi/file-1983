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
    CaseLaw, PdfBranding,
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
        'code', 'created_by', 'discount_type', 'discount_value',
        'sales_count', 'total_revenue', 'partner_cut',
        'is_active', 'expires_at',
    ]
    list_filter = ['is_active', 'discount_type', 'created_by']
    search_fields = ['code', 'created_by__email']
    readonly_fields = ['times_used', 'created_at']
    actions = ['export_codes_csv']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _sales_count=Count('usages'),
            _total_revenue=Sum('usages__amount_cents'),
        )

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
    list_display = ['user', 'amount', 'status', 'requested_at']
    list_filter = ['status']
    search_fields = ['user__email']


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
