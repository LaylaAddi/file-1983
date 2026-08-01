from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("citizen_complaint", "0002_complaint_moderation_categories_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="targetagency",
            name="contact_name",
            field=models.CharField(
                blank=True,
                help_text='Named official this row targets (e.g. "Joseph A. Farrow"), when the '
                          'video description named a specific person rather than a general '
                          'agency line.',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="targetagency",
            name="contact_title",
            field=models.CharField(
                blank=True,
                help_text='Title of contact_name (e.g. "Chief of Police"), as written in the '
                          'source.',
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="targetagency",
            name="source",
            field=models.CharField(
                choices=[
                    ("detected", "Detected from video"),
                    ("db_match", "Matched curated Agency DB"),
                    ("description", "Found in video description"),
                    ("ai_lookup", "AI-assisted web lookup"),
                    ("manual", "Manually added by user"),
                ],
                default="manual",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="incident",
            name="extracted_data",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='AI-extracted structured data. Shape: {"agencies": [str], '
                          '"location": str, "incident_date": str, "contacts": [str], '
                          '"summary": str, "agency_contacts": {agency_name: [{"name", '
                          '"title", "email"}, ...]}, "regex": {...}}. agency_contacts is '
                          'only populated for named officials whose email was '
                          'regex-verified against the raw description/transcript text.',
            ),
        ),
    ]
