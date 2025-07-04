# Generated by Django 5.1.3 on 2024-11-27 23:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('User_Management', '0007_rename_purchased_at_receipt_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='address',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='loyalty_points',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='customuser',
            name='phone_number',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
