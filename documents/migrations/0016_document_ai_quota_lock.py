from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0015_promocodeusage_amount_cents'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='ai_calls_used',
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    'AI quota used on this document (story extraction + draft '
                    'regeneration + addendums). Resets to 0 on payment so paid '
                    'users get a fresh AI_QUOTA_PAID budget.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='locked_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text=(
                    'Set when the user clicks Finalize & Download. Locked '
                    'documents are read-only — no wizard edits, no AI calls. '
                    'Re-download is still allowed.'
                ),
            ),
        ),
    ]
