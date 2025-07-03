from django.shortcuts import render
from django.db import models

# Create your views here.
from appointments.models import Service
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Appointment, Stylist
from .forms import AppointmentForm
from services.models import Service, ServiceCategory
from django.utils.timezone import now, timedelta
from django.urls import reverse
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .models import Rating
from .forms import RatingForm
import datetime
from User_Management.models import CustomUser
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
import datetime
import logging
logger = logging.getLogger(__name__)

def get_appointment_context(form, user, selected_service=None, suggested_time=None):
    """
    Helper function to create context for rendering the appointment booking template.
    """
    return {
        'form': form,
        'service': selected_service,
        'service_categories': ServiceCategory.objects.all(),
        'services': Service.objects.filter(is_active=True),
        'today': now().date(),
        'appointments': get_customer_appointments(user),
        'selected_service': selected_service.id if selected_service else None,
        'suggested_time': suggested_time,
    }


BUFFER_TIME = timedelta(minutes=30)  # Adjust the buffer time as needed

APPOINTMENT_STATUS = {
    'PENDING': 'Pending',
    'CONFIRMED': 'Confirmed',
    'CANCELLED': 'Cancelled'
}

def get_customer_appointments(user):
    return Appointment.objects.filter(customer=user).exclude(status='Cancelled')
from django.http import JsonResponse
import datetime

@login_required
def list_appointments(request):
    """
    View for customers to see their upcoming appointments
    """
    # Get upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        customer=request.user,
        date__gte=now().date()
    ).order_by('date', 'time')
    
    # Get past appointments
    past_appointments = Appointment.objects.filter(
        customer=request.user,
        date__lt=now().date()
    ).order_by('-date', '-time')[:5]  # Limit to last 5 past appointments
    
    # Get all service categories with their services
    service_categories = ServiceCategory.objects.prefetch_related('services').all()
    today = now().date()
    
    context = {
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'service_categories': service_categories,
        'services': Service.objects.all(),
        'today': today,
        'now': now()
    }
    return render(request, 'appointments/my_appointments.html', context)

def get_available_stylists(service, date, time):
    """
    Find available stylists for a specific service, date and time.
    Only returns stylists who have the specific service in their expertise.
    """
    # Get all stylists who have this service in their expertise
    stylists = Stylist.objects.filter(
        available=True,
        user__role='staff',
        expertise__id=service.id  # Direct match with the service object
    ).exclude(
        # Exclude stylists with overlapping appointments
        user__staff_appointments__date=date,
        user__staff_appointments__time=time,
        user__staff_appointments__status__in=['Pending', 'Confirmed']
    ).distinct()
    
    return stylists

def get_preferred_stylist(customer, service, date, time):
    """
    Find the customer's preferred stylist who is available for the given service, date and time.
    If none are available, return None.
    """
    # Check if customer has rated stylists in the past
    top_rated_stylists = Rating.objects.filter(
        appointment__customer=customer,
        rating__gte=4  # Consider 4+ ratings as preferred
    ).values('appointment__stylist').annotate(
        avg_rating=models.Avg('rating')
    ).order_by('-avg_rating')
    
    # Get IDs of preferred stylists
    preferred_stylist_ids = [item['appointment__stylist'] for item in top_rated_stylists]
    
    if not preferred_stylist_ids:
        return None
    
    # Check if any preferred stylists are available for this appointment
    available_stylists = get_available_stylists(service, date, time)
    
    for stylist_id in preferred_stylist_ids:
        # Find the stylist object
        try:
            stylist = CustomUser.objects.get(id=stylist_id)
            # Check if this stylist is in the available list and has expertise for this service
            if stylist in [s.user for s in available_stylists]:
                # Find the corresponding Stylist object instead of returning the CustomUser
                stylist_obj = Stylist.objects.get(user=stylist)
                return stylist_obj
        except CustomUser.DoesNotExist:
            continue
    
    return None

def find_alternative_stylists(service, date, time, exclude_stylist=None):
    """
    Find alternative stylists with the same expertise if the preferred one is not available
    """
    stylists = get_available_stylists(service, date, time)
    
    if exclude_stylist:
        stylists = [s for s in stylists if s.user.id != exclude_stylist.id]
    
    return stylists

