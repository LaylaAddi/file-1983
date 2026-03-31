from django.contrib import admin
from .models import CivilRightsPage, PageSection


class PageSectionInline(admin.StackedInline):
    model = PageSection
    extra = 0
    fields = (
        'section_type', 'order', 'is_visible', 'title', 'subtitle',
        'content', 'content_secondary', 'data', 'background', 'css_class',
        'cta_text', 'cta_url', 'cta_icon', 'cta_secondary_text', 'cta_secondary_url',
        'quote_source', 'alert_type',
    )


@admin.register(CivilRightsPage)
class CivilRightsPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'category', 'is_published', 'order')
    list_filter = ('is_published', 'category', 'show_in_nav')
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published', 'order')
    inlines = [PageSectionInline]
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'icon', 'order')}),
        ('Hero', {'fields': ('hero_title', 'hero_subtitle')}),
        ('SEO', {'fields': ('meta_description', 'meta_keywords')}),
        ('Publishing', {'fields': ('is_published', 'is_featured', 'show_in_nav', 'nav_title')}),
    )
