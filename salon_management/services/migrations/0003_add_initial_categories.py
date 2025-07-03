from django.db import migrations

def create_initial_categories(apps, schema_editor):
    ServiceCategory = apps.get_model('services', 'ServiceCategory')
    
    categories = [
        ('SALON', 'Salon Services'),
        ('BARBERSHOP', 'Barbershop Services'),
    ]
    
    for category_code, category_name in categories:
        ServiceCategory.objects.create(
            name=category_code,
            description=f'All {category_name}'
        )

class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_product_alter_servicecategory_options_and_more'),  # Update this to your last migration
    ]

    operations = [
        migrations.RunPython(create_initial_categories),
    ]
