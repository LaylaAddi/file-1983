from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_expand_location_type_choices'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseLaw',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(
                    max_length=40,
                    choices=[
                        ('1st_recording', 'First Amendment — Right to Record Police'),
                        ('1st_retaliation', 'First Amendment — Retaliation'),
                        ('1st_general', 'First Amendment — General'),
                        ('4th_excessive_force', 'Fourth Amendment — Excessive Force'),
                        ('4th_seizure', 'Fourth Amendment — Seizure / Arrest'),
                        ('4th_search', 'Fourth Amendment — Search'),
                        ('14th_due_process', 'Fourteenth Amendment — Due Process'),
                        ('14th_equal_protection', 'Fourteenth Amendment — Equal Protection'),
                        ('qualified_immunity', 'Qualified Immunity'),
                        ('monell', 'Monell / Municipal Liability'),
                        ('section_1983_general', 'Section 1983 — General Principles'),
                    ],
                )),
                ('case_name', models.CharField(max_length=255, help_text='e.g. "Glik v. Cunniffe"')),
                ('citation', models.CharField(max_length=255, help_text='e.g. "655 F.3d 78 (1st Cir. 2011)"')),
                ('court', models.CharField(blank=True, max_length=255, help_text='e.g. "U.S. Court of Appeals for the First Circuit"')),
                ('year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('holding_summary', models.TextField(help_text='Plain-English summary of what the case held')),
                ('why_it_matters', models.TextField(help_text='Why this matters for 1983 plaintiffs (especially auditors)')),
                ('key_quote', models.TextField(blank=True, help_text='Direct quote from the opinion (optional)')),
                ('jurisdiction_notes', models.TextField(blank=True, help_text='e.g. "Controlling in 1st Circuit; persuasive elsewhere"')),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Case Law',
                'verbose_name_plural': 'Case Law',
                'ordering': ['category', 'order', '-year'],
            },
        ),
    ]
