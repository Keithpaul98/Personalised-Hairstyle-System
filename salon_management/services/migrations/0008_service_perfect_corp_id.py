# Generated by Django 5.1.3 on 2025-04-23 06:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0007_hairstyle_perfect_corp_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='perfect_corp_id',
            field=models.CharField(blank=True, help_text='ID of this service in the Perfect Corp API', max_length=255, null=True),
        ),
    ]
