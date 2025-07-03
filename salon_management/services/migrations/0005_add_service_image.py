from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('services', '0004_fix_service_duration'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='service_images/'
            ),
        ),
    ]