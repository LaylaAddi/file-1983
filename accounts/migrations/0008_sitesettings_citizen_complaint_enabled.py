"""
Adds the Citizen Complaint Assistant on/off switch to SiteSettings.

The field defaults to True (a working feature's normal state, and what a
fresh install or the test suite gets), but the data migration below turns
it OFF for this existing deployment on the way in — the feature is being
parked while its YouTube Data API quota problem is sorted out. Flip the
checkbox back on in admin (Site Settings) to restore it; nothing is
deleted either way.
"""
from django.db import migrations, models


def disable_for_existing_install(apps, schema_editor):
    SiteSettings = apps.get_model('accounts', 'SiteSettings')
    # update_or_create so this also covers a deployment whose singleton row
    # was never saved through admin — on create, every other field takes its
    # normal model default.
    SiteSettings.objects.update_or_create(
        pk=1, defaults={'citizen_complaint_enabled': False},
    )


def noop_reverse(apps, schema_editor):
    """Reversing just drops the column (handled by the AddField below);
    there's no previous value to restore."""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_user_email_verified_user_email_verified_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="citizen_complaint_enabled",
            field=models.BooleanField(
                default=True,
                help_text="Uncheck to hide the Citizen Complaint Assistant from users: its nav "
                          "links disappear and every /citizen-complaint/ URL returns 404. Nothing "
                          "is deleted — existing incidents, drafts and sent complaints stay in the "
                          "database untouched, and re-checking this restores the feature exactly "
                          "as it was. Staff accounts can still reach the feature while it is off, "
                          "so you can test before re-enabling it for everyone.",
                verbose_name="Citizen Complaint Assistant enabled",
            ),
        ),
        migrations.RunPython(disable_for_existing_install, noop_reverse),
    ]
