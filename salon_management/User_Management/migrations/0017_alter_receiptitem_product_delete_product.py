# Generated by Django 5.1.3 on 2025-04-14 22:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Stock_Management', '0001_initial'),
        ('User_Management', '0016_alter_purchase_product'),
    ]

    operations = [
        migrations.AlterField(
            model_name='receiptitem',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Stock_Management.product'),
        ),
        migrations.DeleteModel(
            name='Product',
        ),
    ]
