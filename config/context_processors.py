def site_settings(request):
    """
    Injects site-wide settings into every template context.
    SiteSettings model is added in Step 2. Until then, returns defaults.
    """
    from django.conf import settings as django_settings
    admin_url = getattr(django_settings, 'ADMIN_URL', 'manage-dev/')
    primary_domain = getattr(django_settings, 'PRIMARY_DOMAIN', 'auditfile1983.com')

    try:
        from accounts.models import SiteSettings
        settings_obj = SiteSettings.get_solo()
        return {
            'app_name': settings_obj.app_name,
            'header_app_name': settings_obj.header_app_name,
            'contact_email': settings_obj.contact_email if settings_obj.contact_email_visible else '',
            'contact_phone': settings_obj.contact_phone if settings_obj.contact_phone_visible else '',
            'ADMIN_URL': admin_url,
            'PRIMARY_DOMAIN': primary_domain,
        }
    except Exception:
        return {
            'app_name': 'AuditFile 1983',
            'header_app_name': 'AuditFile 1983',
            'contact_email': '',
            'contact_phone': '',
            'ADMIN_URL': admin_url,
            'PRIMARY_DOMAIN': primary_domain,
        }