def find_next_available_slot(service, date, time, preferred_stylist=None):
    """
    Find the next available time slot if no stylists are available at the requested time
    Returns (date, time, available_stylists)
    """
    # Start with the requested time
    current_date = date
    current_time = time
    
    # Try up to 14 days in the future
    for _ in range(14):
        # Try each hour from the current time until closing time
        while current_time.hour < 18:  # Assuming salon closes at 6 PM
            # Advance time by 30 minutes
            current_time = (datetime.datetime.combine(current_date, current_time) + timedelta(minutes=30)).time()
            
            # Check if any stylists are available at this time
            available_stylists = get_available_stylists(service, current_date, current_time)
            
            # If we have a preferred stylist, check if they're available
            if preferred_stylist and any(s.user.id == preferred_stylist.id for s in available_stylists):
                return current_date, current_time, available_stylists
            
            # Otherwise, if any stylists are available, return this slot
            if available_stylists:
                return current_date, current_time, available_stylists
        
        # Move to the next day
        current_date = current_date + timedelta(days=1)
        current_time = datetime.datetime.strptime("09:00", "%H:%M").time()  # Reset to opening time
    
    # If no slots found in the next 14 days, return None
    return None, None, []

def assign_stylist(customer, service, date, time):
    """
    Intelligently assign a stylist based on expertise, availability and customer preference
    Returns (assigned_stylist, alternative_stylists, next_available_slot)
    """
    # First, get all available stylists with the required expertise
    available_stylists = get_available_stylists(service, date, time)
    
    if not available_stylists:
        # If no stylists with the required expertise are available at this time,
        # find the next available slot
        next_date, next_time, next_stylists = find_next_available_slot(service, date, time, None)
        
        if next_date and next_time:
            # Return the next available slot information
            return None, [], (next_date, next_time, next_stylists)
        
        # If no slots found in the near future
        return None, [], None
    
    # Try to get the customer's preferred stylist among the available ones
    preferred_stylist = get_preferred_stylist(customer, service, date, time)
    
    if preferred_stylist and preferred_stylist in available_stylists:
        # If the customer's preferred stylist is available, assign them
        return preferred_stylist, [s for s in available_stylists if s != preferred_stylist], None
    
    # Otherwise, sort available stylists by rating (highest first)
    sorted_stylists = sorted(available_stylists, key=lambda s: s.rating, reverse=True)
    
    # Assign the highest-rated stylist with the required expertise
    return sorted_stylists[0], sorted_stylists[1:], None

@login_required
def book_appointment(request, service_id=None):
    """
    View for booking an appointment
    """
    selected_service = None
    suggested_time = None
    
    if service_id:
        selected_service = get_object_or_404(Service, id=service_id)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            try:
                selected_service = form.cleaned_data['service']
                selected_date = form.cleaned_data['date']
                selected_time = form.cleaned_data['time']
                
                # Use the smart stylist assignment system
                assigned_stylist, alternative_stylists, next_available_slot = assign_stylist(
                    request.user, selected_service, selected_date, selected_time
                )
                
                if assigned_stylist:
                    # Verify that the assigned stylist has the required expertise
                    if isinstance(assigned_stylist, Stylist):
                        # If assign_stylist returned a Stylist object
                        if not assigned_stylist.expertise.filter(id=selected_service.id).exists():
                            messages.error(request, f"The assigned stylist does not have expertise in {selected_service.name}. Please try again.")
                            return render(request, 'appointments/appointments.html', 
                                        get_appointment_context(form, request.user, selected_service))
                        stylist_user = assigned_stylist.user
                    else:
                        # If assign_stylist returned a User object
                        try:
                            stylist = Stylist.objects.get(user=assigned_stylist)
                            if not stylist.expertise.filter(id=selected_service.id).exists():
                                messages.error(request, f"The assigned stylist does not have expertise in {selected_service.name}. Please try again.")
                                return render(request, 'appointments/appointments.html', 
                                            get_appointment_context(form, request.user, selected_service))
                            stylist_user = assigned_stylist
                        except Stylist.DoesNotExist:
                            messages.error(request, "The assigned stylist does not exist. Please try again.")
                            return render(request, 'appointments/appointments.html', 
                                        get_appointment_context(form, request.user, selected_service))
                    
                    # A stylist is available at the requested time
                    appointment = form.save(commit=False)
                    appointment.customer = request.user
                    appointment.stylist = stylist_user
                    appointment.status = 'Pending'
                    appointment.save()
                    
                    # If there are alternative stylists, pass them to the confirmation page
                    context = {
                        'appointment': appointment,
                        'alternative_stylists': alternative_stylists,
                        'service': selected_service,
                        'date': selected_date,
                        'time': selected_time,
                        'duration': selected_service.duration_minutes,
                        'price': selected_service.price,
                        'form_data': request.POST,
                    }
                    
                    # Notify the stylist
                    notify_stylist_of_appointment(appointment)
                    
                    return render(request, 'appointments/confirm_appointment.html', context)
                
                elif next_available_slot:
                    # No stylists available at requested time, but found alternative slot
                    next_date, next_time, next_stylists = next_available_slot
                    
                    # Save form data in session for later use
                    request.session['appointment_data'] = {
                        'service_id': selected_service.id,
                        'date': next_date.isoformat(),
                        'time': next_time.strftime('%H:%M'),
                    }
                    
                    # Suggest the alternative time slot
                    context = {
                        'form': form,
                        'service': selected_service,
                        'suggested_date': next_date,
                        'suggested_time': next_time,
                        'available_stylists': next_stylists,
                        'service_categories': ServiceCategory.objects.all(),
                        'services': Service.objects.filter(is_active=True),
                        'today': now().date(),
                    }
                    
                    return render(request, 'appointments/suggest_alternative.html', context)
                
                else:
                    # No available slots found
                    messages.error(request, "No available stylists or time slots found in the next 14 days. Please contact the salon directly.")
                    return render(request, 'appointments/appointments.html', 
                                get_appointment_context(form, request.user, selected_service))
                    
            except Exception as e:
                print(f"Booking error: {str(e)}")
                messages.error(request, f"An error occurred while booking your appointment: {str(e)}")
                return render(request, 'appointments/appointments.html', 
                            get_appointment_context(form, request.user, selected_service))
    else:
        initial_data = {'service': selected_service.id} if selected_service else {}
        form = AppointmentForm(initial=initial_data)

    return render(request, 'appointments/appointments.html', 
                 get_appointment_context(form, request.user, selected_service, suggested_time))

