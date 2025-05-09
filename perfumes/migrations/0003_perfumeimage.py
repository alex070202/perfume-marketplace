# Generated by Django 5.2 on 2025-04-28 17:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perfumes', '0002_perfume_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='PerfumeImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='perfume_images/')),
                ('perfume', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='perfumes.perfume')),
            ],
        ),
    ]
