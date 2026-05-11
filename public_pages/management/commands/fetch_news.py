"""
Fetch the latest headlines from a curated list of constitutional-rights /
civil-liberties RSS feeds and upsert them into NewsItem.

Designed to be run on a Render Cron Job hourly:
    python manage.py fetch_news

Idempotent: uses NewsItem.url as the upsert key, so re-running the command
never produces duplicates. Per-feed failures (timeouts, malformed XML,
404s) are logged and skipped — one bad feed never breaks the run.

To add a feed: append a (source_name, url) tuple to FEEDS. Pick sources
that publish about civil rights, constitutional law, police accountability,
First Amendment auditing, qualified immunity, or related federal court
news. Avoid partisan editorial blogs; the landing page is meant to inform.
"""
from datetime import datetime, timezone as dt_timezone
import logging
import socket

import feedparser
from django.core.management.base import BaseCommand
from django.utils import timezone

from public_pages.models import NewsItem


log = logging.getLogger(__name__)


FEEDS = [
    ('ACLU',                    'https://www.aclu.org/news/feed'),
    ('EFF',                     'https://www.eff.org/rss/updates.xml'),
    ('FIRE',                    'https://www.thefire.org/feed'),
    ('Institute for Justice',   'https://ij.org/feed/'),
    ('Cato Institute',          'https://www.cato.org/rss/recent-op-eds.xml'),
    ('Reason',                  'https://reason.com/feed/'),
]

PER_FEED_LIMIT = 10        # only keep the latest N entries from each source
FETCH_TIMEOUT_SECONDS = 15


class Command(BaseCommand):
    help = 'Fetch constitutional-rights headlines from curated RSS feeds.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--purge-older-than-days',
            type=int,
            default=60,
            help='Delete NewsItem rows older than this many days (default: 60).',
        )

    def handle(self, *args, **options):
        socket.setdefaulttimeout(FETCH_TIMEOUT_SECONDS)
        total_new = 0
        total_updated = 0
        total_errors = 0

        for source_name, url in FEEDS:
            try:
                new, updated = self._fetch_one(source_name, url)
                total_new += new
                total_updated += updated
                self.stdout.write(
                    f'  {source_name}: {new} new, {updated} updated'
                )
            except Exception as exc:
                total_errors += 1
                log.exception('fetch_news failed for %s', source_name)
                self.stderr.write(
                    self.style.WARNING(f'  {source_name}: SKIPPED ({exc})')
                )

        purge_days = options['purge_older_than_days']
        if purge_days > 0:
            cutoff = timezone.now() - timezone.timedelta(days=purge_days)
            purged, _ = NewsItem.objects.filter(published_at__lt=cutoff).delete()
            if purged:
                self.stdout.write(f'Purged {purged} item(s) older than {purge_days} days.')

        self.stdout.write(self.style.SUCCESS(
            f'Done. {total_new} new, {total_updated} updated, {total_errors} feed error(s).'
        ))

    def _fetch_one(self, source_name, url):
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            raise RuntimeError(
                f'feed unreadable: {getattr(parsed, "bozo_exception", "no entries")}'
            )

        new = 0
        updated = 0
        for entry in parsed.entries[:PER_FEED_LIMIT]:
            link = (entry.get('link') or '').strip()
            title = (entry.get('title') or '').strip()
            if not link or not title:
                continue

            published_at = self._parse_published(entry)
            if not published_at:
                continue

            summary = (entry.get('summary') or '').strip()[:1000]

            obj, created = NewsItem.objects.update_or_create(
                url=link[:600],
                defaults={
                    'title': title[:400],
                    'source': source_name,
                    'published_at': published_at,
                    'summary': summary,
                },
            )
            if created:
                new += 1
            else:
                updated += 1
        return new, updated

    def _parse_published(self, entry):
        """
        feedparser puts parsed dates into entry.published_parsed (a
        time.struct_time, always UTC). Fall back to updated_parsed if the
        feed doesn't supply a publish date.
        """
        struct_time = entry.get('published_parsed') or entry.get('updated_parsed')
        if not struct_time:
            return None
        try:
            return datetime(*struct_time[:6], tzinfo=dt_timezone.utc)
        except (TypeError, ValueError):
            return None
