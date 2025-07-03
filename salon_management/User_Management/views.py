from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerRegistrationForm, AdminRegistrationForm, CustomLoginForm, StaffForm, ProfileForm, ServiceForm
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Receipt, CartItem, ReceiptItem, Purchase
from appointments.models import Appointment, Stylist
from django.http import HttpResponse
import pdfkit
from django.template.loader import get_template
import logging
from django.core.mail import send_mail
from django.conf import settings
from services.models import Service, ServiceCategory
from django.utils import timezone
from django.db.models import Count, Sum, F, FloatField, ExpressionWrapper
from payments.models import Payment
from reporting.models import Report
from Stock_Management.models import Product, StockTransaction
from django.db import models
from appointments.models import Appointment, Rating
from datetime import datetime

# Create your views here

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def home(request):
    return render(request, 'home.html')


def customer_registration(request):
    form = CustomerRegistrationForm()
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('User_Management:custom_login')
    return render(request, 'user_management/customer_registration.html', {'form': form})

@login_required
def delete_service(request, service_id):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
    
    service = get_object_or_404(Service, id=service_id)
    service.delete()
    messages.success(request, 'Service deleted successfully!')
    return redirect('User_Management:admin_dashboard')

def custom_login(request):
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                # Redirect based on role
                if user.role == 'admin':
                    return redirect('User_Management:admin_dashboard')
                elif user.role == 'staff':
                    return redirect('User_Management:staff_dashboard')
                else:  # customer
                    return redirect('User_Management:home')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = CustomLoginForm()
    
    return render(request, 'User_Management/login.html', {'form': form})
    
         
def custom_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('User_Management:custom_login')

def admin_registration(request):
    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            admin = form.save(commit=False)
            admin.role = 'admin'
            admin.save()
            messages.success(request, 'Admin created successfully')
            return redirect('User_Management:custom_login')
    else:
        form = AdminRegistrationForm()
    return render(request, 'user_management/admin_registration.html', {'form': form})

