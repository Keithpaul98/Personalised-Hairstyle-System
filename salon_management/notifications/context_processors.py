from django.db import models
from .models import Notification

def notification_processor(request):
    """
    Context processor to add unread notification count to all templates
    """
    context = {
        'unread_notifications_count': 0
    }
    
    if request.user.is_authenticated:
        context['unread_notifications_count'] = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    
    return context