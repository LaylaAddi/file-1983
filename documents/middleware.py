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
