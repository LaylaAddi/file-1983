from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0014_document_payment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='promocodeusage',
            name='amount_cents',
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    'Final price the buyer paid (in cents) — captured for '
                    'partner-cut accounting.'
                ),
            ),
        ),
    ]
