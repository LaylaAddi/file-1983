from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0011_pdfbranding_watermark_textfield'),
    ]

    operations = [
        migrations.AddField(
            model_name='wizardsession',
            name='story_addendums',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Per-category snippets the user dictated/typed after the initial analysis',
            ),
        ),
    ]
