from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0016_document_ai_quota_lock'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='previous_factual_allegations_json',
            field=models.JSONField(
                default=dict, blank=True,
                help_text=(
                    'Snapshot of factual_allegations_json captured immediately '
                    'before the most recent regenerate, so users can undo. '
                    'Empty dict means no undo available.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='previous_factual_allegations_drafted_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text='When the snapshot in previous_factual_allegations_json was originally drafted.',
            ),
        ),
    ]
