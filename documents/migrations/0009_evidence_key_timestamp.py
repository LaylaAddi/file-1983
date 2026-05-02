from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0008_document_factual_allegations_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='evidence',
            name='key_timestamp',
            field=models.CharField(
                blank=True,
                help_text=(
                    'HH:MM:SS timestamp into the recording where the key moment '
                    'happens — so the judge knows when to start watching.'
                ),
                max_length=20,
            ),
        ),
    ]
