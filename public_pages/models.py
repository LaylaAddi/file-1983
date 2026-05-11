from django.db import models
from django.urls import reverse


class NewsItem(models.Model):
    """
    Headline + link cached from a curated RSS feed. Populated by the
    `fetch_news` management command (run on a Render cron). Visible on the
    landing page's Latest Updates widget. Set is_visible=False in admin to
    hide anything off-topic that slips through without deleting the row
    (so we don't refetch it).
    """
    url = models.URLField(max_length=600, unique=True)
    title = models.CharField(max_length=400)
    source = models.CharField(max_length=100)
    published_at = models.DateTimeField()
    summary = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'News Item'
        verbose_name_plural = 'News Items'
        indexes = [models.Index(fields=['-published_at', 'is_visible'])]

    def __str__(self):
        return f'[{self.source}] {self.title[:80]}'


class CivilRightsPage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    hero_title = models.CharField(max_length=200, blank=True)
    hero_subtitle = models.TextField(blank=True)
    meta_description = models.TextField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    show_in_nav = models.BooleanField(default=True)
    nav_title = models.CharField(max_length=50, blank=True)

    CATEGORY_CHOICES = [
        ('rights', 'Know Your Rights'),
        ('legal', 'Legal Information'),
        ('action', 'Take Action'),
        ('resources', 'Resources'),
        ('auditors', 'First Amendment Auditors'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='rights')
    icon = models.CharField(max_length=50, default='bi-file-text')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = "Civil Rights Page"
        verbose_name_plural = "Civil Rights Pages"

    def __str__(self):
        status = "✓" if self.is_published else "✗"
        return f"[{status}] {self.title}"

    def get_absolute_url(self):
        return reverse('public_pages:cms_page', kwargs={'slug': self.slug})

    def get_nav_title(self):
        return self.nav_title or self.title

    def get_hero_title(self):
        return self.hero_title or self.title


class PageSection(models.Model):
    page = models.ForeignKey(CivilRightsPage, on_delete=models.CASCADE, related_name='sections')

    SECTION_TYPES = [
        ('hero', 'Hero Section'),
        ('content', 'Rich Text Content'),
        ('cards', 'Card Grid'),
        ('rights_cards', 'Rights Cards (with amendment badge)'),
        ('article_cards', 'Article Cards (with category badge)'),
        ('quote', 'Quote/Blockquote'),
        ('cta', 'Call to Action'),
        ('resources', 'Resource Links'),
        ('stats', 'Statistics Row'),
        ('two_column', 'Two Column Layout'),
        ('checklist', "Checklist (Do/Don't)"),
        ('alert', 'Alert/Notice Box'),
        ('accordion', 'Accordion/FAQ'),
    ]
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    title = models.CharField(max_length=200, blank=True)
    subtitle = models.TextField(blank=True)
    content = models.TextField(blank=True)
    content_secondary = models.TextField(blank=True)
    data = models.JSONField(blank=True, null=True)

    BACKGROUND_CHOICES = [
        ('light', 'White'),
        ('cream', 'Cream/Off-white'),
        ('blue', 'Light Blue'),
        ('dark', 'Dark (for CTAs)'),
    ]
    background = models.CharField(max_length=10, choices=BACKGROUND_CHOICES, default='light')
    css_class = models.CharField(max_length=100, blank=True)
    cta_text = models.CharField(max_length=100, blank=True)
    cta_url = models.CharField(max_length=200, blank=True)
    cta_icon = models.CharField(max_length=50, blank=True, default='bi-shield-check')
    cta_secondary_text = models.CharField(max_length=100, blank=True)
    cta_secondary_url = models.CharField(max_length=200, blank=True)
    quote_source = models.CharField(max_length=200, blank=True)

    ALERT_TYPES = [
        ('info', 'Info (Blue)'),
        ('warning', 'Warning (Yellow)'),
        ('danger', 'Danger (Red)'),
        ('success', 'Success (Green)'),
    ]
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPES, default='info')
    is_visible = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Page Section"
        verbose_name_plural = "Page Sections"

    def __str__(self):
        visible = "✓" if self.is_visible else "✗"
        return f"[{visible}] {self.page.title} - {self.get_section_type_display()}: {self.title or '(no title)'}"

    def get_background_class(self):
        mapping = {
            'light': 'section-light',
            'cream': 'section-cream',
            'blue': 'section-blue',
            'dark': 'cta-section',
        }
        return mapping.get(self.background, 'section-light')