@login_required
def confirm_appointment(request):
    if request.method == 'POST':
        # Recreate the form from the confirmation page
        form = AppointmentForm(request.POST)
        if form.is_valid():
            service = form.cleaned_data['service']
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            stylist_id = request.POST.get('stylist_id')
            
            try:
                # Get the stylist user
                stylist_user = get_object_or_404(CustomUser, id=stylist_id)
                
                # Get the stylist profile associated with this user
                try:
                    stylist = Stylist.objects.get(user=stylist_user)
                    
                    # Verify that the stylist has the required expertise
                    if not stylist.expertise.filter(id=service.id).exists():
                        messages.error(request, f"The selected stylist does not have expertise in {service.name}. Please choose another stylist.")
                        return redirect('appointments:book_appointment')
                    
                    # Create the appointment
                    appointment = form.save(commit=False)
                    appointment.customer = request.user
                    appointment.status = 'Pending'
                    appointment.stylist = stylist_user
                    appointment.save()
                    
                    # Send notification to stylist
                    notify_stylist_of_appointment(appointment)
                    
                    # Redirect directly to payment checkout
                    return redirect('payments:appointment_checkout', appointment_id=appointment.id)
                
                except Stylist.DoesNotExist:
                    messages.error(request, "The selected stylist does not have a valid stylist profile. Please choose another stylist.")
                    return redirect('appointments:book_appointment')
                
            except Exception as e:
                print(f"Confirmation error: {str(e)}")
                messages.error(request, f"An error occurred while confirming your appointment: {str(e)}")
                return redirect('appointments:book_appointment')
    
    # If not POST or form invalid, redirect back to booking
    return redirect('appointments:book_appointment')

def notify_stylist_of_appointment(appointment):
    """
    Send notification to stylist about new appointment
    Creates in-app notifications for both the stylist and the customer
    """
    from notifications.utils import notify_appointment
    
    # Use the centralized notification system
    notify_appointment(appointment)
    
    print(f"Notifications created for appointment {appointment.id}")
    
    # In a production environment, you might also want to:
    # 1. Send email notifications
    # 2. Send SMS notifications
    # 3. Send push notifications to mobile devices

@login_required
def appointment_success(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, customer=request.user)
    
    # Debug prints
    print(f"Appointment ID: {appointment.id}")
    print(f"Stylist: {appointment.stylist}")
    print(f"Stylist username: {appointment.stylist.username}")
    print(f"Stylist first name: {appointment.stylist.first_name}")
    print(f"Stylist last name: {appointment.stylist.last_name}")
    
    return render(request, 'appointments/appointment_success.html', {
        'appointment': appointment,
    })

