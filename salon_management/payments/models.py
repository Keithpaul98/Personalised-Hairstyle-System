from django.db import models
from django.conf import settings
from Stock_Management.models import Product
from appointments.models import Appointment
from django.utils import timezone
import random
from User_Management.models import CustomUser

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('product', 'Product Purchase'),
        ('appointment', 'Appointment'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('card', 'Credit/Debit Card'),
        ('cash', 'Cash'),
    )
    
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='product')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='card')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_id = models.CharField(max_length=100)
    appointment = models.OneToOneField(
        Appointment, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='payment'
    )
    
class AppointmentReceipt(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    appointment = models.OneToOneField('appointments.Appointment', on_delete=models.CASCADE)
    receipt_number = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='Card')
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            date_str = timezone.now().strftime('%Y%m%d')
            random_digits = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            self.receipt_number = f'APT{date_str}{random_digits}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Receipt #{self.receipt_number} - {self.customer.username}"