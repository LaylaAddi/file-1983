from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CivilRightsPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('hero_title', models.CharField(blank=True, max_length=200)),
                ('hero_subtitle', models.TextField(blank=True)),
                ('meta_description', models.TextField(blank=True, max_length=160)),
                ('meta_keywords', models.CharField(blank=True, max_length=255)),
                ('is_published', models.BooleanField(default=False)),
                ('is_featured', models.BooleanField(default=False)),
                ('order', models.PositiveIntegerField(default=0)),
                ('show_in_nav', models.BooleanField(default=True)),
                ('nav_title', models.CharField(blank=True, max_length=50)),
                ('category', models.CharField(choices=[('rights', 'Know Your Rights'), ('legal', 'Legal Information'), ('action', 'Take Action'), ('resources', 'Resources'), ('auditors', 'First Amendment Auditors')], default='rights', max_length=20)),
                ('icon', models.CharField(default='bi-file-text', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Civil Rights Page', 'verbose_name_plural': 'Civil Rights Pages', 'ordering': ['order', 'title']},
        ),
        migrations.CreateModel(
            name='PageSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section_type', models.CharField(choices=[('hero', 'Hero Section'), ('content', 'Rich Text Content'), ('cards', 'Card Grid'), ('rights_cards', 'Rights Cards (with amendment badge)'), ('article_cards', 'Article Cards (with category badge)'), ('quote', 'Quote/Blockquote'), ('cta', 'Call to Action'), ('resources', 'Resource Links'), ('stats', 'Statistics Row'), ('two_column', 'Two Column Layout'), ('checklist', "Checklist (Do/Don't)"), ('alert', 'Alert/Notice Box'), ('accordion', 'Accordion/FAQ')], max_length=20)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('subtitle', models.TextField(blank=True)),
                ('content', models.TextField(blank=True)),
                ('content_secondary', models.TextField(blank=True)),
                ('data', models.JSONField(blank=True, null=True)),
                ('background', models.CharField(choices=[('light', 'White'), ('cream', 'Cream/Off-white'), ('blue', 'Light Blue'), ('dark', 'Dark (for CTAs)')], default='light', max_length=10)),
                ('css_class', models.CharField(blank=True, max_length=100)),
                ('cta_text', models.CharField(blank=True, max_length=100)),
                ('cta_url', models.CharField(blank=True, max_length=200)),
                ('cta_icon', models.CharField(blank=True, default='bi-shield-check', max_length=50)),
                ('cta_secondary_text', models.CharField(blank=True, max_length=100)),
                ('cta_secondary_url', models.CharField(blank=True, max_length=200)),
                ('quote_source', models.CharField(blank=True, max_length=200)),
                ('alert_type', models.CharField(choices=[('info', 'Info (Blue)'), ('warning', 'Warning (Yellow)'), ('danger', 'Danger (Red)'), ('success', 'Success (Green)')], default='info', max_length=10)),
                ('is_visible', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='public_pages.civilrightspage')),
            ],
            options={'verbose_name': 'Page Section', 'verbose_name_plural': 'Page Sections', 'ordering': ['order']},
        ),
    ]
