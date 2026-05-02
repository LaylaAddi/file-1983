from django.db import migrations, models


def create_default_branding(apps, schema_editor):
    PdfBranding = apps.get_model('documents', 'PdfBranding')
    PdfBranding.objects.get_or_create(
        name='default',
        defaults={
            'watermark_text': 'DRAFT — NOT FOR FILING',
            'footer_text': 'Draft preview — upgrade at www.file1983.com to download a clean copy.',
            'website_url': 'www.file1983.com',
            'is_active': True,
        },
    )


def remove_default_branding(apps, schema_editor):
    PdfBranding = apps.get_model('documents', 'PdfBranding')
    PdfBranding.objects.filter(name='default').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0009_evidence_key_timestamp'),
    ]

    operations = [
        migrations.CreateModel(
            name='PdfBranding',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                )),
                ('name', models.CharField(
                    default='default', max_length=50, unique=True,
                    help_text='Internal label so you can keep multiple drafts and toggle '
                              '`is_active` to swap between them.',
                )),
                ('watermark_text', models.CharField(
                    default='DRAFT — NOT FOR FILING', max_length=100,
                    help_text='Diagonal watermark stamped across every page of unpaid PDFs.',
                )),
                ('footer_text', models.CharField(
                    default='Draft preview — upgrade at www.file1983.com to download a clean copy.',
                    max_length=255,
                    help_text='Footer line shown at the bottom of every page of unpaid PDFs.',
                )),
                ('website_url', models.CharField(
                    default='www.file1983.com', max_length=255,
                    help_text='Site URL shown alongside the watermark/footer.',
                )),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'PDF Branding',
                'verbose_name_plural': 'PDF Branding',
            },
        ),
        migrations.RunPython(create_default_branding, remove_default_branding),
    ]
