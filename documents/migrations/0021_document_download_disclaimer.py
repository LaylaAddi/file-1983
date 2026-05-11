from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0020_document_finalize_acknowledged_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='download_disclaimer_acknowledged_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text=(
                    'Audit stamp: when the user explicitly checked the AI / not-a-lawyer '
                    'disclaimer box on the finalize page. Mirrors the signup TOS checkbox '
                    'so we have a per-document agreement on file at the moment the clean '
                    'PDF is released.'
                ),
            ),
        ),
    ]
