"""
Stats helpers for the partner dashboard.

Pure read-only aggregation over PromoCode / PromoCodeUsage / PayoutRequest for
a single referrer User. The dashboard view consumes this dict and renders it.
"""
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum

from documents.models import PromoCode, PromoCodeUsage, PayoutRequest


def _cents_to_dollars(cents):
    return (Decimal(cents or 0) / Decimal(100)).quantize(Decimal('0.01'))


def get_partner_stats(user, recent_limit=50):
    """
    Returns a dict of stats for the given user's referral activity.

    Money values are returned in cents (int) and pre-formatted dollars (Decimal).
    """
    cut_pct = Decimal(getattr(settings, 'PARTNER_CUT_PERCENT', 20))

    codes = PromoCode.objects.filter(created_by=user).order_by('-created_at')

    sales_qs = (
        PromoCodeUsage.objects
        .filter(promo_code__created_by=user)
        .select_related('user', 'document', 'promo_code')
        .order_by('-used_at')
    )

    gross_cents = sales_qs.aggregate(total=Sum('amount_cents'))['total'] or 0
    sales_count = sales_qs.count()
    cut_cents = int((Decimal(gross_cents) * cut_pct / Decimal(100)).to_integral_value())

    recent_sales = []
    for sale in sales_qs[:recent_limit]:
        sale_cut_cents = int((Decimal(sale.amount_cents or 0) * cut_pct / Decimal(100)).to_integral_value())
        recent_sales.append({
            'used_at': sale.used_at,
            'buyer_name': sale.user.get_full_name() or '',
            'buyer_email': sale.user.email,
            'code': sale.promo_code.code,
            'amount_dollars': _cents_to_dollars(sale.amount_cents),
            'cut_dollars': _cents_to_dollars(sale_cut_cents),
        })

    payouts_qs = PayoutRequest.objects.filter(user=user).order_by('-requested_at')
    paid_out_dollars = payouts_qs.filter(status='paid').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    paid_out_cents = int((paid_out_dollars * Decimal(100)).to_integral_value())

    pending_dollars = payouts_qs.filter(status__in=['pending', 'approved']).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    pending_cents = int((pending_dollars * Decimal(100)).to_integral_value())

    unpaid_balance_cents = max(cut_cents - paid_out_cents - pending_cents, 0)
    has_open_request = payouts_qs.filter(status__in=['pending', 'approved']).exists()

    return {
        'cut_percent': cut_pct,
        'codes': codes,
        'sales_count': sales_count,
        'gross_cents': gross_cents,
        'gross_dollars': _cents_to_dollars(gross_cents),
        'cut_cents': cut_cents,
        'cut_dollars': _cents_to_dollars(cut_cents),
        'paid_out_cents': paid_out_cents,
        'paid_out_dollars': _cents_to_dollars(paid_out_cents),
        'pending_cents': pending_cents,
        'pending_dollars': _cents_to_dollars(pending_cents),
        'unpaid_balance_cents': unpaid_balance_cents,
        'unpaid_balance_dollars': _cents_to_dollars(unpaid_balance_cents),
        'recent_sales': recent_sales,
        'payouts': payouts_qs,
        'has_open_request': has_open_request,
    }
