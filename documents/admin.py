from django.contrib import admin
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


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'times_used', 'max_uses', 'is_active', 'expires_at']
    list_filter = ['is_active', 'discount_type']
    search_fields = ['code']


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = ['promo_code', 'user', 'used_at']
    search_fields = ['user__email', 'promo_code__code']


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
