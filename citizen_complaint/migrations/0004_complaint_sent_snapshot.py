"""
Archives the message exactly as sent, so there is a true copy of what each
agency actually received.

`Complaint.body` and everything the headers derive from (agency name/email,
video title, privacy level, contact email, account email) all stay editable
after sending, so previously nothing recorded the sent message beyond the
recipient address. These fields are written once, at send, and never again.

Rows sent before this migration have empty snapshots — there is no way to
recover what went out for those; only `recipient_email_snapshot` and
`sent_at` are available.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("citizen_complaint", "0003_targetagency_contact_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaint",
            name="sent_subject_snapshot",
            field=models.TextField(
                blank=True,
                help_text="Subject line exactly as sent. Derived from agency name + video "
                          "title, both of which stay editable afterwards.",
            ),
        ),
        migrations.AddField(
            model_name="complaint",
            name="sent_body_snapshot",
            field=models.TextField(
                blank=True,
                help_text="The true copy: message body exactly as sent. `body` above remains "
                          "the working draft and can differ if it was edited later.",
            ),
        ),
        migrations.AddField(
            model_name="complaint",
            name="sent_from_snapshot",
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text="From header as sent, including the display name — which depends on "
                          "the privacy level chosen at the time, and can be changed afterwards.",
            ),
        ),
        migrations.AddField(
            model_name="complaint",
            name="sent_reply_to_snapshot",
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text="Reply-To as sent (blank when filed anonymously).",
            ),
        ),
        migrations.AddField(
            model_name="complaint",
            name="sent_bcc_snapshot",
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text="Bcc as sent — the sender's own account email at that time.",
            ),
        ),
        migrations.AddField(
            model_name="complaint",
            name="sent_body_sha256",
            field=models.CharField(
                blank=True,
                max_length=64,
                help_text="SHA-256 of the sent body, recorded at send time. Lets you show the "
                          "stored copy still matches what was hashed on the way out. Not "
                          "tamper-proof on its own (anyone who can rewrite the body row can "
                          "rewrite this too) — it catches accidental or application-level "
                          "modification, not a determined edit.",
            ),
        ),
    ]
