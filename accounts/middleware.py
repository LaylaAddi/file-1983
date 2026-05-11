"""
Force-redirect any authenticated user whose stored Terms-of-Service or
Privacy-Policy acceptance version doesn't match the current versions
(settings.TOS_VERSION / PRIVACY_VERSION) to the re-acceptance gate at
/accounts/accept-terms/ before they can use the rest of the site.

Skips paths the user must be able to reach in order to actually accept
(the gate itself, login/logout, password reset, the public legal pages so
they can read what they're agreeing to, the admin so staff can edit copy,
static files, and webhooks).
"""
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.conf import settings


class RequireLegalAcceptanceMiddleware:
    EXEMPT_PREFIXES = (
        '/accounts/accept-terms',
        '/accounts/login',
        '/accounts/logout',
        '/accounts/password-reset',
        '/accounts/reset',
        '/legal/',
        '/static/',
        '/stripe/webhook',
        '/robots.txt',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_check(request):
            try:
                user = request.user
            except AttributeError:
                user = None
            if user and user.is_authenticated and user.needs_legal_acceptance():
                try:
                    return redirect(reverse('accounts:accept_terms'))
                except NoReverseMatch:
                    pass
        return self.get_response(request)

    def _should_check(self, request):
        path = request.path
        if path.startswith(self.EXEMPT_PREFIXES):
            return False
        admin_url = getattr(settings, 'ADMIN_URL', 'manage-dev/')
        if not admin_url.startswith('/'):
            admin_url = '/' + admin_url
        if path.startswith(admin_url):
            return False
        return True