@login_required
def appointment_details(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check - ensure user can only view their own appointments
    if appointment.customer != request.user and appointment.stylist != request.user and not request.user.role == 'admin':
        messages.error(request, "You don't have permission to view this appointment.")
        return redirect('appointments:my_appointments')

    if request.method == 'POST':
        if 'update' in request.POST:
            form = AppointmentForm(request.POST, instance=appointment)
            if form.is_valid():
                appointment.date = form.cleaned_data['date']
                appointment.time = form.cleaned_data['time']
                appointment.save()
                messages.success(request, 'Appointment updated successfully!')
                return redirect('appointments:appointment_details', appointment_id=appointment.id)
        elif 'cancel' in request.POST:
            # Check if the appointment was previously confirmed or completed
            was_confirmed_or_completed = appointment.status in ['Confirmed', 'Completed']
            
            # Update status to cancelled
            appointment.status = 'Cancelled'
            appointment.save()
            
            # If the appointment was previously confirmed or completed, revoke loyalty points
            if was_confirmed_or_completed:
                # Standard points per appointment is 10
                points_to_revoke = 10
                customer = appointment.customer
                
                # Check if there's a receipt for this appointment to confirm points were awarded
                from payments.models import AppointmentReceipt
                receipt_exists = AppointmentReceipt.objects.filter(appointment=appointment).exists()
                
                if receipt_exists:
                    # Revoke the loyalty points
                    points_revoked = customer.revoke_loyalty_points(points_to_revoke)
                    
                    # Log the points revocation
                    logger.info(f"Revoked {points_revoked} loyalty points from {customer.username} for cancelled appointment {appointment.id}")
                    
                    # Add a message about the revoked points
                    if points_revoked > 0:
                        messages.info(request, f"{points_revoked} loyalty points have been revoked.")
            
            messages.info(request, 'Appointment cancelled successfully.')
            # Redirect based on user role
            if request.user.role == 'staff':
                return redirect('appointments:appointment_history')
            else:
                return redirect('appointments:my_appointments')
    else:
        form = AppointmentForm(instance=appointment)

    context = {
        'appointment': appointment,
        'form': form,
        'back_url': 'appointments:appointment_history' if request.user.role == 'staff' else 'appointments:my_appointments'
    }
    return render(request, 'appointments/appointment_details.html', context)

@login_required
def appointment_history(request):
    # Show different appointments based on user role
    if request.user.role == 'staff':
        # For staff (stylists), show appointments where they are the stylist
        appointments = Appointment.objects.filter(stylist=request.user).order_by('-date', '-time')
    else:
        # For customers, show appointments where they are the customer
        appointments = Appointment.objects.filter(customer=request.user).order_by('-date', '-time')
    
    # Filter to only show past appointments
    today = now().date()
    appointments = appointments.filter(date__lt=today)
    
    # Add debug prints
    for appointment in appointments:
        print(f"Appointment ID: {appointment.id}")
        print(f"Service: {appointment.service}")
        print(f"Stylist: {appointment.stylist}")
        print(f"Stylist username: {appointment.stylist.username if appointment.stylist else 'None'}")
        print("=" * 50)
    
    return render(request, 'appointments/appointment_history.html', {
        'appointments': appointments,
        'user_role': request.user.role
    })

def is_admin_or_staff(user):
    return user.is_authenticated and (user.role == 'admin' or user.role == 'staff')

@user_passes_test(is_admin_or_staff)
def admin_appointments(request):
    # For staff, only show their own appointments
    if request.user.role == 'staff':
        appointments = Appointment.objects.filter(stylist=request.user).order_by('-date', '-time')
    else:
        # For admins, show all appointments
        appointments = Appointment.objects.all().order_by('-date', '-time')
    
    # Get filter parameters
    status = request.GET.get('status')
    date = request.GET.get('date')
    
    # Apply filters
    if status:
        appointments = appointments.filter(status=status)
    if date:
        appointments = appointments.filter(date=date)
    
    return render(request, 'appointments/admin_appointments.html', {
        'appointments': appointments,
        'status_choices': Appointment.STATUS_CHOICES,
    })

@login_required
def rate_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security checks
    if appointment.customer != request.user:
        messages.error(request, "You can't rate this appointment.")
        return redirect('appointments:appointment_history')
        
    if appointment.status != 'Completed':
        messages.error(request, "You can only rate completed appointments.")
        return redirect('appointments:appointment_history')
        
    # Check if already rated
    if Rating.objects.filter(appointment=appointment).exists():
        messages.info(request, "You've already rated this appointment.")
        return redirect('appointments:appointment_history')
    
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.appointment = appointment
            rating.customer = request.user
            rating.stylist = appointment.stylist
            rating.save()
            
            messages.success(request, "Thank you for your rating!")
            return redirect('appointments:appointment_history')
    else:
        form = RatingForm()
    
    return render(request, 'appointments/rate_appointment.html', {
        'form': form,
        'appointment': appointment
    })

@login_required
def create_appointment(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.customer = request.user
            appointment.status = 'pending'  # Set initial status as pending
            appointment.save()
            
            # Redirect to payment checkout
            return redirect('appointment_checkout', appointment_id=appointment.id)
    else:
        form = AppointmentForm()
    
    return render(request, 'appointments/create_appointment.html', {
        'form': form
    })

def get_next_available_time(service, date, time):
    """
    Find the next available time slot for a given service
    """
    # Convert date and time to datetime object
    if isinstance(time, str):
        # Parse time string if needed
        time_obj = datetime.datetime.strptime(time, '%H:%M').time()
    else:
        time_obj = time
        
    # Create a datetime object by combining date and time
    current_time = datetime.datetime.combine(date, time_obj)
    
    # Define the end of the day (e.g., 6 PM)
    end_of_day = datetime.datetime.combine(date, datetime.time(18, 0))
    
    while current_time < end_of_day:
        current_time += datetime.timedelta(minutes=30)  # Check next 30-min slot
        
        # Get all stylists with the required expertise
        available_stylists = Stylist.objects.filter(
            available=True,
            user__role='staff',
            expertise__id=service.id
        ).exclude(
            # Exclude stylists with overlapping appointments
            user__staff_appointments__date=current_time.date(),
            user__staff_appointments__time=current_time.time(),
            user__staff_appointments__status__in=['Pending', 'Confirmed']
        ).distinct()
        
        if available_stylists.exists():
            return current_time.time()
    
    return None  # No available time found today

def check_and_fix_stylists():
    """
    Check if existing stylists have services assigned to their expertise
    If not, assign all services to their expertise
    Also ensure all staff users have is_staff=True and a stylist profile
    """
    try:
        # First, ensure all users with role='staff' have is_staff=True
        staff_users_fixed = 0
        for user in CustomUser.objects.filter(role='staff', is_staff=False):
            user.is_staff = True
            user.save()
            staff_users_fixed += 1
            print(f"Fixed user {user.username}: set is_staff=True")
        
        if staff_users_fixed > 0:
            print(f"Fixed {staff_users_fixed} staff users to have is_staff=True")
            
        # Get all stylists
        stylists = Stylist.objects.all()
        
        if not stylists.exists():
            print("No stylists found in the database")
        else:
            print(f"Found {stylists.count()} stylists in the database")
            
        # Check each stylist
        for stylist in stylists:
            # Check if the stylist has any expertise
            if stylist.expertise.count() == 0:
                print(f"Stylist {stylist.user.username} has no expertise, adding all services")
                
                # Add all services to the stylist's expertise
                for service in Service.objects.all():
                    stylist.expertise.add(service)
                
                print(f"Added {Service.objects.count()} services to stylist {stylist.user.username}")
            else:
                print(f"Stylist {stylist.user.username} already has {stylist.expertise.count()} services in expertise")
                
            # Ensure stylist is available
            if not stylist.available:
                stylist.available = True
                stylist.save()
                print(f"Updated stylist {stylist.user.username} to be available")
                
        # Also ensure all staff users have a stylist profile
        staff_users = CustomUser.objects.filter(role='staff', is_staff=True)
        print(f"Found {staff_users.count()} staff users with is_staff=True")
        
        stylists_created = 0
        for user in staff_users:
            # Check if user has a stylist profile
            try:
                Stylist.objects.get(user=user)
                # If we get here, the user already has a stylist profile
            except Stylist.DoesNotExist:
                print(f"Creating missing stylist profile for {user.username}")
                stylist = Stylist.objects.create(
                    user=user,
                    available=True,
                    rating=5.0
                )
                
                # Add all services to the stylist's expertise
                for service in Service.objects.all():
                    stylist.expertise.add(service)
                    
                print(f"Created stylist profile for {user.username} with {stylist.expertise.count()} services")
                stylists_created += 1
        
        if stylists_created > 0:
            print(f"Created {stylists_created} new stylist profiles")
                
    except Exception as e:
        print(f"Error checking stylists: {str(e)}")

def display_stylists_info():
    """
    Display information about all stylists in the database
    """
    stylists = Stylist.objects.all().prefetch_related('expertise')
    
    for stylist in stylists:
        print(f"Stylist: {stylist}")
        print(f"User: {stylist.user}")
        print(f"Expertise: {', '.join([service.name for service in stylist.expertise.all()])}")
        print(f"Rating: {stylist.rating}")
        print(f"Available: {stylist.available}")
        print("-------------------")

@login_required
@user_passes_test(is_admin_or_staff)
def edit_appointment(request, appointment_id):
    """
    View for admin to edit an appointment
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated successfully.')
            return redirect('appointments:admin_appointments')
    else:
        form = AppointmentForm(instance=appointment)
    
    # Get all service categories with their services
    service_categories = ServiceCategory.objects.prefetch_related('services').all()
    
    context = {
        'form': form,
        'appointment': appointment,
        'service_categories': service_categories,
        'services': Service.objects.filter(is_active=True),
        'today': now().date(),
        'staff_members': CustomUser.objects.filter(role='staff'),
        'status_choices': Appointment.STATUS_CHOICES,
    }
    
    return render(request, 'appointments/edit_appointment.html', context)

@login_required
def cancel_appointment(request, appointment_id):
    """
    View for cancelling an appointment (works for both admin/staff and customers)
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Security check: ensure customers can only cancel their own appointments
    if request.user.is_authenticated and request.user.role == 'customer':
        # Check if the appointment belongs to this customer
        if appointment.customer != request.user:
            messages.error(request, 'You can only cancel your own appointments.')
            return redirect('home')
    
    if request.method == 'POST':
        # Check if the appointment was previously confirmed or completed
        was_confirmed_or_completed = appointment.status in ['Confirmed', 'Completed']
        
        # Update status to cancelled
        appointment.status = 'Cancelled'
        appointment.save()
        
        # If the appointment was previously confirmed or completed, revoke loyalty points
        if was_confirmed_or_completed:
            # Standard points per appointment is 10
            points_to_revoke = 10
            customer = appointment.customer
            
            # Check if there's a receipt for this appointment to confirm points were awarded
            from payments.models import AppointmentReceipt
            receipt_exists = AppointmentReceipt.objects.filter(appointment=appointment).exists()
            
            if receipt_exists:
                # Revoke the loyalty points
                points_revoked = customer.revoke_loyalty_points(points_to_revoke)
                
                # Log the points revocation
                logger.info(f"Revoked {points_revoked} loyalty points from {customer.username} for cancelled appointment {appointment.id}")
                
                # Add a message about the revoked points
                if points_revoked > 0:
                    revoke_message = f" {points_revoked} loyalty points have been revoked."
                else:
                    revoke_message = ""
            else:
                revoke_message = ""
        
        # Send different messages based on user role
        if request.user.is_authenticated and request.user.role in ['admin', 'staff']:
            messages.success(request, f'Appointment has been cancelled.{revoke_message}')
            return redirect('appointments:admin_appointments')
        else:
            messages.success(request, f'Your appointment has been cancelled successfully.{revoke_message}')
            
            # Redirect based on user role
            if request.user.is_authenticated and request.user.role == 'customer':
                return redirect('appointments:my_appointments')
            else:
                return redirect('home')
    
    context = {
        'appointment': appointment,
    }
    
    # Use the appointment_details template with a cancel confirmation
    context['cancel_confirmation'] = True
    
    # Set the back_url based on user role
    if request.user.is_authenticated and request.user.role in ['admin', 'staff']:
        context['back_url'] = 'appointments:admin_appointments'
    else:
        context['back_url'] = 'appointments:my_appointments'
        
    return render(request, 'appointments/appointment_details.html', context)


@login_required
def customer_dashboard(request):
    """
    Customer dashboard showing upcoming and past appointments with management options
    """
    # Get upcoming appointments (not cancelled)
    upcoming_appointments = Appointment.objects.filter(
        customer=request.user,
        date__gte=now().date(),
        status__in=['Pending', 'Confirmed']
    ).order_by('date', 'time')
    
    # Get past appointments
    past_appointments = Appointment.objects.filter(
        customer=request.user,
        date__lt=now().date()
    ).order_by('-date', '-time')[:5]  # Show last 5 appointments
    
    # Get frequently booked services
    frequent_services = Service.objects.filter(
        appointment__customer=request.user,
        appointment__status='Completed'
    ).annotate(count=models.Count('id')).order_by('-count')[:3]
    
    context = {
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'frequent_services': frequent_services,
    }
    
    return render(request, 'appointments/customer_dashboard.html', context)


@login_required
def accept_alternative(request):
    """
    Handle acceptance of an alternative appointment time
    """
    if request.method == 'POST' and 'accept_alternative' in request.POST:
        # Get the saved appointment data from session
        appointment_data = request.session.get('appointment_data')
        
        if not appointment_data:
            messages.error(request, "Session expired. Please try booking again.")
            return redirect('appointments:book_appointment')
        
        try:
            # Create the appointment with the alternative time
            service = get_object_or_404(Service, id=appointment_data['service_id'])
            date = datetime.datetime.fromisoformat(appointment_data['date']).date()
            time = datetime.datetime.strptime(appointment_data['time'], '%H:%M').time()
            
            # Find an available stylist
            available_stylists = get_available_stylists(service, date, time)
            
            if not available_stylists:
                messages.error(request, "Sorry, this time slot is no longer available. Please try again.")
                return redirect('appointments:book_appointment')
            
            # Use the preferred stylist if available, otherwise use the first available one
            preferred_stylist = get_preferred_stylist(request.user, service, date, time)
            assigned_stylist = preferred_stylist.user if preferred_stylist else available_stylists[0].user
            
            # Create the appointment
            appointment = Appointment.objects.create(
                customer=request.user,
                stylist=assigned_stylist,
                service=service,
                date=date,
                time=time,
                status='Pending'
            )
            
            # Clear the session data
            if 'appointment_data' in request.session:
                del request.session['appointment_data']
            
            # Notify the stylist
            notify_stylist_of_appointment(appointment)
            
            messages.success(request, "Your appointment has been scheduled successfully!")
            return redirect('appointments:appointment_success', appointment_id=appointment.id)
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('appointments:book_appointment')
    
    return redirect('appointments:book_appointment')

# Function to automatically update appointment statuses
def update_appointment_statuses():
    """
    Automatically update appointment statuses based on time:
    - Pending appointments that have passed their date/time get cancelled
    - Confirmed appointments that occurred over 24 hours ago get marked as completed
    """
    today = now().date()
    current_time = now().time()
    yesterday = today - timedelta(days=1)
    
    # Cancel pending appointments that have passed
    pending_appointments = Appointment.objects.filter(
        status='Pending',
        date__lt=today  # Date is in the past
    )
    pending_appointments.update(status='Cancelled')
    
    # Also cancel pending appointments from today that have passed their time
    today_pending_appointments = Appointment.objects.filter(
        status='Pending',
        date=today,
        time__lt=current_time  # Time has passed
    )
    today_pending_appointments.update(status='Cancelled')
    
    # Complete confirmed appointments from yesterday or earlier
    confirmed_appointments = Appointment.objects.filter(
        status='Confirmed',
        date__lte=yesterday  # Date is yesterday or earlier
    )
    confirmed_appointments.update(status='Completed')
    
    return {
        'cancelled_pending': pending_appointments.count() + today_pending_appointments.count(),
        'completed_confirmed': confirmed_appointments.count()
    }

# Run the update when the module is loaded
update_results = update_appointment_statuses()
print(f"Auto-updated appointments: {update_results['cancelled_pending']} cancelled, {update_results['completed_confirmed']} completed")

# API endpoint for updating appointment status
@login_required
@user_passes_test(is_admin_or_staff)
def update_appointment_status(request, appointment_id):
    """
    AJAX endpoint for updating appointment status
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST requests allowed'})
    
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Check permissions - staff can only update their own appointments
        if request.user.role == 'staff' and appointment.stylist != request.user:
            return JsonResponse({'success': False, 'error': 'You can only update your own appointments'})
        
        new_status = request.POST.get('status')
        if new_status not in dict(Appointment.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'})
        
        # Allow updating to any status regardless of date
        appointment.status = new_status
        appointment.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Appointment status updated to {new_status}',
            'new_status': new_status
        })
    except Appointment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Appointment not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
