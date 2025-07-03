from django.utils import timezone
from datetime import timedelta, datetime
from appointments.models import Appointment
from User_Management.models import CustomUser
from .utils import create_notification
import logging
from django.db.models import F

logger = logging.getLogger(__name__)

def send_appointment_reminders():
    """
    Send reminder notifications for appointments scheduled for tomorrow.
    This function should be run once daily via a scheduled task.
    """
    # Get tomorrow's date
    tomorrow = timezone.now().date() + timedelta(days=1)
    
    # Find all appointments scheduled for tomorrow
    tomorrow_appointments = Appointment.objects.filter(
        date=tomorrow,
        status__in=['Pending', 'Confirmed']  # Only remind for pending or confirmed appointments
    )
    
    reminder_count = 0
    for appointment in tomorrow_appointments:
        # Notify the customer
        customer_notification = create_notification(
            recipient=appointment.customer,
            notification_type='appointment',
            title='Appointment Reminder',
            message=f'You have an appointment for {appointment.service.name} with {appointment.stylist.get_full_name()} '
                    f'tomorrow at {appointment.time.strftime("%I:%M %p")}.',
            related_object_id=appointment.id,
            related_object_type='Appointment'
        )
        
        # Notify the stylist
        stylist_notification = create_notification(
            recipient=appointment.stylist,
            notification_type='appointment',
            title='Appointment Reminder',
            message=f'You have an appointment with {appointment.customer.get_full_name()} '
                    f'for {appointment.service.name} tomorrow at {appointment.time.strftime("%I:%M %p")}.',
            related_object_id=appointment.id,
            related_object_type='Appointment'
        )
        
        if customer_notification or stylist_notification:
            reminder_count += 1
    
    logger.info(f"Sent {reminder_count} appointment reminders for {tomorrow}")
    return reminder_count

def send_loyalty_points_expiration_reminders():
    """
    Send reminder notifications for loyalty points that will expire soon.
    This function should be run once daily via a scheduled task.
    """
    # Get date 7 days from now
    expiry_threshold = timezone.now().date() + timedelta(days=7)
    
    # Find all customers with loyalty points expiring within 7 days
    customers_with_expiring_points = CustomUser.objects.filter(
        role='customer',
        discount_expiry__lte=expiry_threshold,
        discount_expiry__gte=timezone.now().date(),  # Only future expirations
        loyalty_points__gt=0  # Only if they have points
    )
    
    reminder_count = 0
    for customer in customers_with_expiring_points:
        days_remaining = (customer.discount_expiry - timezone.now().date()).days
        
        notification = create_notification(
            recipient=customer,
            notification_type='system',
            title='Loyalty Points Expiring Soon',
            message=f'Your {customer.loyalty_points} loyalty points will expire in {days_remaining} days. '
                    f'Book an appointment or make a purchase to use them before they expire!',
            related_object_id=customer.id,
            related_object_type='Customer'
        )
        
        if notification:
            reminder_count += 1
    
    logger.info(f"Sent {reminder_count} loyalty points expiration reminders")
    return reminder_count

def send_new_product_notifications():
    """
    Send notifications about new products added in the last 24 hours.
    Only sends to customers who have purchased similar products before.
    """
    from Stock_Management.models import Product
    from django.db.models import Q
    
    # Get products added in the last 24 hours
    one_day_ago = timezone.now() - timedelta(days=1)
    new_products = Product.objects.filter(created_at__gte=one_day_ago)
    
    notification_count = 0
    for product in new_products:
        # Find customers who purchased similar products (same category)
        similar_product_customers = CustomUser.objects.filter(
            role='customer',
            purchase__product__category=product.category
        ).distinct()
        
        for customer in similar_product_customers:
            notification = create_notification(
                recipient=customer,
                notification_type='system',
                title='New Product Alert',
                message=f'New product alert! {product.name} is now available for ${product.price}. '
                        f'Based on your previous purchases, we thought you might be interested.',
                related_object_id=product.id,
                related_object_type='Product'
            )
            
            if notification:
                notification_count += 1
    
    logger.info(f"Sent {notification_count} new product notifications")
    return notification_count