def customer_products(request): 
    # Show only products that are available for retail sale (usage_type is 'retail' or 'both')
    # and are in stock
    products = Product.objects.filter(
        is_active=True,
        usage_type__in=['retail', 'both'],
        current_stock__gt=0  # Only show products that are in stock
    )
    return render(request, 'User_Management/customer_products.html', {'products': products})

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
        
    # Get counts
    total_appointments = Appointment.objects.count()
    total_services = Service.objects.count()
    total_products = Product.objects.count()
    total_reports = Report.objects.count()
    total_staff = CustomUser.objects.filter(role='staff').count()

    # Get recent items
    recent_appointments = Appointment.objects.all().order_by('-created_at')[:5]
    recent_reports = Report.objects.all().order_by('-date_generated')[:5]
    
    # Get low stock products
    low_stock_products = Product.objects.filter(
        current_stock__lte=F('minimum_stock'),
        is_active=True
    ).order_by('current_stock')[:10]
    
    # Get recent sales transactions
    recent_sales = StockTransaction.objects.filter(
        transaction_type='sale'
    ).order_by('-transaction_date')[:5]
    
    # Get staff members
    staff_members = CustomUser.objects.filter(role='staff')
    
    # Get services
    services = Service.objects.all()
    categories = ServiceCategory.objects.all()

    # Get revenue data
    total_revenue = Payment.objects.aggregate(Sum('total'))['total__sum'] or 0

    # Get today's data
    today = timezone.now().date()
    todays_appointments = Appointment.objects.filter(date=today).count()
    todays_revenue = Payment.objects.filter(paid_at__date=today).aggregate(Sum('total'))['total__sum'] or 0
    
    # Get today's sales
    todays_sales = StockTransaction.objects.filter(
        transaction_type='sale',
        transaction_date__date=today
    ).aggregate(
        total_items=Sum('quantity'),
        total_amount=Sum('total_amount')
    )
    todays_sales_count = todays_sales['total_items'] or 0
    todays_sales_amount = todays_sales['total_amount'] or 0

    # Get data for charts
    monthly_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_appointments = [Appointment.objects.filter(date__month=i, date__year=today.year).count() for i in range(1, 13)]
    
    # Fix monthly revenue calculation to include both product and appointment payments
    monthly_revenue = []
    for i in range(1, 13):
        # Get product payments for the month
        product_revenue = Payment.objects.filter(
            paid_at__month=i, 
            paid_at__year=today.year,
            payment_type='product'
        ).aggregate(Sum('total'))['total__sum'] or 0
        
        # Get appointment payments for the month
        appointment_revenue = Payment.objects.filter(
            paid_at__month=i, 
            paid_at__year=today.year,
            payment_type='appointment'
        ).aggregate(Sum('total'))['total__sum'] or 0
        
        # Total revenue for the month
        total_month_revenue = product_revenue + appointment_revenue
        monthly_revenue.append(total_month_revenue)
    
    # Add debug information to help troubleshoot
    context_debug = {
        'monthly_revenue_debug': monthly_revenue,
        'has_revenue_data': any(revenue > 0 for revenue in monthly_revenue)
    }

    # Get sales vs. salon usage data
    sales_vs_salon_data = {
        'retail_sales': StockTransaction.objects.filter(
            transaction_type='sale',
            product__usage_type__in=['retail', 'both']
        ).aggregate(
            total=Sum('total_amount', output_field=models.DecimalField(max_digits=10, decimal_places=2))
        )['total'] or 0,
        
        'salon_usage': StockTransaction.objects.filter(
            transaction_type='salon_usage',
            product__usage_type__in=['salon', 'both']
        ).aggregate(
            total=Sum('total_amount', output_field=models.DecimalField(max_digits=10, decimal_places=2))
        )['total'] or 0
    }

    # Calculate percentages for the pie chart
    total_usage = sales_vs_salon_data['retail_sales'] + sales_vs_salon_data['salon_usage']
    if total_usage > 0:
        retail_percentage = int((sales_vs_salon_data['retail_sales'] / total_usage) * 100)
        salon_percentage = 100 - retail_percentage
    else:
        retail_percentage = 50
        salon_percentage = 50

    # Get top retail products
    top_retail_products = Product.objects.filter(
        usage_type__in=['retail', 'both'],
        transactions__transaction_type='sale'
    ).annotate(
        total_sold=Sum('transactions__quantity', output_field=models.IntegerField())
    ).order_by('-total_sold')[:5]
    
    # Calculate percentages for progress bars
    if top_retail_products:
        max_retail_sold = top_retail_products[0].total_sold
        for product in top_retail_products:
            product.percentage = int((product.total_sold / max_retail_sold) * 100)
    
    # Get top salon usage products
    top_salon_products = Product.objects.filter(
        usage_type__in=['salon', 'both'],
        transactions__transaction_type='salon_usage'
    ).annotate(
        total_used=Sum('transactions__quantity', output_field=models.IntegerField()),
        frequency=Count('transactions')
    ).order_by('-total_used')[:5]
    
    # Calculate percentages for progress bars
    if top_salon_products:
        max_salon_used = top_salon_products[0].total_used
        for product in top_salon_products:
            product.percentage = int((product.total_used / max_salon_used) * 100)

    context = {
        'total_appointments': total_appointments,
        'total_services': total_services,
        'total_products': total_products,
        'total_reports': total_reports,
        'total_staff': total_staff,
        'recent_appointments': recent_appointments,
        'recent_reports': recent_reports,
        'low_stock_products': low_stock_products,
        'recent_sales': recent_sales,
        'staff_members': staff_members,
        'services': services,
        'categories': categories,
        'total_revenue': total_revenue,
        'todays_appointments': todays_appointments,
        'todays_revenue': todays_revenue,
        'todays_sales_count': todays_sales_count,
        'todays_sales_amount': todays_sales_amount,
        'monthly_labels': monthly_labels,
        'monthly_appointments': monthly_appointments,
        'monthly_revenue': monthly_revenue,
        'sales_vs_salon_data': sales_vs_salon_data,
        'retail_percentage': retail_percentage,
        'salon_percentage': salon_percentage,
        'top_retail_products': top_retail_products,
        'top_salon_products': top_salon_products,
        'low_stock_count': low_stock_products.count(),
        'active_customers': CustomUser.objects.filter(role='customer', is_active=True).count(),
        'active_tab': 'dashboard',
    }

    return render(request, 'User_Management/admin_dashboard.html', context)

