def site_settings(request):
    """
    Injects site-wide settings into every template context.
    SiteSettings model is added in Step 2. Until then, returns defaults.
    """
    from django.conf import settings as django_settings
    admin_url = getattr(django_settings, 'ADMIN_URL', 'manage-dev/')

    try:
        from accounts.models import SiteSettings
        settings_obj = SiteSettings.get_solo()
        return {
            'app_name': settings_obj.app_name,
            'header_app_name': settings_obj.header_app_name,
            'ADMIN_URL': admin_url,
        }
    except Exception:
        return {
            'app_name': 'File 1983',
            'header_app_name': 'File 1983',
            'ADMIN_URL': admin_url,
        }