def send_service_discount_notifications():
    """
    Send notifications about service discounts to relevant customers.
    This looks for services with prices that are lower than usual
    (based on a comparison with similar services).
    """
    try:
        from services.models import Service, ServiceCategory
        from django.db.models import Avg
        from decimal import Decimal
        
        notification_count = 0
        
        # Get all service categories
        categories = ServiceCategory.objects.all()
        
        for category in categories:
            # Calculate average price for this category
            avg_price = Service.objects.filter(
                category=category,
                is_active=True
            ).aggregate(avg_price=Avg('price'))['avg_price']
            
            if not avg_price:
                continue
            
            # Find services that are at least 15% cheaper than average for their category
            discount_threshold = avg_price * Decimal('0.85')  # 15% discount threshold
            discounted_services = Service.objects.filter(
                category=category,
                is_active=True,
                price__lt=discount_threshold
            )
            
            for service in discounted_services:
                # Calculate discount percentage
                discount_percentage = int(((avg_price - service.price) / avg_price) * 100)
                
                # Find customers who have used services in this category before
                previous_customers = CustomUser.objects.filter(
                    role='customer',
                    customer_appointments__service__category=category
                ).distinct()
                
                for customer in previous_customers:
                    notification = create_notification(
                        recipient=customer,
                        notification_type='system',
                        title='Service Discount Available',
                        message=f'Special offer! {service.name} is approximately {discount_percentage}% cheaper than similar services. '
                                f'Regular price for similar services: ${avg_price:.2f}, this service: ${service.price:.2f}. '
                                f'Book now to take advantage of this great value!',
                        related_object_id=service.id,
                        related_object_type='Service'
                    )
                    
                    if notification:
                        notification_count += 1
        
        logger.info(f"Sent {notification_count} service discount notifications")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_service_discount_notifications: {str(e)}")
        return 0

def send_birthday_special_notifications():
    """
    Send special offers to customers.
    Since there's no birth_date field, we send weekly specials instead.
    """
    try:
        # Get today's date
        today = timezone.now().date()
        
        # Since there's no birth_date field, we'll send to all customers
        # This is a fallback since we can't filter by birthday
        customers = CustomUser.objects.filter(
            role='customer',
            is_active=True
        )[:20]  # Limit to 20 customers to avoid sending too many notifications
        
        notification_count = 0
        for customer in customers:
            notification = create_notification(
                recipient=customer,
                notification_type='system',
                title='Special Offer This Week',
                message=f'Hello {customer.get_full_name()}! Enjoy a special 15% discount '
                        f'on any service booked this week. Valid for 7 days.',
                related_object_id=customer.id,
                related_object_type='Customer'
            )
            
            if notification:
                notification_count += 1
        
        logger.info(f"Sent {notification_count} special offer notifications")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_birthday_special_notifications: {str(e)}")
        return 0

def send_inactive_customer_notifications():
    """
    Send re-engagement notifications to customers who haven't visited in 3 months.
    """
    try:
        three_months_ago = timezone.now().date() - timedelta(days=90)
        
        # Find customers who haven't had an appointment in the last 3 months
        inactive_customers = CustomUser.objects.filter(
            role='customer',
            customer_appointments__date__lt=three_months_ago
        ).exclude(
            customer_appointments__date__gte=three_months_ago
        ).distinct()
        
        notification_count = 0
        for customer in inactive_customers:
            notification = create_notification(
                recipient=customer,
                notification_type='system',
                title='We Miss You!',
                message=f'Hi {customer.get_full_name()}, we miss you! It\'s been a while since your last visit. '
                        f'Book an appointment today and receive 100 bonus loyalty points!',
                related_object_id=customer.id,
                related_object_type='Customer'
            )
            
            if notification:
                notification_count += 1
        
        logger.info(f"Sent {notification_count} inactive customer notifications")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_inactive_customer_notifications: {str(e)}")
        return 0

