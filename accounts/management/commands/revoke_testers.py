"""Revoke tester status from accounts after a testing round closes.

Pair this with `python manage.py seed_tester_promo --deactivate --code ...`
to fully wind down a testing round: the promo command stops new signups
from getting free checkout, this command strips the flag from accounts
that already have it (removes the example-stories autofill + navbar badge,
no effect on their existing documents/payments).

Usage:
    python manage.py revoke_testers            # revoke all current testers
    python manage.py revoke_testers --dry-run   # preview who would be affected
"""
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Revoke is_tester status from all accounts currently flagged as testers.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List affected accounts without making changes.',
        )

    def handle(self, *args, **options):
        testers = User.objects.filter(is_tester=True)
        count = testers.count()

        if not count:
            self.stdout.write(self.style.WARNING('No tester accounts found.'))
            return

        if options['dry_run']:
            self.stdout.write(f'Would revoke is_tester from {count} account(s):')
            for email in testers.values_list('email', flat=True):
                self.stdout.write(f'  - {email}')
            return

        updated = testers.update(is_tester=False, tester_granted_at=None)
        self.stdout.write(self.style.SUCCESS(
            f'Revoked is_tester from {updated} account(s).'
        ))
