from django.db import models
from .models import Notification, NotificationPreference

def create_notification(recipient, notification_type, title, message, related_object_id=None, related_object_type=None):
    """
    Utility function to create a notification
    
    Args:
        recipient: User object who will receive the notification
        notification_type: Type of notification (appointment, stock, payment, system)
        title: Title of the notification
        message: Detailed message for the notification
        related_object_id: ID of the related object (optional)
        related_object_type: Type of the related object (optional)
    
    Returns:
        Notification object
    """
    # Check user preferences
    try:
        preferences = NotificationPreference.objects.get(user=recipient)
        
        # Check if this type of notification is enabled for the user
        if notification_type == 'appointment' and not preferences.appointment_notifications:
            return None
        elif notification_type == 'stock' and not preferences.stock_notifications:
            return None
        elif notification_type == 'payment' and not preferences.payment_notifications:
            return None
        elif notification_type == 'system' and not preferences.system_notifications:
            return None
    except NotificationPreference.DoesNotExist:
        # If preferences don't exist, create default ones
        preferences = NotificationPreference.objects.create(user=recipient)
    
    # Create the notification
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_object_id=related_object_id,
        related_object_type=related_object_type
    )
    
    # If email delivery is preferred, send an email
    if preferences.delivery_method == 'email':
        # This would be implemented with Django's email functionality
        pass
    
    # If SMS delivery is preferred, send an SMS
    if preferences.delivery_method == 'sms':
        # This would be implemented with a third-party SMS service
        pass
    
    return notification

def notify_appointment(appointment):
    """
    Create notifications for a new appointment
    
    Args:
        appointment: Appointment object
    """
    # Notify the stylist
    stylist_message = f"New appointment scheduled for {appointment.service.name} on {appointment.date} at {appointment.time} with {appointment.customer.get_full_name() or appointment.customer.username}."
    
    create_notification(
        recipient=appointment.stylist,
        notification_type='appointment',
        title=f"New Appointment: {appointment.service.name}",
        message=stylist_message,
        related_object_id=appointment.id,
        related_object_type='Appointment'
    )
    
    # Notify the customer
    customer_message = f"Your appointment for {appointment.service.name} on {appointment.date} at {appointment.time} has been confirmed with {appointment.stylist.get_full_name() or appointment.stylist.username}."
    
    create_notification(
        recipient=appointment.customer,
        notification_type='appointment',
        title="Appointment Confirmed",
        message=customer_message,
        related_object_id=appointment.id,
        related_object_type='Appointment'
    )

def notify_low_stock(product, admin_users):
    """
    Create notifications for low stock products
    
    Args:
        product: Product object
        admin_users: QuerySet of admin users to notify
    """
    message = f"The stock for {product.name} is running low. Current stock: {product.current_stock} units (Minimum: {product.minimum_stock})."
    
    for admin in admin_users:
        create_notification(
            recipient=admin,
            notification_type='stock',
            title=f"Low Stock Alert: {product.name}",
            message=message,
            related_object_id=product.id,
            related_object_type='Product'
        )

def notify_payment_confirmation(payment, user):
    """
    Create notification for payment confirmation
    
    Args:
        payment: Payment object
        user: User who made the payment
    """
    message = f"Your payment of ${payment.total} has been successfully processed. Thank you for your business!"
    
    create_notification(
        recipient=user,
        notification_type='payment',
        title="Payment Confirmation",
        message=message,
        related_object_id=payment.id,
        related_object_type='Payment'
    )

def notify_message(message, is_reply=False):
    """
    Create notifications for messages
    
    Args:
        message: CustomerMessage object
        is_reply: Boolean indicating if this is a reply notification
    """
    if is_reply:
        # Notify the customer about admin reply
        create_notification(
            recipient=message.customer,
            notification_type='system',
            title="Admin Reply to Your Message",
            message=f"Subject: {message.subject}\n\nAdmin has replied to your message.",
            related_object_id=message.id,
            related_object_type='CustomerMessage'
        )
    else:
        # Notify admins about new customer message
        from User_Management.models import CustomUser
        admin_users = CustomUser.objects.filter(role='admin')
        
        for admin in admin_users:
            create_notification(
                recipient=admin,
                notification_type='system',
                title=f"New Message from {message.customer.username}",
                message=f"Subject: {message.subject}\n\n{message.message[:100]}...",
                related_object_id=message.id,
                related_object_type='CustomerMessage'
            )