def send_busy_day_notifications():
    """
    Send notifications to stylists about upcoming busy days.
    Alerts stylists when they have more than 5 appointments scheduled on a single day.
    """
    try:
        # Look ahead for the next 7 days
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=7)
        
        # Find all staff members (stylists)
        stylists = CustomUser.objects.filter(role='staff')
        
        notification_count = 0
        for stylist in stylists:
            # Check each day in the next week
            for day_offset in range(7):
                check_date = start_date + timedelta(days=day_offset)
                
                # Count appointments for this stylist on this day
                appointment_count = Appointment.objects.filter(
                    stylist=stylist,
                    date=check_date,
                    status__in=['Pending', 'Confirmed']
                ).count()
                
                # If it's a busy day (more than 5 appointments)
                if appointment_count > 5:
                    # Format the date
                    formatted_date = check_date.strftime("%A, %B %d")
                    
                    notification = create_notification(
                        recipient=stylist,
                        notification_type='appointment',
                        title='Busy Day Alert',
                        message=f'Heads up! You have {appointment_count} appointments scheduled for {formatted_date}. '
                                f'Make sure you\'re prepared for a busy day.',
                        related_object_id=stylist.id,
                        related_object_type='Stylist'
                    )
                    
                    if notification:
                        notification_count += 1
                    
                    # Only send one notification per stylist (for the first busy day found)
                    break
        
        logger.info(f"Sent {notification_count} busy day notifications to stylists")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_busy_day_notifications: {str(e)}")
        return 0

def send_schedule_gap_notifications():
    """
    Send notifications to stylists about large gaps in their schedule.
    Alerts stylists when they have gaps of 2+ hours between appointments.
    """
    try:
        # Look at today and tomorrow
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=1)
        
        # Find all staff members (stylists)
        stylists = CustomUser.objects.filter(role='staff')
        
        notification_count = 0
        for stylist in stylists:
            # Check each day
            for day_offset in range(2):
                check_date = start_date + timedelta(days=day_offset)
                
                # Get all appointments for this stylist on this day, ordered by time
                appointments = Appointment.objects.filter(
                    stylist=stylist,
                    date=check_date,
                    status__in=['Pending', 'Confirmed']
                ).order_by('time')
                
                # If there are at least 2 appointments, check for gaps
                if appointments.count() >= 2:
                    gaps_found = False
                    gap_start_time = None
                    gap_end_time = None
                    gap_hours = 0
                    
                    # Convert to list for easier processing
                    appt_list = list(appointments)
                    
                    # Check each pair of consecutive appointments
                    for i in range(len(appt_list) - 1):
                        current_appt = appt_list[i]
                        next_appt = appt_list[i + 1]
                        
                        # Calculate end time of current appointment (assuming service duration)
                        try:
                            current_end_time = (
                                datetime.combine(check_date, current_appt.time) + 
                                timedelta(minutes=current_appt.service.duration_minutes)
                            ).time()
                        except AttributeError:
                            # If service doesn't have duration_minutes, use a default of 60 minutes
                            current_end_time = (
                                datetime.combine(check_date, current_appt.time) + 
                                timedelta(minutes=60)
                            ).time()
                        
                        # Calculate gap duration in hours
                        gap_start = datetime.combine(check_date, current_end_time)
                        gap_end = datetime.combine(check_date, next_appt.time)
                        gap_hours = (gap_end - gap_start).total_seconds() / 3600
                        
                        # If gap is 2+ hours
                        if gap_hours >= 2:
                            gaps_found = True
                            gap_start_time = current_end_time.strftime("%I:%M %p")
                            gap_end_time = next_appt.time.strftime("%I:%M %p")
                            break
                    
                    if gaps_found:
                        # Format the date
                        formatted_date = check_date.strftime("%A, %B %d")
                        
                        notification = create_notification(
                            recipient=stylist,
                            notification_type='appointment',
                            title='Schedule Gap Alert',
                            message=f'You have a {int(gap_hours)}-hour gap in your schedule on {formatted_date} '
                                    f'between {gap_start_time} and {gap_end_time}. '
                                    f'This might be a good opportunity to schedule additional appointments.',
                            related_object_id=stylist.id,
                            related_object_type='Stylist'
                        )
                        
                        if notification:
                            notification_count += 1
        
        logger.info(f"Sent {notification_count} schedule gap notifications to stylists")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_schedule_gap_notifications: {str(e)}")
        return 0

