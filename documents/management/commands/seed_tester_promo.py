"""Seed a free-access promo code for testing.

Idempotent: re-running with the same code just refreshes its settings.
The default code includes a short random suffix on first creation so it
can't be guessed by visitors, then stays stable for the testing round.

Usage:
    python manage.py seed_tester_promo
    python manage.py seed_tester_promo --code TESTFREE-MYBATCH
    python manage.py seed_tester_promo --code TESTFREE-MYBATCH --deactivate

Print the resulting code at the end so the operator can copy/paste it
into the tester instructions.
"""
import secrets
from django.core.management.base import BaseCommand
from documents.models import PromoCode


def _default_code():
    return 'TESTFREE-' + secrets.token_hex(3).upper()


class Command(BaseCommand):
    help = 'Create or update a free-access promo code used for testing rounds.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            default=None,
            help='Promo code string. Defaults to TESTFREE-<random6>. Same '
                 'code on subsequent runs reuses the existing row.',
        )
        parser.add_argument(
            '--deactivate',
            action='store_true',
            help='Set is_active=False on the matching code instead of '
                 'creating/activating one. Use after a testing round closes.',
        )

    def handle(self, *args, **options):
        code = options['code'] or _default_code()

        if options['deactivate']:
            updated = PromoCode.objects.filter(code=code).update(is_active=False)
            if updated:
                self.stdout.write(self.style.WARNING(f'Deactivated promo: {code}'))
            else:
                self.stdout.write(self.style.ERROR(f'No promo code found with code={code}'))
            return

        promo, created = PromoCode.objects.get_or_create(
            code=code,
            defaults={
                'discount_type': 'free',
                'discount_value': 0,
                'max_uses': 0,
                'is_active': True,
            },
        )
        if not created:
            promo.discount_type = 'free'
            promo.discount_value = 0
            promo.is_active = True
            promo.save(update_fields=['discount_type', 'discount_value', 'is_active'])

        action = 'Created' if created else 'Refreshed'
        self.stdout.write(self.style.SUCCESS(
            f'{action} free-access promo code: {promo.code}\n'
            f'  is_active = {promo.is_active}\n'
            f'  times_used = {promo.times_used}\n'
            f'Share this code with testers. Run with --deactivate when the '
            f'testing round ends.'
        ))
