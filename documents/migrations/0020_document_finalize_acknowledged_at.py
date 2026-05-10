from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0019_partner_adjustment_partnership_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='finalize_acknowledged_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text=(
                    'Audit stamp: when the user explicitly checked the '
                    '"complete + understand editing will lock" box on the '
                    'finalize confirmation page. Set together with locked_at.'
                ),
            ),
        ),
    ]
