from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_revenue_partner',
            field=models.BooleanField(
                default=False,
                help_text='Grants access to the /partner/ dashboard to view sales and request payouts.',
            ),
        ),
    ]
