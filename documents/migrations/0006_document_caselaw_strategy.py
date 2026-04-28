from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_caselaw'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='caselaw_strategy',
            field=models.CharField(
                choices=[
                    ('none', 'No case law — pleads facts only'),
                    ('inline', 'Light inline citations within the complaint'),
                    ('memorandum', 'Separate memorandum of supporting authority'),
                    ('appendix', 'Appendix attached to the complaint'),
                ],
                default='none',
                help_text='How (if at all) supporting case law should appear in the final document',
                max_length=20,
            ),
        ),
    ]
