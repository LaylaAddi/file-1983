from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('public_pages', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=600, unique=True)),
                ('title', models.CharField(max_length=400)),
                ('source', models.CharField(max_length=100)),
                ('published_at', models.DateTimeField()),
                ('summary', models.TextField(blank=True)),
                ('is_visible', models.BooleanField(default=True)),
                ('fetched_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'News Item',
                'verbose_name_plural': 'News Items',
                'ordering': ['-published_at'],
            },
        ),
        migrations.AddIndex(
            model_name='newsitem',
            index=models.Index(fields=['-published_at', 'is_visible'], name='public_page_publish_2881fe_idx'),
        ),
    ]
