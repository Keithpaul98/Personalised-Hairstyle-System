from django.db import models
from services.models import Service
from User_Management.models import CustomUser

# Create your models here.

class Stylist(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='stylist_profile')
    expertise = models.ManyToManyField(Service)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def save(self, *args, **kwargs):
        # Ensure the user is a staff member
        if not self.user.role == 'staff':
            raise ValueError("Stylist must be associated with a staff user")
        super().save(*args, **kwargs)

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )

    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='customer_appointments')
    stylist = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='staff_appointments')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == 'Completed':
            self.customer.loyalty_points += 20 if self.service.name == 'special' else 10
            self.customer.save()
            if self.customer.appointment_set.filter(status='completed').count() % 5 == 0:
                self.customer.loyalty_points += 100
            self.customer.save()

    def __str__(self):
        return f"{self.customer.username} - {self.service.name} on {self.date} at {self.time}"

class Rating(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='rating')
    customer = models.ForeignKey('User_Management.CustomUser', 
                               on_delete=models.CASCADE, 
                               related_name='ratings_given')
    stylist = models.ForeignKey('User_Management.CustomUser', 
                               on_delete=models.CASCADE, 
                               related_name='ratings_received')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update stylist's overall rating
        self.stylist.update_rating(self.rating)

    def __str__(self):
        return f"Rating for {self.stylist.get_full_name()} by {self.customer.get_full_name()}"


