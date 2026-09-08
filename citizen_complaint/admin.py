from django.contrib import admin

from .models import Incident, Agency, TargetAgency, Complaint


class TargetAgencyInline(admin.TabularInline):
    model = TargetAgency
    extra = 0
    fields = ['name', 'contact_name', 'contact_title', 'email', 'role_description', 'source', 'confirmed']


class ComplaintInline(admin.TabularInline):
    model = Complaint
    extra = 0
    fields = ['target_agency', 'status', 'sent_at', 'recipient_email_snapshot']
    readonly_fields = ['sent_at', 'recipient_email_snapshot']


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['slug', 'user', 'video_title', 'video_platform', 'status', 'api_calls_used', 'created_at']
    list_filter = ['status', 'video_platform', 'privacy_level']
    search_fields = ['slug', 'user__email', 'video_url', 'video_title']
    readonly_fields = ['slug', 'api_calls_used', 'created_at', 'updated_at']
    inlines = [TargetAgencyInline, ComplaintInline]


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'jurisdiction', 'complaint_email', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'jurisdiction', 'complaint_email']


@admin.register(TargetAgency)
class TargetAgencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_name', 'email', 'incident', 'source', 'confirmed']
    list_filter = ['source', 'confirmed']
    search_fields = ['name', 'contact_name', 'email', 'incident__slug']


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['incident', 'target_agency', 'status', 'moderation_flagged', 'sent_at', 'created_at']
    list_filter = ['status', 'moderation_flagged']
    # Every sent_* field is written once at send and must never be editable —
    # they're the record of what the agency actually received.
    readonly_fields = [
        'sent_at', 'recipient_email_snapshot',
        'sent_subject_snapshot', 'sent_body_snapshot', 'sent_from_snapshot',
        'sent_reply_to_snapshot', 'sent_bcc_snapshot', 'sent_body_sha256',
        'sent_copy_intact',
        'moderation_checked_at', 'moderation_flagged', 'moderation_categories',
    ]

    @admin.display(description='Sent copy intact?')
    def sent_copy_intact(self, obj):
        """Re-hashes the stored sent body and compares it to the hash recorded
        at send time."""
        result = obj.sent_copy_matches_hash()
        if result is None:
            return '— (not sent, or sent before snapshots existed)'
        return 'Yes — matches the hash recorded at send time' if result else 'NO — stored copy does not match the send-time hash'
