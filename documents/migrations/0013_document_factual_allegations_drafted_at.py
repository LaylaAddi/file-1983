from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0012_wizardsession_story_addendums'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='factual_allegations_drafted_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text=(
                    'When the factual allegations were last (re)drafted or saved. '
                    'Compared against wizard_session.updated_at to detect stale drafts.'
                ),
            ),
        ),
    ]
