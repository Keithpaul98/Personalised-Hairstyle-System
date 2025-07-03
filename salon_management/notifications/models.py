from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.db import models  # This line was added

class Notification(models.Model):
    """
    Model for storing all types of notifications in the system
    """
    NOTIFICATION_TYPES = [
        ('appointment', 'Appointment'),
        ('stock', 'Stock Alert'),
        ('payment', 'Payment'),
        ('system', 'System Announcement'),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='notifications',
        on_delete=models.CASCADE
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object_type = models.CharField(max_length=100, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    def get_absolute_url(self):
        return reverse('notifications:notification_detail', kwargs={'pk': self.pk})


class NotificationPreference(models.Model):
    """
    Model for storing user notification preferences
    """
    DELIVERY_METHODS = [
        ('in_app', 'In-App Notifications'),
        ('email', 'Email Notifications'),
        ('sms', 'SMS Notifications'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='notification_preferences',
        on_delete=models.CASCADE
    )
    appointment_notifications = models.BooleanField(default=True)
    stock_notifications = models.BooleanField(default=True)
    payment_notifications = models.BooleanField(default=True)
    system_notifications = models.BooleanField(default=True)
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_METHODS, default='in_app')
    
    def __str__(self):
        return f"Notification preferences for {self.user.username}"