from django.db import models
from django.conf import settings
from User_Management.models import Product
# Create your models here.

class Payment(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_id = models.CharField(max_length=100)
    