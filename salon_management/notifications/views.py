from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Notification, NotificationPreference

@login_required
def notification_list(request):
    """View to display all notifications for the current user"""
    notifications = Notification.objects.filter(recipient=request.user)
    unread_count = notifications.filter(is_read=False).count()
    
    # Pagination
    paginator = Paginator(notifications, 10)  # Show 10 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'notifications/notification_list.html', {
        'notifications': page_obj,
        'unread_count': unread_count
    })

@login_required
def notification_detail(request, pk):
    """View to display a single notification and mark it as read"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    
    # Mark as read if it's not already
    if not notification.is_read:
        notification.mark_as_read()
    
    # Determine where to redirect based on notification type and related object
    redirect_url = None
    if notification.related_object_type and notification.related_object_id:
        if notification.related_object_type == 'Appointment':
            redirect_url = f'/appointments/details/{notification.related_object_id}/'
        elif notification.related_object_type == 'Product':
            redirect_url = f'/stock/product/{notification.related_object_id}/'
        elif notification.related_object_type == 'Payment':
            redirect_url = f'/payments/details/{notification.related_object_id}/'
    
    context = {
        'notification': notification,
        'redirect_url': redirect_url
    }
    
    return render(request, 'notifications/notification_detail.html', context)

@login_required
def mark_notification_read(request, pk):
    """API view to mark a notification as read"""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@login_required
def mark_all_notifications_read(request):
    """View to mark all notifications as read"""
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:notification_list')

@login_required
def notification_preferences(request):
    """View to manage notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        preferences.appointment_notifications = 'appointment_notifications' in request.POST
        preferences.stock_notifications = 'stock_notifications' in request.POST
        preferences.payment_notifications = 'payment_notifications' in request.POST
        preferences.system_notifications = 'system_notifications' in request.POST
        preferences.delivery_method = request.POST.get('delivery_method', 'in_app')
        preferences.save()
        
        messages.success(request, 'Notification preferences updated successfully.')
        return redirect('notifications:notification_preferences')
    
    return render(request, 'notifications/notification_preferences.html', {
        'preferences': preferences
    })

@login_required
def create_test_notification(request):
    """View to create a test notification for debugging purposes"""
    if request.method == 'POST':
        # Create a test notification
        notification = Notification.objects.create(
            recipient=request.user,
            notification_type='system',
            title='Test Notification',
            message='This is a test notification to verify the notification system is working properly.',
            is_read=False
        )
        
        messages.success(request, 'Test notification created successfully.')
        return redirect('notifications:notification_list')
    
    return render(request, 'notifications/create_test.html')