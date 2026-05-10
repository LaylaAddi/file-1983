"""
Capture ?ref=CODE on any request and store it in the session so the pay page
can pre-fill the promo input.

Behavior:
- Reads `ref` from request.GET on every request.
- Validates the code against PromoCode (active codes only). Invalid codes are
  ignored — we don't want to seed garbage that confuses the user at checkout.
- Skips capture for the buyer's own code (a partner-buyer testing their own
  link should not get their own discount).
- Latest valid ref wins — a new link clobbers an older one in the session.
"""
from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CaptureReferralMiddleware:
    SESSION_KEY = 'referral_code'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ref = (request.GET.get('ref') or '').strip()
        if ref:
            self._capture(request, ref)
        return self.get_response(request)

    def _capture(self, request, ref):
        # Lazy import — middleware loads before apps are fully ready otherwise.
        from documents.models import PromoCode

        try:
            code = PromoCode.objects.filter(code__iexact=ref, is_active=True).first()
        except Exception:
            return

        if not code:
            return

        # Don't seed a partner with their own code.
        if (
            request.user.is_authenticated
            and code.created_by_id == request.user.id
        ):
            return

        # Store the canonical (DB-cased) code so the pay page shows the right form.
        request.session[self.SESSION_KEY] = code.code


class CanonicalDomainMiddleware:
    """
    301-redirects any request whose host is not the canonical PRIMARY_DOMAIN
    to the same path on the canonical domain. Skips localhost, IP addresses,
    and *.onrender.com so dev and Render's internal health checks keep working.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.canonical = (getattr(settings, 'PRIMARY_DOMAIN', '') or '').lower().strip()

    def __call__(self, request):
        if not self.canonical or settings.DEBUG:
            return self.get_response(request)

        host = request.get_host().split(':', 1)[0].lower()

        if host == self.canonical:
            return self.get_response(request)

        # Skip non-public hosts so health checks and direct Render URLs keep working.
        if (
            host in ('localhost', '127.0.0.1')
            or host.endswith('.onrender.com')
            or host.replace('.', '').isdigit()
        ):
            return self.get_response(request)

        # Strip a leading "www." before comparing so www.canonical also matches.
        bare = host[4:] if host.startswith('www.') else host
        if bare == self.canonical:
            # User hit www.<canonical> — redirect to the bare canonical form.
            new_url = f'https://{self.canonical}{request.get_full_path()}'
            return HttpResponsePermanentRedirect(new_url)

        new_url = f'https://{self.canonical}{request.get_full_path()}'
        return HttpResponsePermanentRedirect(new_url)
