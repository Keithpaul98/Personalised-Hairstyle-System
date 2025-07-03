# appointments/context_processors.py
from django.utils import timezone
from .models import Appointment

def appointment_context(request):
    """
    Add appointment-related context variables to all templates.
    """
    context = {
        'today_date': timezone.now().date(),
        'today_appointments_count': 0,
    }
    
    # Only calculate appointment counts for authenticated staff users
    if request.user.is_authenticated and request.user.role == 'staff':
        today = timezone.now().date()
        context['today_appointments_count'] = Appointment.objects.filter(
            stylist=request.user,
            date=today
        ).count()
    
    return context