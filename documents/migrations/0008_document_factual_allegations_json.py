from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0007_document_caselaw_strategy'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='factual_allegations_json',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'AI-drafted (and user-edited) numbered factual allegations. '
                    'Shape: {"paragraphs": ["...", "..."]}.'
                ),
            ),
        ),
    ]
