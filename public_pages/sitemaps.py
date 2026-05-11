"""
Sitemap definitions for /sitemap.xml.

Includes only public, indexable pages:
- Static landing + know-your-rights pages
- Legal pages (terms, privacy, disclaimer, cookies)
- Published CMS pages (CivilRightsPage with is_published=True)

Explicitly excludes:
- Account pages (login, register, profile, password reset)
- Document wizard + payment flow
- Stripe webhook
- Admin
- API
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import CivilRightsPage


class StaticPagesSitemap(Sitemap):
    """Hand-curated list of evergreen public URLs."""
    protocol = 'https'

    def items(self):
        return [
            ('public_pages:home',                    1.0, 'weekly'),
            ('public_pages:know_your_rights',        0.9, 'monthly'),
            ('public_pages:right_to_record',         0.9, 'monthly'),
            ('public_pages:section_1983',            0.9, 'monthly'),
            ('public_pages:rights_violated',         0.8, 'monthly'),
            ('public_pages:first_amendment_auditors', 0.8, 'monthly'),
            ('public_pages:fourth_amendment',        0.8, 'monthly'),
            ('public_pages:fifth_amendment',         0.8, 'monthly'),
        ]

    def location(self, obj):
        return reverse(obj[0])

    def priority(self, obj):
        return obj[1]

    def changefreq(self, obj):
        return obj[2]


class LegalPagesSitemap(Sitemap):
    """Terms, privacy, disclaimer, cookies."""
    changefreq = 'yearly'
    priority = 0.3
    protocol = 'https'

    def items(self):
        return [
            'public_pages:terms',
            'public_pages:privacy',
            'public_pages:disclaimer',
            'public_pages:cookies',
        ]

    def location(self, obj):
        return reverse(obj)


class CMSPageSitemap(Sitemap):
    """Published CivilRightsPage rows authored via admin."""
    changefreq = 'monthly'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return CivilRightsPage.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


SITEMAPS = {
    'static': StaticPagesSitemap,
    'legal': LegalPagesSitemap,
    'pages': CMSPageSitemap,
}
