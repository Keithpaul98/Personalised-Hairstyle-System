from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Service Categories"
    
    def __str__(self):
        return self.name

class Service(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        ServiceCategory, 
        on_delete=models.CASCADE,
        related_name='services'
    )
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.IntegerField(
        help_text="Duration in minutes",
        default=60
    )
    image = models.ImageField(
        upload_to='service_images/', 
        blank=True, 
        null=True
    )
    perfect_corp_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ID of this service in the Perfect Corp API"
    )
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - MK{self.price}"

class Hairstyle(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('U', 'Unisex')
    ]

    name = models.CharField(max_length=200)
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.DurationField(default=timezone.timedelta(minutes=30))
    image = models.ImageField(upload_to='hairstyles/')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    perfect_corp_id = models.CharField(max_length=255, null=True, blank=True, 
                                   help_text="ID of this hairstyle in the Perfect Corp API")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_gender_display()})"

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    stock = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Store(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    services_offered = models.ManyToManyField(ServiceCategory)
    
    def __str__(self):
        return self.name