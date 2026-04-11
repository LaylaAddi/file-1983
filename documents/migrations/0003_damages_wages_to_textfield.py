from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_examplestory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='damages',
            name='lost_wages',
            field=models.TextField(
                blank=True,
                help_text='Description of lost wages or income, e.g. "Missed 2 work shifts, approx $300"'
            ),
        ),
        migrations.AlterField(
            model_name='damages',
            name='property_damage_amount',
            field=models.TextField(
                blank=True,
                help_text='Description of property damage, e.g. "Phone screen cracked, replacement ~$200"'
            ),
        ),
    ]
