from django.contrib import admin
from .models import (
    Document, WizardSession, PlaintiffInfo, IncidentOverview,
    Defendant, IncidentNarrative, RightsViolated, Witness, Evidence,
    Damages, PriorComplaints, ReliefSought, AIPrompt,
    PromoCode, PromoCodeUsage, PayoutRequest,
)


class WizardSessionInline(admin.StackedInline):
    model = WizardSession
    extra = 0


class PlaintiffInfoInline(admin.StackedInline):
    model = PlaintiffInfo
    extra = 0


class IncidentOverviewInline(admin.StackedInline):
    model = IncidentOverview
    extra = 0


class DefendantInline(admin.TabularInline):
    model = Defendant
    extra = 1


class IncidentNarrativeInline(admin.StackedInline):
    model = IncidentNarrative
    extra = 0


class RightsViolatedInline(admin.TabularInline):
    model = RightsViolated
    extra = 0


class WitnessInline(admin.TabularInline):
    model = Witness
    extra = 0


class EvidenceInline(admin.TabularInline):
    model = Evidence
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
    list_display = ['slug', 'user', 'title', 'payment_status', 'created_at']
    list_filter = ['payment_status']
    search_fields = ['slug', 'user__email', 'title']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    inlines = [
        WizardSessionInline,
        PlaintiffInfoInline,
        IncidentOverviewInline,
        DefendantInline,
        IncidentNarrativeInline,
        RightsViolatedInline,
        WitnessInline,
        EvidenceInline,
        DamagesInline,
        PriorComplaintsInline,
        ReliefSoughtInline,
    ]


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
