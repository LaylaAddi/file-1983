"""
Stripe Checkout integration for single-document purchases.

Pricing: PRICE_FULL_CENTS by default; PRICE_DISCOUNTED_CENTS when a valid
PromoCode is applied. We validate the code in our DB and pass the final
amount inline to Stripe (no Stripe Coupon sync needed).

Referrer attribution rides on PromoCode.created_by — every PromoCodeUsage
row links code -> user -> document, so revenue per referrer is queryable.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

import stripe
from django.conf import settings
from django.urls import reverse

from documents.models import Document, PromoCode, PromoCodeUsage


def _stripe_client():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def lookup_promo_code(code: str) -> Optional[PromoCode]:
    """Case-insensitive lookup. Returns None if not found."""
    if not code:
        return None
    return PromoCode.objects.filter(code__iexact=code.strip()).first()


def validate_promo_for_user(code: str, user) -> dict:
    """
    Validate a code for a given user. Returns:
        {
          'valid': bool,
          'cents': int,             # final price after discount
          'original_cents': int,    # always PRICE_FULL_CENTS
          'message': str,           # human-friendly explanation
          'code': PromoCode | None,
        }
    """
    full = settings.PRICE_FULL_CENTS
    result = {
        'valid': False,
        'cents': full,
        'original_cents': full,
        'message': '',
        'code': None,
    }

    promo = lookup_promo_code(code)
    if promo is None:
        result['message'] = 'That code isn’t recognized.'
        return result

    if not promo.is_valid():
        result['message'] = 'That code is no longer active.'
        return result

    if PromoCodeUsage.objects.filter(promo_code=promo, user=user).exists():
        result['message'] = 'You’ve already used this code.'
        return result

    result['valid'] = True
    result['code'] = promo
    result['cents'] = _apply_discount(full, promo)
    result['message'] = f'Code applied — your price is ${result["cents"] / 100:.2f}.'
    return result


def _apply_discount(amount_cents: int, promo: PromoCode) -> int:
    """Compute the final cents after applying a promo code's discount."""
    if promo.discount_type == 'free':
        return 0
    if promo.discount_type == 'percent':
        # discount_value is 0-100
        pct = Decimal(promo.discount_value) / Decimal(100)
        discounted = Decimal(amount_cents) * (Decimal(1) - pct)
        return max(0, int(discounted.quantize(Decimal('1'))))
    if promo.discount_type == 'fixed':
        # discount_value is dollars; convert to cents
        off_cents = int(Decimal(promo.discount_value) * 100)
        return max(0, amount_cents - off_cents)
    return amount_cents


def create_checkout_session(*, document: Document, user, code: str, request) -> dict:
    """
    Create a Stripe Checkout Session for one document.

    Returns {'url': str, 'session_id': str, 'amount_cents': int, 'promo_id': int|None}
    Raises ValueError if the code was provided but invalid.
    """
    full = settings.PRICE_FULL_CENTS
    amount_cents = full
    promo_id = None

    if code:
        v = validate_promo_for_user(code, user)
        if not v['valid']:
            raise ValueError(v['message'] or 'Promo code is invalid.')
        amount_cents = v['cents']
        promo_id = v['code'].id if v['code'] else None

    success_path = reverse('documents:payment_success', args=[document.slug])
    cancel_path = reverse('documents:payment_cancel', args=[document.slug])

    success_url = request.build_absolute_uri(success_path) + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url = request.build_absolute_uri(cancel_path)

    client = _stripe_client()
    session = client.checkout.Session.create(
        mode='payment',
        payment_method_types=['card'],
        customer_email=user.email or None,
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f'Section 1983 Complaint — {document.title or document.slug}',
                    'description': 'Clean, watermark-free PDF of your complaint.',
                },
                'unit_amount': amount_cents,
            },
            'quantity': 1,
        }],
        metadata={
            'document_slug': document.slug,
            'user_id': str(user.id),
            'promo_code_id': str(promo_id) if promo_id else '',
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return {
        'url': session.url,
        'session_id': session.id,
        'amount_cents': amount_cents,
        'promo_id': promo_id,
    }
