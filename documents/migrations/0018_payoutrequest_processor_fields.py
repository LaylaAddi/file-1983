from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0017_document_previous_draft'),
    ]

    operations = [
        migrations.AddField(
            model_name='payoutrequest',
            name='payment_processor',
            field=models.CharField(
                blank=True,
                choices=[
                    ('paypal', 'PayPal'),
                    ('venmo', 'Venmo'),
                    ('zelle', 'Zelle'),
                    ('check', 'Check'),
                    ('other', 'Other'),
                ],
                help_text='How the partner wants to be paid.',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='payoutrequest',
            name='payment_method_details',
            field=models.TextField(
                blank=True,
                help_text='Partner-supplied destination — PayPal email, Venmo handle, Zelle phone/email, mailing address for check, etc.',
            ),
        ),
        migrations.AddField(
            model_name='payoutrequest',
            name='payment_reference',
            field=models.CharField(
                blank=True,
                help_text='Admin-recorded transaction ID, check number, or confirmation reference once paid.',
                max_length=120,
            ),
        ),
        migrations.AddField(
            model_name='payoutrequest',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='payoutrequest',
            name='admin_notes',
            field=models.TextField(
                blank=True,
                help_text='Internal admin notes; not shown to the partner.',
            ),
        ),
        migrations.AlterField(
            model_name='payoutrequest',
            name='notes',
            field=models.TextField(
                blank=True,
                help_text='Partner-facing note left at request time.',
            ),
        ),
        migrations.AlterModelOptions(
            name='payoutrequest',
            options={'ordering': ['-requested_at']},
        ),
    ]
