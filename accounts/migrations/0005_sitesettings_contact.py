from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_rebrand_legal_copy'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='contact_email',
            field=models.EmailField(blank=True, default='rights@auditfile1983.com', max_length=254),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='contact_email_visible',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='contact_phone',
            field=models.CharField(blank=True, default='555-555-1212', max_length=40),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='contact_phone_visible',
            field=models.BooleanField(default=True),
        ),
    ]