def send_customer_anniversary_notifications():
    """
    Send notifications to stylists about customer service anniversaries.
    Alerts stylists when it's been exactly 1 year since a customer's first appointment.
    """
    try:
        # Today's date
        today = timezone.now().date()
        
        # Find all staff members (stylists)
        stylists = CustomUser.objects.filter(role='staff')
        
        notification_count = 0
        for stylist in stylists:
            # Find customers who had their first appointment with this stylist exactly 1 year ago
            one_year_ago = today - timedelta(days=365)
            
            # Get all customers who have had appointments with this stylist
            stylist_customers = CustomUser.objects.filter(
                role='customer',
                customer_appointments__stylist=stylist
            ).distinct()
            
            for customer in stylist_customers:
                # Get the date of the first appointment for this customer with this stylist
                first_appointment = Appointment.objects.filter(
                    customer=customer,
                    stylist=stylist
                ).order_by('date').first()
                
                # Check if the first appointment was exactly 1 year ago
                if first_appointment and first_appointment.date == one_year_ago:
                    notification = create_notification(
                        recipient=stylist,
                        notification_type='system',
                        title='Customer Anniversary',
                        message=f'Today marks 1 year since {customer.get_full_name()}\'s first appointment with you! '
                                f'Consider sending them a special offer or thank you message.',
                        related_object_id=customer.id,
                        related_object_type='Customer'
                    )
                    
                    if notification:
                        notification_count += 1
        
        logger.info(f"Sent {notification_count} customer anniversary notifications to stylists")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_customer_anniversary_notifications: {str(e)}")
        return 0

def send_product_restock_notifications():
    """
    Send notifications to admin users about products that need restocking.
    Alerts admins when products are at or below their minimum stock level.
    """
    try:
        # Try to import Product model
        try:
            from Stock_Management.models import Product
        except ImportError:
            logger.error("Could not import Product model, skipping product restock notifications")
            return 0
        
        # Find all admin users
        admin_users = CustomUser.objects.filter(role='admin')
        
        if not admin_users.exists():
            logger.warning("No admin users found to send product restock notifications")
            return 0
        
        # Find products that are low in stock
        try:
            # Find products where current_stock is less than or equal to minimum_stock
            low_stock_products = Product.objects.filter(
                current_stock__lte=F('minimum_stock'),
                is_active=True
            )
        except Exception as e:
            logger.error(f"Error querying low stock products: {str(e)}")
            # Fallback to a simpler query if the above fails
            try:
                low_stock_products = Product.objects.filter(
                    current_stock__lte=5,  # Default minimum threshold
                    is_active=True
                )
            except Exception as e:
                logger.error(f"Fallback query also failed: {str(e)}")
                return 0
        
        notification_count = 0
        
        # If we have low stock products, notify all admin users
        if low_stock_products:
            product_list = ", ".join([f"{p.name} ({p.current_stock} left)" for p in low_stock_products[:5]])
            
            # If there are more than 5 products, add a note
            if len(low_stock_products) > 5:
                product_list += f", and {len(low_stock_products) - 5} more"
            
            for admin in admin_users:
                notification = create_notification(
                    recipient=admin,
                    notification_type='stock',
                    title='Products Running Low',
                    message=f'The following products are running low on stock: {product_list}. '
                            f'Please consider restocking these items soon.',
                    related_object_id=None,
                    related_object_type='Product'
                )
                
                if notification:
                    notification_count += 1
        
        logger.info(f"Sent {notification_count} product restock notifications to admin users")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_product_restock_notifications: {str(e)}")
        return 0

