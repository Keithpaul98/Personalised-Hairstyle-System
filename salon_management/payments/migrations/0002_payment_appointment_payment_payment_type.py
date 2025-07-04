# Generated by Django 5.1.3 on 2024-12-01 23:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0006_alter_appointment_customer_alter_appointment_status_and_more'),
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='appointment',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment', to='appointments.appointment'),
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_type',
            field=models.CharField(choices=[('product', 'Product Purchase'), ('appointment', 'Appointment')], default='product', max_length=20),
        ),
    ]
