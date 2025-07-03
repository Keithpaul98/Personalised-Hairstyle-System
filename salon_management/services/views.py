from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template import TemplateDoesNotExist
from .models import Service, ServiceCategory, Hairstyle

def service_list(request):
    """Display all service categories and their services"""
    try:
        # Get all categories with their services
        categories = ServiceCategory.objects.all().prefetch_related('services')
        
        # Get all active services
        services = Service.objects.filter(is_active=True)
        
        # Get all active hairstyles from the Hairstyle model
        hairstyles = Hairstyle.objects.filter(is_active=True)
        
        context = {
            'categories': categories,
            'services': services,
            'hairstyles': hairstyles,
            'page_title': 'Our Services'
        }
        
        # Use the hairstyles template since it's already set up to display both services and hairstyles
        return render(request, 'services/hairstyles.html', context)
    except Exception as e:
        messages.error(request, f"Error loading services: {str(e)}")
        return redirect('User_Management:home')

@login_required
def service_detail(request, service_id):
    """Display details of a specific service"""
    try:
        service = get_object_or_404(Service, id=service_id)
        context = {
            'service': service,
            'page_title': service.name
        }
        # Use hairstyle_details.html template directly since it's already set up for displaying service details
        return render(request, 'services/hairstyle_details.html', context)
    except Service.DoesNotExist:
        messages.error(request, "Service not found")
        return redirect('services:service_list')

@login_required
def list_hairstyles(request):
    """Display all hairstyles"""
    try:
        # Get all categories
        categories = ServiceCategory.objects.all().prefetch_related('services')
        
        # Get all active services
        services = Service.objects.filter(is_active=True)
        
        # Get all active hairstyles
        hairstyles = Hairstyle.objects.filter(is_active=True)
        
        context = {
            'categories': categories,
            'services': services,
            'hairstyles': hairstyles,
            'page_title': 'Hairstyles'
        }
        
        return render(request, 'services/hairstyles.html', context)
    except Exception as e:
        messages.error(request, f"Error loading hairstyles: {str(e)}")
        return redirect('User_Management:home')

@login_required
def select_hairstyle(request, hairstyle_id):
    """Handle selection of a specific hairstyle"""
    try:
        # Try to get the hairstyle from Service model first
        try:
            hairstyle = Service.objects.get(id=hairstyle_id)
            # For Service model, use duration_minutes
            duration = hairstyle.duration_minutes
        except Service.DoesNotExist:
            # If not found in Service, try Hairstyle model
            hairstyle = Hairstyle.objects.get(id=hairstyle_id)
            # For Hairstyle model, use duration directly
            duration = hairstyle.duration
        
        # Store the selected hairstyle in session
        request.session['selected_hairstyle'] = {
            'id': hairstyle_id,
            'name': hairstyle.name,
            'price': str(hairstyle.price),
            'duration': str(duration)
        }
        
        messages.success(request, f"Selected {hairstyle.name} for your appointment")
        return redirect('appointments:book_appointment')
        
    except (Service.DoesNotExist, Hairstyle.DoesNotExist):
        messages.error(request, "Hairstyle not found")
        return redirect('services:list_hairstyles')
    except Exception as e:
        messages.error(request, f"Error selecting hairstyle: {str(e)}")
        return redirect('services:list_hairstyles')