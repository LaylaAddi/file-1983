"""
Management command: test_gpt_extraction

Calls the GPT story extraction service in dry-run mode and prints
the raw API response + the parsed JSON to the terminal.
Nothing is saved to the database.

Usage:
    # Use example story #1 from the DB (default)
    python manage.py test_gpt_extraction

    # Use a specific example story by PK
    python manage.py test_gpt_extraction --example 3

    # Pipe in story text directly
    python manage.py test_gpt_extraction --story "On March 15 I was standing on the sidewalk..."

    # Show only the parsed JSON (no section headers/separators)
    python manage.py test_gpt_extraction --json-only

    # Show only a specific top-level section of the JSON
    python manage.py test_gpt_extraction --section defendants
    python manage.py test_gpt_extraction --section constitutional_claims
"""

import json
import os
import sys
import textwrap

from django.core.management.base import BaseCommand, CommandError


SECTIONS = [
    'document', 'plaintiff', 'incident', 'timeline', 'defendants',
    'government_entity', 'constitutional_claims', 'evidence',
    'witnesses', 'damages', 'relief', 'prior_complaints',
]

# Map section name → DB model name (for "would be saved as" display)
SECTION_MODEL_MAP = {
    'document':              'Document (title, jury_trial_demand)',
    'plaintiff':             'PlaintiffInfo',
    'incident':              'IncidentOverview',
    'timeline':              'TimelineEntry (one row per entry)',
    'defendants':            'Defendant (one row per defendant)',
    'government_entity':     'GovernmentEntity',
    'constitutional_claims': 'ConstitutionalClaim (one row per claim)',
    'evidence':              'Evidence (one row per item)',
    'witnesses':             'Witness (one row per witness)',
    'damages':               'Damages',
    'relief':                'ReliefSought',
    'prior_complaints':      'PriorComplaints',
}


class Command(BaseCommand):
    help = 'Test GPT story extraction (dry run — nothing is saved to the DB)'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '--story', type=str,
            help='Story text to send to GPT (use quotes around the text)',
        )
        group.add_argument(
            '--example', type=int, default=1, metavar='PK',
            help='PK of an ExampleStory row to use (default: 1)',
        )
        parser.add_argument(
            '--json-only', action='store_true',
            help='Print only the raw parsed JSON, no formatting',
        )
        parser.add_argument(
            '--section', type=str, choices=SECTIONS, metavar='SECTION',
            help=(
                f'Print only one top-level section of the result. '
                f'Choices: {", ".join(SECTIONS)}'
            ),
        )

    def handle(self, *args, **options):
        from django.conf import settings as django_settings

        # ------------------------------------------------------------------ #
        # 1. Check API key up front for a friendly error message              #
        # ------------------------------------------------------------------ #
        api_key = getattr(django_settings, 'OPENAI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
        if not api_key:
            raise CommandError(
                'OPENAI_API_KEY is not set.\n'
                'Add it to your .env file:  OPENAI_API_KEY=sk-...'
            )

        # ------------------------------------------------------------------ #
        # 2. Get story text                                                    #
        # ------------------------------------------------------------------ #
        story_text = options.get('story')

        if not story_text:
            pk = options['example']
            story_text, title = self._load_example_story(pk)

            if not options['json_only']:
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f'\nUsing example story #{pk}: "{title}"'
                ))

        if not story_text:
            raise CommandError('No story text provided and no example stories found in the DB.')

        # ------------------------------------------------------------------ #
        # 3. Show story preview                                                #
        # ------------------------------------------------------------------ #
        if not options['json_only']:
            self.stdout.write('\n' + '─' * 72)
            self.stdout.write(self.style.MIGRATE_HEADING('STORY (first 300 chars):'))
            self.stdout.write(textwrap.fill(story_text[:300], width=72) + ('…' if len(story_text) > 300 else ''))
            self.stdout.write('─' * 72)
            self.stdout.write(self.style.WARNING('\nSending to GPT-4o…\n'))

        # ------------------------------------------------------------------ #
        # 4. Call the service in dry-run mode                                 #
        # ------------------------------------------------------------------ #
        # Build a lightweight fake session so we can reuse the service
        class _FakeSession:
            story_text = None

        fake_session = _FakeSession()
        fake_session.story_text = story_text

        from documents.services.openai_service import extract_story
        ai_analysis, error = extract_story(fake_session, dry_run=True)

        if error:
            raise CommandError(f'GPT extraction failed:\n{error}')

        # ------------------------------------------------------------------ #
        # 5. Output                                                            #
        # ------------------------------------------------------------------ #
        if options['json_only']:
            self.stdout.write(json.dumps(ai_analysis, indent=2))
            return

        section_filter = options.get('section')

        if section_filter:
            self._print_section(section_filter, ai_analysis.get(section_filter))
        else:
            self._print_full_result(ai_analysis)

        self.stdout.write('\n' + self.style.SUCCESS('Done. Nothing was saved to the database.') + '\n')

    # ---------------------------------------------------------------------- #
    # Helpers                                                                 #
    # ---------------------------------------------------------------------- #

    def _load_example_story(self, pk):
        from documents.models import ExampleStory
        try:
            story = ExampleStory.objects.get(pk=pk)
            return story.story_text, story.title
        except ExampleStory.DoesNotExist:
            # Try the first active story
            story = ExampleStory.objects.filter(is_active=True).first()
            if story:
                self.stdout.write(
                    self.style.WARNING(f'Example #{pk} not found — using #{story.pk} instead.')
                )
                return story.story_text, story.title
            return None, None

    def _print_section(self, name, data):
        model_label = SECTION_MODEL_MAP.get(name, name)
        self.stdout.write('\n' + '─' * 72)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'SECTION: {name.upper()}  →  saves to: {model_label}'
        ))
        self.stdout.write('─' * 72)
        self.stdout.write(json.dumps(data, indent=2))

    def _print_full_result(self, ai_analysis):
        self.stdout.write('\n' + '=' * 72)
        self.stdout.write(self.style.MIGRATE_HEADING('GPT EXTRACTION RESULT'))
        self.stdout.write('=' * 72)

        for section in SECTIONS:
            data = ai_analysis.get(section)
            model_label = SECTION_MODEL_MAP.get(section, section)

            self.stdout.write('\n' + '─' * 72)
            self.stdout.write(
                self.style.MIGRATE_HEADING(f'[{section}]') +
                self.style.HTTP_INFO(f'  →  {model_label}')
            )
            self.stdout.write('─' * 72)

            if data is None:
                self.stdout.write(self.style.WARNING('  (null — nothing extracted)'))
            elif isinstance(data, list):
                if not data:
                    self.stdout.write(self.style.WARNING('  (empty list — nothing extracted)'))
                else:
                    for i, item in enumerate(data, 1):
                        self.stdout.write(f'  [{i}] ' + json.dumps(item, indent=6).lstrip())
            else:
                self.stdout.write(json.dumps(data, indent=2))