@receiver(post_save, sender=Product)
def check_stock(sender, instance, **kwargs):
    threshold = instance.current_stock * 0.5
    if instance.current_stock <= threshold:
        # Send email to admin
        admin_users = CustomUser.objects.filter(role='admin')
        admin_emails = [user.email for user in admin_users]
        
        subject = f'Low Stock Alert: {instance.name}'
        message = f'''
        Low stock alert for {instance.name}:
        Current stock: {instance.current_stock}
        Threshold: {threshold}
        Please reorder soon.
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True
        )

@login_required
def add_to_cart(request, product_id):
    from Stock_Management.models import Product
    
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    # Check if there's enough stock
    if quantity > product.current_stock:
        quantity = product.current_stock
        messages.warning(request, f'Quantity adjusted to available stock ({product.current_stock}).')
    
    # Add to cart
    cart_item, created = CartItem.objects.get_or_create(customer=request.user, product=product)
    if not created:
        cart_item.quantity += quantity
        # Check again if the total quantity exceeds available stock
        if cart_item.quantity > product.current_stock:
            cart_item.quantity = product.current_stock
            messages.warning(request, f'Quantity adjusted to available stock ({product.current_stock}).')
    else:
        cart_item.quantity = quantity
    
    cart_item.save()
    
    messages.success(request, f'{product.name} added to cart.')
    return redirect('User_Management:customer_products')

@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(customer=request.user)
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'User_Management/cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, customer=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('User_Management:view_cart')

@login_required
def profile(request):
    if request.user.role == 'staff':
        # Redirect staff to their stylist profile
        return redirect('User_Management:stylist_profile', stylist_id=request.user.id)
        
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('User_Management:profile')
    else:
        form = ProfileForm(instance=request.user)
    
    # Check if discount has expired before displaying the profile
    request.user.check_discount_expiry()
    
    # Update total earned points for this user
    update_user_total_earned_points(request.user)
    
    # Get user's appointments
    appointments = Appointment.objects.filter(
        customer=request.user
    ).order_by('-date')[:5]  # Get last 5 appointments

    # Get user's receipts - Change date to created_at
    receipts = Receipt.objects.filter(
        customer=request.user
    ).order_by('-created_at')[:5]  # Changed from date to created_at

    context = {
        'form': form,
        'appointments': appointments,
        'receipts': receipts,
    }
    
    return render(request, 'User_Management/profile.html', context)

@login_required
def delete_profile(request):
    user = request.user
    user.delete()
    messages.success(request, 'Profile deleted successfully')
    return redirect('User_Management:custom_login')


#download and view receipts
def download_receipt(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id, customer=request.user)
    template = get_template('User_Management/receipt_pdf.html')
    html = template.render({'receipt': receipt})

    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    pdf = pdfkit.from_string(html, False, configuration=config)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{receipt.id}.pdf"'
    return response

@login_required
def view_receipts(request):
    receipts = Receipt.objects.filter(customer=request.user)
    return render(request, 'user_management/receipts.html', {'receipts': receipts})

#add stylist
@login_required 
def add_stylist(request): 
    if request.method == 'POST':
        form = StaffForm(request.POST) 
        if form.is_valid(): 
            form.save() 
            messages.success(request, 'Stylist added successfully!') 
            return redirect('User_Management:add_staff') 
        else:
            messages.error(request, 'Error adding stylist')
    else: 
        form = StaffForm()
    return render(request, 'user_management/add_staff.html', {'form': form})
@login_required
def add_product(request):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
        
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('User_Management:admin_dashboard')
    else:
        form = ProductForm()
    
    return render(request, 'User_Management/add_product.html', {'form': form})

@login_required
def add_service(request):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
        
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service added successfully!')
            return redirect('User_Management:admin_dashboard')
    else:
        form = ServiceForm()
    
    # Get all categories for context
    categories = ServiceCategory.objects.all()
    
    context = {
        'form': form,
        'categories': categories,
    }
    
    return render(request, 'User_Management/add_service.html', context)

@login_required
def add_staff(request):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
        
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the user but don't commit to DB yet
            staff = form.save(commit=False)
            staff.role = 'staff'  # Set the role to 'staff'
            staff.is_staff = True  # Set is_staff to True
            staff.save()
            
            # Get expertise and rating from the form
            expertise = form.cleaned_data.get('expertise')
            rating = form.cleaned_data.get('rating')
            
            # Create Stylist profile for the staff member
            stylist = Stylist.objects.create(
                user=staff,
                rating=rating
            )
            
            # Add services to the stylist's expertise
            # For simplicity, let's add a default service if no expertise is specified
            try:
                # Try to get the service by name or ID
                if expertise.isdigit():
                    service = Service.objects.get(id=expertise)
                else:
                    # Try to find a service with a name containing the expertise text
                    service = Service.objects.filter(name__icontains=expertise).first()
                    if not service:
                        # If no matching service, get the first service
                        service = Service.objects.first()
                
                if service:
                    stylist.expertise.add(service)
                    print(f"Added service {service.name} to stylist {staff.username}'s expertise")
            except Exception as e:
                print(f"Error adding expertise: {str(e)}")
                # If there's any error, add all services to ensure the stylist has some expertise
                for service in Service.objects.all():
                    stylist.expertise.add(service)
                    print(f"Added all services to stylist {staff.username}'s expertise")
            
            messages.success(request, 'Staff member added successfully!')
            return redirect('User_Management:admin_dashboard')
    else:
        form = StaffForm()
    
    return render(request, 'User_Management/add_staff.html', {'form': form})

@login_required
def edit_service(request, service_id):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
    
    service = get_object_or_404(Service, id=service_id)
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service updated successfully!')
            return redirect('User_Management:admin_dashboard')
    else:
        form = ServiceForm(instance=service)
    
    return render(request, 'User_Management/edit_service.html', {'form': form, 'service': service})


@login_required
def edit_staff(request, staff_id):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
    
    staff_member = get_object_or_404(CustomUser, id=staff_id, role='staff')
    services = Service.objects.all()  # Get all services for the expertise selection
    
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=staff_member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member updated successfully!')
            return redirect('User_Management:admin_dashboard')
    else:
        form = StaffForm(instance=staff_member)
    
    return render(request, 'User_Management/edit_staff.html', {
        'form': form, 
        'staff_member': staff_member,
        'services': services  # Pass services to the template
    })


@login_required
def delete_staff(request, staff_id):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
    
    staff_member = get_object_or_404(CustomUser, id=staff_id, role='staff')
    staff_member.delete()
    messages.success(request, 'Staff member deleted successfully!')
    return redirect('User_Management:admin_dashboard')

@login_required
def edit_product(request, product_id):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
    
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('User_Management:admin_dashboard')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'User_Management/edit_product.html', {
        'form': form,
        'product': product
    })

@login_required
def delete_product(request, product_id):
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
    
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully!')
    return redirect('User_Management:admin_dashboard')

@login_required
def checkout(request):
    # Get all cart items for the current user
    cart_items = CartItem.objects.filter(customer=request.user)
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('User_Management:view_cart')
    
    # Calculate total
    total = sum(item.total_price() for item in cart_items)
    
    if request.method == 'POST':
        # Create a new receipt
        receipt = Receipt.objects.create(
            customer=request.user,
            total=total
        )
        
        # Process each cart item
        from Stock_Management.models import Product, StockTransaction
        
        for cart_item in cart_items:
            # Create receipt item
            ReceiptItem.objects.create(
                receipt=receipt,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            
            # Update product stock
            product = cart_item.product
            
            # Create a stock transaction to record the sale
            StockTransaction.objects.create(
                product=product,
                transaction_type='sale',
                quantity=cart_item.quantity,
                unit_price=product.price,
                total_amount=cart_item.quantity * product.price,
                reference_number=f"SALE-{receipt.id}",
                notes=f"Sale to {request.user.username}",
                created_by=request.user
            )
            
            # Update product stock
            product.current_stock -= cart_item.quantity
            product.save()
            
            # Create a purchase record
            Purchase.objects.create(
                customer=request.user,
                product=product,
                quantity=cart_item.quantity,
                total_price=cart_item.total_price()
            )
            
            # Delete cart item
            cart_item.delete()
        
        messages.success(request, 'Your order has been processed successfully!')
        return redirect('User_Management:view_receipts')
    
    return render(request, 'User_Management/checkout.html', {
        'cart_items': cart_items,
        'total': total
    })

#stylists

@login_required
def stylist_directory(request):
    stylists = CustomUser.objects.filter(role='staff')
    return render(request, 'User_Management/stylist_directory.html', {'stylists': stylists})


@login_required
def stylist_profile(request, stylist_id):
    stylist = get_object_or_404(CustomUser, id=stylist_id, role='staff')
    expertise = stylist.expertise.all()
    ratings = Rating.objects.filter(stylist=stylist)
    show_appointments = (
        request.user.role == 'admin' or
        (request.user.role == 'staff' and request.user.id == stylist.id)
    )
    appointments = Appointment.objects.filter(stylist=stylist) if show_appointments else None
    context = {
        'stylist': stylist,
        'expertise': expertise,
        'ratings': ratings,
        'show_appointments': show_appointments,
        'appointments': appointments,
    }
    return render(request, 'User_Management/stylist_profile.html', context)


@login_required
def staff_dashboard(request):
    if not (request.user.role == 'staff'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')

    today = timezone.now().date()
    # Today's appointments for this stylist
    todays_appointments = Appointment.objects.filter(
        stylist=request.user,
        date=today
    ).order_by('time')
    
    # Appointment statistics
    completed_appointments = Appointment.objects.filter(
        stylist=request.user,
        status='Completed'
    ).count()
    
    cancelled_appointments = Appointment.objects.filter(
        stylist=request.user,
        status='Cancelled'
    ).count()
    
    upcoming_appointments = Appointment.objects.filter(
        stylist=request.user,
        date__gte=today,
        status__in=['Pending', 'Confirmed']
    ).count()
    
    # Calculate total appointments
    total_appointments = Appointment.objects.filter(
        stylist=request.user
    ).count()

    # Frequent customers (by appointment count)
    frequent_customers = (
        Appointment.objects.filter(stylist=request.user)
        .values('customer__id', 'customer__first_name', 'customer__last_name', 'customer__username')
        .annotate(appointment_count=Count('id'))
        .order_by('-appointment_count')[:5]
    )

    context = {
        'todays_appointments': todays_appointments,
        'today_appointments_count': todays_appointments.count(),
        'frequent_customers': frequent_customers,
        'user': request.user,
        'completed_appointments_count': completed_appointments,
        'cancelled_appointments_count': cancelled_appointments,
        'upcoming_appointments_count': upcoming_appointments,
        'total_appointments': total_appointments,
    }
    return render(request, 'User_Management/staff_dashboard.html', context)

@login_required
def customer_list(request):
    """
    Display a list of customers who have had appointments with the logged-in stylist.
    """
    # Get all appointments for this stylist
    stylist_appointments = Appointment.objects.filter(stylist=request.user)
    
    # Get unique customers from these appointments
    customer_ids = stylist_appointments.values_list('customer', flat=True).distinct()
    customers = CustomUser.objects.filter(id__in=customer_ids)
    
    # For each customer, get their appointment history with this stylist
    customer_data = []
    for customer in customers:
        appointments = stylist_appointments.filter(customer=customer)
        completed_count = appointments.filter(status='Completed').count()
        cancelled_count = appointments.filter(status='Cancelled').count()
        upcoming_count = appointments.filter(
            status__in=['Pending', 'Confirmed'],
            date__gte=datetime.now().date()
        ).count()
        
        # Get the latest appointment
        latest_appointment = appointments.order_by('-date', '-time').first()
        
        # Get most common service booked
        service_counts = {}
        for appointment in appointments:
            service_name = appointment.service.name
            service_counts[service_name] = service_counts.get(service_name, 0) + 1
        
        most_common_service = None
        if service_counts:
            most_common_service = max(service_counts.items(), key=lambda x: x[1])[0]
        
        customer_data.append({
            'customer': customer,
            'completed_count': completed_count,
            'cancelled_count': cancelled_count,
            'upcoming_count': upcoming_count,
            'total_count': appointments.count(),
            'latest_appointment': latest_appointment,
            'most_common_service': most_common_service
        })
    
    # Sort customers by total appointments (most frequent first)
    customer_data.sort(key=lambda x: x['total_count'], reverse=True)
    
    context = {
        'customer_data': customer_data,
        'active_tab': 'customers'
    }
    
    return render(request, 'User_Management/customer_list.html', context)

@login_required
def update_total_earned_points(request):
    """
    One-time function to update total_earned_points for all users based on their
    appointment history and previous payments.
    Only accessible by admin users.
    """
    if not request.user.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('User_Management:home')
    
    # Get all customers
    customers = CustomUser.objects.filter(role='customer')
    updated_count = 0
    
    for customer in customers:
        # Calculate points from appointments (10 points per appointment)
        appointment_count = Appointment.objects.filter(
            customer=customer, 
            status__in=['Completed', 'Confirmed']
        ).count()
        
        appointment_points = appointment_count * 10
        
        # Calculate points from purchases (1 point per $10 spent)
        purchases_total = Purchase.objects.filter(
            customer=customer
        ).aggregate(total=models.Sum('total_price'))['total'] or 0
        
        purchase_points = int(purchases_total / 10)
        
        # Calculate points from current loyalty_points and any active discount
        current_points = customer.loyalty_points
        
        # If customer has an active discount, add the threshold that was used
        discount_threshold_points = 0
        if customer.discount > 0:
            # Find the threshold that matches the discount
            discount_tiers = [
                (4000, 100, 14),  # 100% off for 14 days at 4000 points
                (2000, 100, 10),  # 100% off for 10 days at 2000 points
                (1000, 100, 7),   # 100% off for 7 days at 1000 points
                (500, 50, 7),     # 50% off for 7 days at 500 points
                (200, 20, 7),     # 20% off for 7 days at 200 points
                (100, 10, 7),     # 10% off for 7 days at 100 points
            ]
            
            for threshold, discount, days in discount_tiers:
                if customer.discount == discount:
                    discount_threshold_points = threshold
                    break
        
        # Total earned points is the sum of all sources
        total_earned = customer.loyalty_points + discount_threshold_points
        
        # For a new user with no history, use the calculated points if higher
        if total_earned == 0 and (appointment_points + purchase_points) > 0:
            total_earned = appointment_points + purchase_points
        
        # Only update if the calculated value is greater than the current value
        if total_earned > customer.total_earned_points:
            customer.total_earned_points = total_earned
            customer.save(update_fields=['total_earned_points'])
            updated_count += 1
    
    messages.success(request, f"Successfully updated total earned points for {updated_count} customers.")
    return redirect('User_Management:admin_dashboard')

def update_user_total_earned_points(user):
    """
    Update total_earned_points for a specific user based on their
    appointment history and previous payments.
    """
    if user.role != 'customer':
        return
    
    # Calculate points from appointments (10 points per appointment)
    appointment_count = Appointment.objects.filter(
        customer=user, 
        status__in=['Completed', 'Confirmed']
    ).count()
    
    appointment_points = appointment_count * 10
    
    # Calculate points from purchases (1 point per $10 spent)
    purchases_total = Purchase.objects.filter(
        customer=user
    ).aggregate(total=models.Sum('total_price'))['total'] or 0
    
    purchase_points = int(purchases_total / 10)
    
    # If user has an active discount, add the threshold that was used
    discount_threshold_points = 0
    if user.discount > 0:
        # Find the threshold that matches the discount
        discount_tiers = [
            (4000, 100, 14),  # 100% off for 14 days at 4000 points
            (2000, 100, 10),  # 100% off for 10 days at 2000 points
            (1000, 100, 7),   # 100% off for 7 days at 1000 points
            (500, 50, 7),     # 50% off for 7 days at 500 points
            (200, 20, 7),     # 20% off for 7 days at 200 points
            (100, 10, 7),     # 10% off for 7 days at 100 points
        ]
        
        for threshold, discount, days in discount_tiers:
            if user.discount == discount:
                discount_threshold_points = threshold
                break
    
    # Total earned points is the sum of all sources
    # Current loyalty_points represents unspent points, so we add:
    # 1. Current unspent points
    # 2. Points spent on discounts (if any)
    # We don't need to add appointment/purchase points separately as they're already 
    # reflected in the user's current points + any spent on discounts
    total_earned = user.loyalty_points + discount_threshold_points
    
    # For a new user with no history, use the calculated points if higher
    if total_earned == 0 and (appointment_points + purchase_points) > 0:
        total_earned = appointment_points + purchase_points
    
    # Only update if the calculated value is greater than the current value
    if total_earned > user.total_earned_points:
        user.total_earned_points = total_earned
        user.save(update_fields=['total_earned_points'])

@login_required
def reset_total_earned_points(request):
    """
    Reset total_earned_points to a reasonable value for the current user.
    This is a temporary fix for users with inflated point values.
    """
    if request.user.role != 'customer':
        messages.error(request, "This function is only available for customers.")
        return redirect('User_Management:home')
    
    user = request.user
    
    # If user has a discount, calculate total as current points + discount threshold
    discount_threshold_points = 0
    if user.discount > 0:
        # Find the threshold that matches the discount
        discount_tiers = [
            (4000, 100, 14),  # 100% off for 14 days at 4000 points
            (2000, 100, 10),  # 100% off for 10 days at 2000 points
            (1000, 100, 7),   # 100% off for 7 days at 1000 points
            (500, 50, 7),     # 50% off for 7 days at 500 points
            (200, 20, 7),     # 20% off for 7 days at 200 points
            (100, 10, 7),     # 10% off for 7 days at 100 points
        ]
        
        for threshold, discount, days in discount_tiers:
            if user.discount == discount:
                discount_threshold_points = threshold
                break
    
    # Set total earned points to a reasonable value
    total_earned = user.loyalty_points + discount_threshold_points
    
    # Ensure it's at least 10 points per appointment (up to 10 appointments)
    appointment_count = min(10, Appointment.objects.filter(
        customer=user, 
        status__in=['Completed', 'Confirmed']
    ).count())
    
    appointment_points = appointment_count * 10
    
    # Use the larger of the two calculations
    total_earned = max(total_earned, appointment_points)
    
    # Update the user's total earned points
    user.total_earned_points = total_earned
    user.save(update_fields=['total_earned_points'])
    
    messages.success(request, f"Your total earned points have been reset to {total_earned}.")
    return redirect('User_Management:profile')
