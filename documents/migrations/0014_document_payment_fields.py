from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0013_document_factual_allegations_drafted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='stripe_session_id',
            field=models.CharField(
                max_length=200, blank=True, default='', db_index=True,
                help_text=(
                    'Stripe Checkout Session ID — set when payment lands. '
                    'Used for webhook idempotency.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='paid_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text='When payment was confirmed by the Stripe webhook.',
            ),
        ),
    ]
