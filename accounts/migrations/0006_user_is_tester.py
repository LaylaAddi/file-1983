from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_sitesettings_contact'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_tester',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Grants test-mode features (example-stories autofill, '
                    '"Test mode" navbar badge). Lower-privilege than is_staff '
                    '— safe to grant to recruited testers.'
                ),
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='tester_granted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