def send_daily_revenue_notifications():
    """
    Send daily revenue summary notifications to admin users.
    Provides a summary of the previous day's revenue from appointments and product sales.
    """
    try:
        # Try to import necessary models
        try:
            from appointments.models import Appointment
            from Stock_Management.models import StockTransaction
        except ImportError as e:
            logger.error(f"Could not import required models for revenue notifications: {str(e)}")
            return 0
        
        # Find all admin users
        admin_users = CustomUser.objects.filter(role='admin')
        
        if not admin_users.exists():
            logger.warning("No admin users found to send revenue notifications")
            return 0
        
        # Get yesterday's date
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Calculate appointment revenue for yesterday
        try:
            # Get all completed appointments from yesterday
            completed_appointments = Appointment.objects.filter(
                date=yesterday,
                status='Completed'
            )
            
            # Calculate total appointment revenue
            appointment_revenue = sum(appointment.service.price for appointment in completed_appointments)
            appointment_count = completed_appointments.count()
            
            # Calculate product sales revenue (if StockTransaction model exists)
            try:
                product_sales = StockTransaction.objects.filter(
                    transaction_date__date=yesterday,
                    transaction_type='sale'
                )
                product_revenue = sum(sale.total_amount for sale in product_sales)
                product_count = product_sales.count()
            except Exception as e:
                logger.warning(f"Error calculating product revenue: {str(e)}")
                product_revenue = 0
                product_count = 0
                
            # Calculate total revenue
            total_revenue = appointment_revenue + product_revenue
            
            # Format the date
            formatted_date = yesterday.strftime("%A, %B %d, %Y")
            
            notification_count = 0
            for admin in admin_users:
                notification = create_notification(
                    recipient=admin,
                    notification_type='revenue',
                    title=f'Daily Revenue Summary for {formatted_date}',
                    message=f'Revenue summary for {formatted_date}:\n'
                            f'• Appointments: ${appointment_revenue:.2f} ({appointment_count} completed)\n'
                            f'• Product Sales: ${product_revenue:.2f} ({product_count} items sold)\n'
                            f'• Total Revenue: ${total_revenue:.2f}',
                    related_object_id=None,
                    related_object_type='Revenue'
                )
                
                if notification:
                    notification_count += 1
            
            logger.info(f"Sent {notification_count} daily revenue notifications to admin users")
            return notification_count
        except Exception as e:
            logger.error(f"Error calculating appointment revenue: {str(e)}")
            return 0
    except Exception as e:
        logger.error(f"Error in send_daily_revenue_notifications: {str(e)}")
        return 0

