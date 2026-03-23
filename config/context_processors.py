def site_settings(request):
    """
    Injects site-wide settings into every template context.
    SiteSettings model is added in Step 2. Until then, returns defaults.
    """
    try:
        from accounts.models import SiteSettings
        settings_obj = SiteSettings.get_solo()
        return {
            'app_name': settings_obj.app_name,
            'header_app_name': settings_obj.header_app_name,
        }
    except Exception:
        return {
            'app_name': 'File 1983',
            'header_app_name': 'File 1983',
        }
