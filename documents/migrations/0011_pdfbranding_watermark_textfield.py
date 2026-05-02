from django.db import migrations, models


def update_default_watermark(apps, schema_editor):
    """Replace the single-line default with a two-line version on existing rows
    that still hold the old value (so the previously-seeded 'default' row picks
    up the line-break-friendly text). Custom admin edits are preserved."""
    PdfBranding = apps.get_model('documents', 'PdfBranding')
    PdfBranding.objects.filter(watermark_text='DRAFT — NOT FOR FILING').update(
        watermark_text='DRAFT\nNOT FOR FILING'
    )


def revert_default_watermark(apps, schema_editor):
    PdfBranding = apps.get_model('documents', 'PdfBranding')
    PdfBranding.objects.filter(watermark_text='DRAFT\nNOT FOR FILING').update(
        watermark_text='DRAFT — NOT FOR FILING'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0010_pdfbranding'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pdfbranding',
            name='watermark_text',
            field=models.TextField(
                default='DRAFT\nNOT FOR FILING',
                help_text=(
                    'Diagonal watermark stamped across every page of unpaid PDFs. '
                    'Newlines render as line breaks so the text wraps cleanly.'
                ),
            ),
        ),
        migrations.RunPython(update_default_watermark, revert_default_watermark),
    ]