def send_staff_performance_notifications():
    """
    Send staff performance summary notifications to admin users.
    Provides a weekly summary of each stylist's performance metrics.
    """
    try:
        # Only send this notification on Mondays
        today = timezone.now().date()
        if today.weekday() != 0:  # 0 is Monday
            return 0
        
        # Try to import necessary models
        try:
            from appointments.models import Appointment
        except ImportError as e:
            logger.error(f"Could not import required models for staff performance notifications: {str(e)}")
            return 0
        
        # Find all admin users
        admin_users = CustomUser.objects.filter(role='admin')
        
        if not admin_users.exists():
            logger.warning("No admin users found to send staff performance notifications")
            return 0
        
        # Get date range for the previous week (Monday to Sunday)
        end_date = today - timedelta(days=1)  # Yesterday (Sunday)
        start_date = end_date - timedelta(days=6)  # Previous Monday
        
        # Find all staff members (stylists)
        stylists = CustomUser.objects.filter(role='staff')
        
        if not stylists.exists():
            logger.warning("No stylists found for performance metrics")
            return 0
        
        # Prepare performance summary for each stylist
        performance_summary = []
        
        for stylist in stylists:
            # Get all completed appointments for this stylist in the previous week
            completed_appointments = Appointment.objects.filter(
                stylist=stylist,
                date__range=[start_date, end_date],
                status='Completed'
            )
            
            # Calculate metrics
            appointment_count = completed_appointments.count()
            
            if appointment_count > 0:
                # Calculate total revenue
                total_revenue = sum(appointment.service.price for appointment in completed_appointments)
                
                # Calculate average revenue per appointment
                avg_revenue = total_revenue / appointment_count
                
                # Add to summary
                performance_summary.append({
                    'name': stylist.get_full_name(),
                    'appointments': appointment_count,
                    'revenue': total_revenue,
                    'avg_revenue': avg_revenue
                })
        
        # Sort by total revenue (highest first)
        performance_summary.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Format date range
        formatted_start = start_date.strftime("%b %d")
        formatted_end = end_date.strftime("%b %d, %Y")
        
        # Create message
        if performance_summary:
            message = f"Weekly staff performance summary ({formatted_start} - {formatted_end}):\n\n"
            
            for idx, perf in enumerate(performance_summary, 1):
                message += (f"{idx}. {perf['name']}\n"
                           f"   • Appointments: {perf['appointments']}\n"
                           f"   • Total Revenue: ${perf['revenue']:.2f}\n"
                           f"   • Avg Revenue/Appointment: ${perf['avg_revenue']:.2f}\n\n")
        else:
            message = f"No completed appointments for the week of {formatted_start} - {formatted_end}."
        
        # Send notification to all admin users
        notification_count = 0
        for admin in admin_users:
            notification = create_notification(
                recipient=admin,
                notification_type='performance',
                title=f'Weekly Staff Performance Summary ({formatted_start} - {formatted_end})',
                message=message,
                related_object_id=None,
                related_object_type='Performance'
            )
            
            if notification:
                notification_count += 1
        
        logger.info(f"Sent {notification_count} staff performance notifications to admin users")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_staff_performance_notifications: {str(e)}")
        return 0

