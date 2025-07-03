from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('services', '0005_add_service_image'),
    ]

    operations = [
        # Skip duration operations since we've already handled them
        # Only update the field definitions that need to change
        migrations.AlterField(
            model_name='service',
            name='category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='services',
                to='services.servicecategory'
            ),
        ),
        migrations.AlterField(
            model_name='service',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='servicecategory',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='servicecategory',
            name='name',
            field=models.CharField(max_length=100),
        ),
    ]