def send_cancellation_trend_notifications():
    """
    Send notifications to admin users about appointment cancellation trends.
    Analyzes cancellation patterns and alerts admins if cancellation rates exceed thresholds.
    """
    try:
        # Only send this notification once a week (on Fridays)
        today = timezone.now().date()
        if today.weekday() != 4:  # 4 is Friday
            return 0
        
        # Try to import necessary models
        try:
            from appointments.models import Appointment
        except ImportError as e:
            logger.error(f"Could not import required models for cancellation trend notifications: {str(e)}")
            return 0
        
        # Find all admin users
        admin_users = CustomUser.objects.filter(role='admin')
        
        if not admin_users.exists():
            logger.warning("No admin users found to send cancellation trend notifications")
            return 0
        
        # Get date range for the past 30 days
        end_date = today
        start_date = end_date - timedelta(days=30)
        
        # Get all appointments in the date range
        all_appointments = Appointment.objects.filter(
            date__range=[start_date, end_date]
        )
        
        total_appointments = all_appointments.count()
        
        if total_appointments == 0:
            logger.info("No appointments found in the past 30 days for cancellation analysis")
            return 0
        
        # Get cancelled appointments
        cancelled_appointments = all_appointments.filter(status='Cancelled')
        cancellation_count = cancelled_appointments.count()
        
        # Calculate cancellation rate
        cancellation_rate = (cancellation_count / total_appointments) * 100
        
        # Analyze cancellations by stylist
        stylist_cancellations = {}
        stylists = CustomUser.objects.filter(role='staff')
        
        for stylist in stylists:
            stylist_appointments = all_appointments.filter(stylist=stylist)
            stylist_total = stylist_appointments.count()
            
            if stylist_total > 0:
                stylist_cancelled = stylist_appointments.filter(status='Cancelled').count()
                stylist_rate = (stylist_cancelled / stylist_total) * 100
                
                if stylist_rate > 10:  # Only include stylists with >10% cancellation rate
                    stylist_cancellations[stylist.get_full_name()] = {
                        'total': stylist_total,
                        'cancelled': stylist_cancelled,
                        'rate': stylist_rate
                    }
        
        # Sort stylists by cancellation rate (highest first)
        sorted_stylists = sorted(
            stylist_cancellations.items(),
            key=lambda x: x[1]['rate'],
            reverse=True
        )
        
        # Create notification message
        message = f"Appointment Cancellation Analysis (Past 30 Days):\n\n"
        message += f"• Overall cancellation rate: {cancellation_rate:.1f}% ({cancellation_count} of {total_appointments} appointments)\n"
        
        if cancellation_rate > 15:
            message += f"⚠️ WARNING: Overall cancellation rate exceeds 15% threshold\n"
        
        if sorted_stylists:
            message += "\nStylists with high cancellation rates:\n"
            
            for stylist_name, data in sorted_stylists:
                message += f"• {stylist_name}: {data['rate']:.1f}% ({data['cancelled']} of {data['total']} appointments)"
                
                if data['rate'] > 20:
                    message += " ⚠️"
                
                message += "\n"
        
        # Send notification to all admin users
        notification_count = 0
        for admin in admin_users:
            notification = create_notification(
                recipient=admin,
                notification_type='cancellation',
                title='Weekly Appointment Cancellation Analysis',
                message=message,
                related_object_id=None,
                related_object_type='CancellationAnalysis'
            )
            
            if notification:
                notification_count += 1
        
        logger.info(f"Sent {notification_count} cancellation trend notifications to admin users")
        return notification_count
    except Exception as e:
        logger.error(f"Error in send_cancellation_trend_notifications: {str(e)}")
        return 0

def run_all_scheduled_notifications():
    """
    Run all scheduled notification tasks.
    This function can be called from a management command or scheduled task.
    """
    # Customer notifications
    appointment_reminders = send_appointment_reminders()
    loyalty_reminders = send_loyalty_points_expiration_reminders()
    new_product_notifications = send_new_product_notifications()
    service_discount_notifications = send_service_discount_notifications()
    birthday_special_notifications = send_birthday_special_notifications()
    inactive_customer_notifications = send_inactive_customer_notifications()
    
    # Stylist notifications
    busy_day_notifications = send_busy_day_notifications()
    schedule_gap_notifications = send_schedule_gap_notifications()
    customer_anniversary_notifications = send_customer_anniversary_notifications()
    
    # Admin notifications
    product_restock_notifications = send_product_restock_notifications()
    daily_revenue_notifications = send_daily_revenue_notifications()
    staff_performance_notifications = send_staff_performance_notifications()
    cancellation_trend_notifications = send_cancellation_trend_notifications()
    
    return {
        # Customer notifications
        'appointment_reminders': appointment_reminders,
        'loyalty_reminders': loyalty_reminders,
        'new_product_notifications': new_product_notifications,
        'service_discount_notifications': service_discount_notifications,
        'birthday_special_notifications': birthday_special_notifications,
        'inactive_customer_notifications': inactive_customer_notifications,
        
        # Stylist notifications
        'busy_day_notifications': busy_day_notifications,
        'schedule_gap_notifications': schedule_gap_notifications,
        'customer_anniversary_notifications': customer_anniversary_notifications,
        
        # Admin notifications
        'product_restock_notifications': product_restock_notifications,
        'daily_revenue_notifications': daily_revenue_notifications,
        'staff_performance_notifications': staff_performance_notifications,
        'cancellation_trend_notifications': cancellation_trend_notifications,
    }