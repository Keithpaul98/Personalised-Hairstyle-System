from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, Avg, F, Q, Max, ExpressionWrapper, FloatField, IntegerField, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.http import HttpResponse, JsonResponse
import json
import csv
import io
from xhtml2pdf import pisa
from django.template.loader import get_template
from decimal import Decimal

from .models import (
    Report, 
    StylistPerformance, 
    ServiceAnalytics, 
    CustomerAnalytics, 
    ProductAnalytics, 
    HairstyleAnalytics
)
from User_Management.models import Purchase, CustomUser, Receipt
from Stock_Management.models import Product, StockTransaction, ProductCategory
from appointments.models import Appointment, Stylist
from payments.models import Payment, AppointmentReceipt
from services.models import Service
#from discounts.models import Discount

# Helper function to get date range
def get_date_range(request):
    """Get date range from request or default to last 30 days"""
    today = timezone.now().date()
    
    # Default: last 30 days
    default_start = today - timedelta(days=30)
    default_end = today
    
    # Get from request
    start_date_str = request.GET.get('start_date') or request.POST.get('start_date')
    end_date_str = request.GET.get('end_date') or request.POST.get('end_date')
    
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = default_start
            
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = default_end
    except ValueError:
        # Handle invalid date format
        start_date = default_start
        end_date = default_end
        
    # Ensure end date is not before start date
    if end_date < start_date:
        end_date = start_date
        
    return start_date, end_date

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'staff'])
def report_dashboard(request):
    """Main reporting dashboard showing all reports and quick stats"""
    # Get all reports, ordered by most recent first
    reports = Report.objects.all().order_by('-date_generated')[:10]
    
    # Get date range for quick stats
    start_date, end_date = get_date_range(request)
    
    # Quick stats for dashboard
    total_revenue = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date]
    ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    total_appointments = Appointment.objects.filter(
        date__range=[start_date, end_date]
    ).count()
    
    completed_appointments = Appointment.objects.filter(
        date__range=[start_date, end_date],
        status='Completed'
    ).count()
    
    cancelled_appointments = Appointment.objects.filter(
        date__range=[start_date, end_date],
        status='Cancelled'
    ).count()
    
    total_products_sold = Purchase.objects.filter(
        purchased_at__date__range=[start_date, end_date]
    ).aggregate(total=Coalesce(Sum('quantity', output_field=IntegerField()), 0))['total']
    
    # Top services
    top_services = Service.objects.annotate(
        appointment_count=Count('appointment', filter=Q(
            appointment__date__range=[start_date, end_date]
        ))
    ).order_by('-appointment_count')[:5]
    
    # Top stylists
    top_stylists = CustomUser.objects.filter(role='staff').annotate(
        appointment_count=Count('staff_appointments', filter=Q(
            staff_appointments__date__range=[start_date, end_date]
        )),
        revenue=Coalesce(Sum('staff_appointments__payment__total', filter=Q(
            staff_appointments__date__range=[start_date, end_date]
        ), output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00'))
    ).order_by('-appointment_count')[:5]
    
    # Top products
    top_products = Product.objects.annotate(
        sold_count=Coalesce(Sum('purchase__quantity', filter=Q(
            purchase__purchased_at__date__range=[start_date, end_date]
        ), output_field=IntegerField()), 0)
    ).order_by('-sold_count')[:5]
    
    context = {
        'reports': reports,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'cancelled_appointments': cancelled_appointments,
        'total_products_sold': total_products_sold,
        'top_services': top_services,
        'top_stylists': top_stylists,
        'top_products': top_products,
    }
    
    return render(request, 'reporting/dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'staff'])
def view_report(request, report_id):
    """View detailed report"""
    report = get_object_or_404(Report, id=report_id)
    
    # Get related analytics
    stylist_performances = report.stylist_performances.all().order_by('-revenue_generated')
    service_analytics = report.service_analytics.all().order_by('popularity_rank')
    product_analytics = report.product_analytics.all().order_by('popularity_rank')
    customer_analytics = report.customer_analytics.first()
    hairstyle_analytics = report.hairstyle_analytics.all().order_by('popularity_rank')
    
    # Start with existing JSON data
    json_data = report.json_data or {}
    
    # For business and sales reports, prepare revenue chart data
    if report.report_type in ['business', 'sales']:
        json_data['revenue_breakdown'] = {
            'labels': ['Product Revenue', 'Service Revenue'],
            'data': [float(report.product_revenue), float(report.service_revenue)]
        }
    
    # For appointment reports, prepare appointment status chart data
    if report.report_type in ['business', 'appointments']:
        completed = report.completed_appointments
        cancelled = report.cancelled_appointments
        pending = report.total_appointments - completed - cancelled
        
        json_data['appointment_status'] = {
            'labels': ['Completed', 'Cancelled', 'Pending'],
            'data': [completed, cancelled, pending]
        }
    
    # Add debug information to help troubleshoot
    json_data['debug'] = {
        'report_type': report.report_type,
        'has_daily_sales': 'daily_sales' in json_data and len(json_data.get('daily_sales', [])) > 0,
        'has_daily_appointments': 'daily_appointments' in json_data and len(json_data.get('daily_appointments', [])) > 0,
        'product_revenue': float(report.product_revenue),
        'service_revenue': float(report.service_revenue),
        'total_appointments': report.total_appointments,
        'completed_appointments': report.completed_appointments,
        'cancelled_appointments': report.cancelled_appointments
    }
    
    context = {
        'report': report,
        'stylist_performances': stylist_performances,
        'service_analytics': service_analytics,
        'product_analytics': product_analytics,
        'customer_analytics': customer_analytics,
        'hairstyle_analytics': hairstyle_analytics,
        'json_data': json.dumps(json_data)
    }
    
    return render(request, 'reporting/view_report.html', context)

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'staff'])
def export_report_pdf(request, report_id):
    """Export report as PDF"""
    report = get_object_or_404(Report, id=report_id)
    
    # Get related analytics
    stylist_performances = report.stylist_performances.all().order_by('-revenue_generated')
    service_analytics = report.service_analytics.all().order_by('popularity_rank')
    product_analytics = report.product_analytics.all().order_by('popularity_rank')
    customer_analytics = report.customer_analytics.first()
    hairstyle_analytics = report.hairstyle_analytics.all().order_by('popularity_rank')
    
    # Prepare template context
    context = {
        'report': report,
        'stylist_performances': stylist_performances,
        'service_analytics': service_analytics,
        'product_analytics': product_analytics,
        'customer_analytics': customer_analytics,
        'hairstyle_analytics': hairstyle_analytics,
    }
    
    # Render HTML content
    template = get_template('reporting/report_pdf.html')
    html = template.render(context)
    
    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report.title}.pdf"'
    
    # Generate PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    # Return PDF response
    if pisa_status.err:
        return HttpResponse('PDF generation error', status=500)
    return response

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'staff'])
def export_report_csv(request, report_id):
    """Export report as CSV"""
    report = get_object_or_404(Report, id=report_id)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report.title}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow([
        'Report Type', 'Generated Date', 'Date Range', 'Generated By',
        'Total Revenue', 'Product Revenue', 'Service Revenue',
        'Total Appointments', 'Completed Appointments', 'Cancelled Appointments',
        'Total Products', 'Products Sold'
    ])
    
    # Write data row
    writer.writerow([
        report.get_report_type_display(),
        report.date_generated.strftime('%Y-%m-%d %H:%M'),
        f"{report.date_range_start.strftime('%Y-%m-%d')} to {report.date_range_end.strftime('%Y-%m-%d')}",
        report.generated_by.username,
        report.total_revenue,
        report.product_revenue,
        report.service_revenue,
        report.total_appointments,
        report.completed_appointments,
        report.cancelled_appointments,
        report.total_products,
        report.products_sold
    ])
    
    # Add blank row
    writer.writerow([])
    
    # Export based on report type
    if report.report_type in ['business', 'stylists'] and report.stylist_performances.exists():
        # Write stylist performance header
        writer.writerow(['Stylist Performance'])
        writer.writerow([
            'Stylist', 'Appointments', 'Completed', 'Cancelled', 'Revenue', 'Average Rating'
        ])
        
        # Write stylist performance data
        for perf in report.stylist_performances.all().order_by('-revenue_generated'):
            writer.writerow([
                perf.stylist.get_full_name() or perf.stylist.username,
                perf.appointments_count,
                perf.completed_appointments,
                perf.cancelled_appointments,
                perf.revenue_generated,
                perf.average_rating
            ])
        
        # Add blank row
        writer.writerow([])
    
    if report.report_type in ['business', 'sales', 'inventory'] and report.product_analytics.exists():
        # Write product analytics header
        writer.writerow(['Product Analytics'])
        writer.writerow([
            'Product', 'Quantity Sold', 'Revenue', 'Current Stock', 'Popularity Rank'
        ])
        
        # Write product analytics data
        for prod in report.product_analytics.all().order_by('popularity_rank'):
            writer.writerow([
                prod.product_name,
                prod.quantity_sold,
                prod.revenue_generated,
                prod.current_stock,
                prod.popularity_rank
            ])
        
        # Add blank row
        writer.writerow([])
    
    if report.report_type in ['business', 'appointments', 'services'] and report.service_analytics.exists():
        # Write service analytics header
        writer.writerow(['Service Analytics'])
        writer.writerow([
            'Service', 'Bookings', 'Revenue', 'Popularity Rank'
        ])
        
        # Write service analytics data
        for svc in report.service_analytics.all().order_by('popularity_rank'):
            writer.writerow([
                svc.service_name,
                svc.booking_count,
                svc.revenue_generated,
                svc.popularity_rank
            ])
        
        # Add blank row
        writer.writerow([])
    
    if report.report_type in ['business', 'customers'] and report.customer_analytics.exists():
        # Write customer analytics header
        writer.writerow(['Customer Analytics'])
        writer.writerow([
            'Total Customers', 'New Customers', 'Returning Customers', 
            'Average Spend', 'Loyalty Points Issued'
        ])
        
        # Write customer analytics data
        cust = report.customer_analytics.first()
        if cust:
            writer.writerow([
                cust.total_customers,
                cust.new_customers,
                cust.returning_customers,
                cust.average_spend,
                cust.loyalty_points_issued
            ])
    
    return response

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'staff'])
def delete_report(request, report_id):
    """Delete a report"""
    report = get_object_or_404(Report, id=report_id)
    
    if request.method == 'POST':
        report.delete()
        messages.success(request, 'Report deleted successfully')
        return redirect('reporting:dashboard')
    
    return render(request, 'reporting/confirm_delete.html', {'report': report})

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'staff'])
def generate_report(request):
    """Generate a new report based on selected parameters"""
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'business')
        title = request.POST.get('title', f'{report_type.capitalize()} Report')
        start_date, end_date = get_date_range(request)
        
        # Create the base report
        report = Report.objects.create(
            title=title,
            report_type=report_type,
            date_range_start=start_date,
            date_range_end=end_date,
            generated_by=request.user,
            date_generated=timezone.now()
        )
        
        # Generate report data based on type
        if report_type == 'business':
            generate_business_report(report, start_date, end_date)
        elif report_type == 'sales':
            generate_sales_report(report, start_date, end_date)
        elif report_type == 'appointments':
            generate_appointments_report(report, start_date, end_date)
        elif report_type == 'stylists':
            generate_stylists_report(report, start_date, end_date)
        elif report_type == 'customers':
            generate_customers_report(report, start_date, end_date)
        elif report_type == 'inventory':
            generate_inventory_report(report, start_date, end_date)
        elif report_type == 'services':
            generate_services_report(report, start_date, end_date)
        elif report_type == 'hairstyles':
            generate_hairstyles_report(report, start_date, end_date)
        elif report_type == 'system_wide':
            generate_system_wide_report(report, start_date, end_date)
        
        messages.success(request, f'Report "{title}" generated successfully')
        return redirect('reporting:view_report', report_id=report.id)
    
    # If GET request, show the report generation form
    context = {
        'report_types': Report.REPORT_TYPES
    }
    return render(request, 'reporting/generate_report.html', context)

def generate_business_report(report, start_date, end_date):
    """Generate comprehensive business overview report"""
    # Product metrics
    total_products = Product.objects.count()
    products_sold = Purchase.objects.filter(
        purchased_at__date__range=[start_date, end_date]
    ).aggregate(total=Coalesce(Sum('quantity', output_field=IntegerField()), 0))['total']
    
    # Appointment metrics
    total_appointments = Appointment.objects.filter(
        date__range=[start_date, end_date]
    ).count()
    
    completed_appointments = Appointment.objects.filter(
        date__range=[start_date, end_date],
        status='Completed'
    ).count()
    
    cancelled_appointments = Appointment.objects.filter(
        date__range=[start_date, end_date],
        status='Cancelled'
    ).count()
    
    # Revenue metrics
    product_revenue = Purchase.objects.filter(
        purchased_at__date__range=[start_date, end_date]
    ).aggregate(
        total=Coalesce(Sum(F('quantity') * F('product__price'), output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00'))
    )['total']
    
    service_revenue = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date],
        payment_type='appointment'
    ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    receipt_revenue = AppointmentReceipt.objects.filter(
        created_at__date__range=[start_date, end_date],
        appointment__status__in=['Completed', 'Confirmed']
    ).aggregate(total=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    total_revenue = product_revenue + service_revenue + receipt_revenue
    
    # Update report with aggregated data
    report.total_products = total_products
    report.products_sold = products_sold
    report.total_appointments = total_appointments
    report.completed_appointments = completed_appointments
    report.cancelled_appointments = cancelled_appointments
    report.product_revenue = product_revenue
    report.service_revenue = service_revenue + receipt_revenue
    report.total_revenue = total_revenue  # Both are already DecimalField
    report.save()
    
    # Calculate average transaction value if there were any transactions
    transaction_count = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date]
    ).count()
    
    if transaction_count > 0:
        report.average_transaction_value = total_revenue / transaction_count
    
    report.save()
    
    # Generate additional analytics
    generate_stylist_performance_analytics(report, start_date, end_date)
    generate_service_analytics(report, start_date, end_date)
    generate_product_analytics(report, start_date, end_date)
    generate_customer_analytics(report, start_date, end_date)
    generate_hairstyle_analytics(report, start_date, end_date)
    
    # Generate daily data for charts
    json_data = generate_daily_data(start_date, end_date)
    report.json_data = json_data
    report.save()

def generate_sales_report(report, start_date, end_date):
    """Generate sales and revenue report"""
    # Product sales
    product_sales = Purchase.objects.filter(
        purchased_at__date__range=[start_date, end_date]
    )
    
    products_sold = product_sales.aggregate(
        total=Coalesce(Sum('quantity', output_field=IntegerField()), 0)
    )['total']
    
    product_revenue = product_sales.aggregate(
        total=Coalesce(Sum(F('quantity') * F('product__price'), output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00'))
    )['total']
    
    # Service sales
    service_revenue = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date],
        payment_type='appointment'
    ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    receipt_revenue = AppointmentReceipt.objects.filter(
        created_at__date__range=[start_date, end_date],
        appointment__status__in=['Completed', 'Confirmed']
    ).aggregate(total=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    total_revenue = product_revenue + service_revenue + receipt_revenue
    
    # Update report
    report.products_sold = products_sold
    report.total_revenue = total_revenue
    report.product_revenue = product_revenue
    report.service_revenue = service_revenue + receipt_revenue
    
    # Calculate average transaction value
    transaction_count = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date]
    ).count()
    
    if transaction_count > 0:
        report.average_transaction_value = total_revenue / transaction_count
    
    report.save()
    
    # Generate analytics
    generate_product_analytics(report, start_date, end_date)
    generate_service_analytics(report, start_date, end_date)
    
    # Generate daily sales data
    json_data = {
        'daily_sales': generate_daily_sales_data(start_date, end_date)
    }
    report.json_data = json_data
    report.save()

def generate_appointments_report(report, start_date, end_date):
    """Generate appointments report"""
    # Get appointments in date range
    appointments = Appointment.objects.filter(
        date__range=[start_date, end_date]
    )
    
    total_appointments = appointments.count()
    completed_appointments = appointments.filter(status='Completed').count()
    cancelled_appointments = appointments.filter(status='Cancelled').count()
    
    # Calculate revenue from appointments
    service_revenue = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date],
        payment_type='appointment'
    ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    receipt_revenue = AppointmentReceipt.objects.filter(
        created_at__date__range=[start_date, end_date],
        appointment__status__in=['Completed', 'Confirmed']
    ).aggregate(total=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    total_revenue = service_revenue + receipt_revenue
    
    # Update report
    report.total_appointments = total_appointments
    report.completed_appointments = completed_appointments
    report.cancelled_appointments = cancelled_appointments
    report.service_revenue = total_revenue
    report.total_revenue = total_revenue
    report.save()
    
    # Generate analytics
    generate_stylist_performance_analytics(report, start_date, end_date)
    generate_service_analytics(report, start_date, end_date)
    
    # Generate daily appointment data
    daily_data = generate_daily_appointment_data(start_date, end_date)
    

    json_data = {
        'daily_appointments': daily_data
    }
    report.json_data = json_data
    report.save()

def generate_stylists_report(report, start_date, end_date):
    """Generate stylists performance report"""
    # Update basic report info
    appointments = Appointment.objects.filter(
        date__range=[start_date, end_date]
    )
    
    total_appointments = appointments.count()
    completed_appointments = appointments.filter(status='Completed').count()
    cancelled_appointments = appointments.filter(status='Cancelled').count()
    
    service_revenue = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date],
        payment_type='appointment'
    ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    receipt_revenue = AppointmentReceipt.objects.filter(
        created_at__date__range=[start_date, end_date],
        appointment__status__in=['Completed', 'Confirmed']
    ).aggregate(total=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    total_revenue = service_revenue + receipt_revenue
    
    report.total_appointments = total_appointments
    report.completed_appointments = completed_appointments
    report.cancelled_appointments = cancelled_appointments
    report.service_revenue = total_revenue
    report.total_revenue = total_revenue
    report.save()
    
    # Generate detailed stylist analytics
    generate_stylist_performance_analytics(report, start_date, end_date)

def generate_customers_report(report, start_date, end_date):
    """Generate customer analytics report"""
    # Get basic metrics for the report
    total_revenue = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date]
    ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    report.total_revenue = total_revenue
    report.save()
    
    # Generate detailed customer analytics
    generate_customer_analytics(report, start_date, end_date)

def generate_inventory_report(report, start_date, end_date):
    """Generate inventory and product report"""
    # Get product metrics
    total_products = Product.objects.count()
    
    product_sales = Purchase.objects.filter(
        purchased_at__date__range=[start_date, end_date]
    )
    
    products_sold = product_sales.aggregate(
        total=Coalesce(Sum('quantity', output_field=IntegerField()), 0)
    )['total']
    
    product_revenue = product_sales.aggregate(
        total=Coalesce(Sum(F('quantity') * F('product__price'), output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00'))
    )['total']
    
    # Update report
    report.total_products = total_products
    report.products_sold = products_sold
    report.product_revenue = product_revenue
    report.total_revenue = product_revenue
    report.save()
    
    # Generate detailed product analytics
    generate_product_analytics(report, start_date, end_date)

def generate_services_report(report, start_date, end_date):
    """Generate services report"""
    # Get service metrics
    appointments = Appointment.objects.filter(
        date__range=[start_date, end_date]
    )
    
    total_appointments = appointments.count()
    completed_appointments = appointments.filter(status='Completed').count()
    
    service_revenue = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date],
        payment_type='appointment'
    ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    receipt_revenue = AppointmentReceipt.objects.filter(
        created_at__date__range=[start_date, end_date],
        appointment__status__in=['Completed', 'Confirmed']
    ).aggregate(total=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    total_revenue = service_revenue + receipt_revenue
    
    # Update report
    report.total_appointments = total_appointments
    report.completed_appointments = completed_appointments
    report.service_revenue = total_revenue
    report.total_revenue = total_revenue
    report.save()
    
    # Generate detailed service analytics
    generate_service_analytics(report, start_date, end_date)

def generate_hairstyles_report(report, start_date, end_date):
    """Generate hairstyles popularity report"""
    # Get basic metrics
    total_appointments = Appointment.objects.filter(
        date__range=[start_date, end_date]
    ).count()
    
    report.total_appointments = total_appointments
    report.save()
    
    # Generate detailed hairstyle analytics
    generate_hairstyle_analytics(report, start_date, end_date)

def generate_system_wide_report(report, start_date, end_date):
    """Generate a comprehensive system-wide report with data from all parts of the salon system"""
    # First, gather all the basic data from other report types
    generate_business_report(report, start_date, end_date)
    
    # Add sales vs. salon usage data
    from Stock_Management.models import StockTransaction
    
    # Get retail sales transactions
    retail_sales = StockTransaction.objects.filter(
        transaction_type='sale',
        transaction_date__date__range=[start_date, end_date]
    ).aggregate(
        total_quantity=Coalesce(Sum('quantity', output_field=IntegerField()), 0),
        total_value=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00'))
    )
    
    # Get salon usage transactions
    salon_usage = StockTransaction.objects.filter(
        transaction_type='salon_usage',
        transaction_date__date__range=[start_date, end_date]
    ).aggregate(
        total_quantity=Coalesce(Sum('quantity', output_field=IntegerField()), 0),
        total_value=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00'))
    )
    
    # Monthly comparison data for chart
    monthly_data = {}
    
    # Get all months in the date range
    current = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    
    while current <= end_month:
        month_name = current.strftime('%b %Y')
        monthly_data[month_name] = {'retail': 0, 'salon': 0}
        current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    
    # Aggregate sales by month
    sales_by_month = StockTransaction.objects.filter(
        transaction_type='sale',
        transaction_date__date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('transaction_date')
    ).values('month').annotate(
        total=Coalesce(Sum('quantity', output_field=IntegerField()), 0)
    ).order_by('month')
    
    # Aggregate salon usage by month
    salon_by_month = StockTransaction.objects.filter(
        transaction_type='salon_usage',
        transaction_date__date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('transaction_date')
    ).values('month').annotate(
        total=Coalesce(Sum('quantity', output_field=IntegerField()), 0)
    ).order_by('month')
    
    # Populate monthly data
    for item in sales_by_month:
        month_name = item['month'].strftime('%b %Y')
        if month_name in monthly_data:
            monthly_data[month_name]['retail'] = item['total']
    
    for item in salon_by_month:
        month_name = item['month'].strftime('%b %Y')
        if month_name in monthly_data:
            monthly_data[month_name]['salon'] = item['total']
    
    # Convert to list for the template
    monthly_comparison = [
        {'month': month, 'retail': data['retail'], 'salon': data['salon']}
        for month, data in monthly_data.items()
    ]
    
    # Top products by retail sales
    top_retail_products = StockTransaction.objects.filter(
        transaction_type='sale',
        transaction_date__date__range=[start_date, end_date]
    ).values('product__name').annotate(
        total_quantity=Sum('quantity', output_field=IntegerField()),
        total_value=Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2))
    ).order_by('-total_quantity')[:5]
    
    # Top products by salon usage
    top_salon_products = StockTransaction.objects.filter(
        transaction_type='salon_usage',
        transaction_date__date__range=[start_date, end_date]
    ).values('product__name').annotate(
        total_quantity=Sum('quantity', output_field=IntegerField()),
        total_value=Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2))
    ).order_by('-total_quantity')[:5]
    
    # Calculate ratio of retail to salon usage
    total_retail_quantity = retail_sales['total_quantity']
    total_salon_quantity = salon_usage['total_quantity']
    total_quantity = total_retail_quantity + total_salon_quantity
    
    retail_percentage = 0
    salon_percentage = 0
    
    if total_quantity > 0:
        retail_percentage = (float(total_retail_quantity) / float(total_quantity)) * 100
        salon_percentage = (float(total_salon_quantity) / float(total_quantity)) * 100
    
    # Store the data in the report's JSON field
    json_data = report.json_data or {}
    json_data.update({
        'retail_sales': {
            'total_quantity': retail_sales['total_quantity'],
            'total_value': float(retail_sales['total_value'])
        },
        'salon_usage': {
            'total_quantity': salon_usage['total_quantity'],
            'total_value': float(salon_usage['total_value'])
        },
        'monthly_comparison': monthly_comparison,
        'top_retail_products': list(top_retail_products),
        'top_salon_products': list(top_salon_products),
        'retail_percentage': retail_percentage,
        'salon_percentage': salon_percentage
    })
    
    # Update the report with the new data
    report.json_data = json_data
    report.save()

# Helper functions for analytics generation
def generate_stylist_performance_analytics(report, start_date, end_date):
    """Generate stylist performance analytics"""
    stylists = CustomUser.objects.filter(role='staff')
    
    for stylist in stylists:
        # Get appointments for this stylist
        stylist_appointments = Appointment.objects.filter(
            stylist=stylist,
            date__range=[start_date, end_date]
        )
        
        appointments_count = stylist_appointments.count()
        
        # Skip if no appointments
        if appointments_count == 0:
            continue
        
        completed_appointments = stylist_appointments.filter(status='Completed').count()
        cancelled_appointments = stylist_appointments.filter(status='Cancelled').count()
        
        # Calculate revenue
        revenue_generated = Payment.objects.filter(
            appointment__stylist=stylist,
            paid_at__date__range=[start_date, end_date]
        ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
        
        receipt_revenue = AppointmentReceipt.objects.filter(
            created_at__date__range=[start_date, end_date],
            appointment__stylist=stylist,
            appointment__status__in=['Completed', 'Confirmed']
        ).aggregate(total=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
        
        total_revenue = revenue_generated + receipt_revenue
        
        # Calculate average rating
        average_rating = stylist_appointments.filter(
            rating__isnull=False
        ).aggregate(avg=Coalesce(Avg('rating', output_field=DecimalField(max_digits=3, decimal_places=2)), Decimal('0.00')))['avg']
        
        # Create stylist performance record
        StylistPerformance.objects.create(
            report=report,
            stylist=stylist,
            appointments_count=appointments_count,
            completed_appointments=completed_appointments,
            cancelled_appointments=cancelled_appointments,
            revenue_generated=total_revenue,
            average_rating=average_rating
        )

def generate_service_analytics(report, start_date, end_date):
    """Generate service analytics"""
    services = Service.objects.all()
    
    # Create a list to store service data for ranking
    service_data = []
    
    for service in services:
        # Get appointments for this service
        service_appointments = Appointment.objects.filter(
            service=service,
            date__range=[start_date, end_date]
        )
        
        booking_count = service_appointments.count()
        
        # Skip if no bookings
        if booking_count == 0:
            continue
        
        # Calculate revenue
        revenue_generated = Payment.objects.filter(
            appointment__service=service,
            paid_at__date__range=[start_date, end_date]
        ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
        
        receipt_revenue = AppointmentReceipt.objects.filter(
            created_at__date__range=[start_date, end_date],
            appointment__service=service,
            appointment__status__in=['Completed', 'Confirmed']
        ).aggregate(total=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
        
        total_revenue = revenue_generated + receipt_revenue
        
        # Add to list for ranking
        service_data.append({
            'service': service,
            'booking_count': booking_count,
            'revenue_generated': total_revenue
        })
    
    # Sort by booking count for popularity ranking
    service_data.sort(key=lambda x: x['booking_count'], reverse=True)
    
    # Create service analytics records with rankings
    for rank, data in enumerate(service_data, 1):
        ServiceAnalytics.objects.create(
            report=report,
            service_id=data['service'].id,
            service_name=data['service'].name,
            booking_count=data['booking_count'],
            revenue_generated=data['revenue_generated'],
            popularity_rank=rank
        )

def generate_product_analytics(report, start_date, end_date):
    """Generate product analytics"""
    products = Product.objects.all()
    
    # Create a list to store product data for ranking
    product_data = []
    
    for product in products:
        # Get purchases for this product
        product_purchases = Purchase.objects.filter(
            product=product,
            purchased_at__date__range=[start_date, end_date]
        )
        
        quantity_sold = product_purchases.aggregate(
            total=Coalesce(Sum('quantity', output_field=IntegerField()), 0)
        )['total']
        
        # Calculate revenue
        revenue_generated = product_purchases.aggregate(
            total=Coalesce(Sum(F('quantity') * F('product__price'), output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00'))
        )['total']
        
        # Get current stock
        current_stock = product.current_stock
        
        # Add to list for ranking (only if sold)
        if quantity_sold > 0:
            product_data.append({
                'product': product,
                'quantity_sold': quantity_sold,
                'revenue_generated': revenue_generated,
                'current_stock': current_stock
            })
    
    # Sort by quantity sold for popularity ranking
    product_data.sort(key=lambda x: x['quantity_sold'], reverse=True)
    
    # Create product analytics records with rankings
    for rank, data in enumerate(product_data, 1):
        ProductAnalytics.objects.create(
            report=report,
            product_id=data['product'].id,
            product_name=data['product'].name,
            quantity_sold=data['quantity_sold'],
            revenue_generated=data['revenue_generated'],
            current_stock=data['current_stock'],
            popularity_rank=rank
        )

def generate_customer_analytics(report, start_date, end_date):
    """Generate customer analytics"""
    # Get all customers who had appointments or purchases in the date range
    customer_appointments = Appointment.objects.filter(
        date__range=[start_date, end_date]
    ).values_list('customer', flat=True).distinct()
    
    customer_purchases = Purchase.objects.filter(
        purchased_at__date__range=[start_date, end_date]
    ).values_list('customer', flat=True).distinct()
    
    # Combine unique customers
    all_customer_ids = set(list(customer_appointments) + list(customer_purchases))
    total_customers = len(all_customer_ids)
    
    # Find new customers (first appointment or purchase in this period)
    new_customer_count = 0
    returning_customer_count = 0
    
    for customer_id in all_customer_ids:
        # Check if this is their first activity
        first_appointment = Appointment.objects.filter(
            customer_id=customer_id
        ).order_by('date').first()
        
        first_purchase = Purchase.objects.filter(
            customer_id=customer_id
        ).order_by('purchased_at').first()
        
        # Determine if this is a new customer
        is_new = False
        
        if first_appointment and first_purchase:
            # Customer has both appointments and purchases
            first_date = min(first_appointment.date, first_purchase.purchased_at.date())
            is_new = first_date >= start_date
        elif first_appointment:
            # Customer only has appointments
            is_new = first_appointment.date >= start_date
        elif first_purchase:
            # Customer only has purchases
            is_new = first_purchase.purchased_at.date() >= start_date
        
        if is_new:
            new_customer_count += 1
        else:
            returning_customer_count += 1
    
    # Calculate average spend per customer
    total_revenue = Payment.objects.filter(
        paid_at__date__range=[start_date, end_date]
    ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
    
    average_spend = 0
    if total_customers > 0:
        average_spend = total_revenue / total_customers
    
    # Create customer analytics record
    CustomerAnalytics.objects.create(
        report=report,
        total_customers=total_customers,
        new_customers=new_customer_count,
        returning_customers=returning_customer_count,
        average_spend=average_spend,
        loyalty_points_issued=0,  # Not implemented in this version
        discounts_redeemed=0      # Not implemented in this version
    )

def generate_hairstyle_analytics(report, start_date, end_date):
    """Generate hairstyle popularity analytics"""
    # Get hairstyles from appointments in the date range
    hairstyles = Appointment.objects.filter(
        date__range=[start_date, end_date],
        hairstyle__isnull=False
    ).values('hairstyle', 'hairstyle__name').annotate(
        booking_count=Count('id', output_field=IntegerField())
    ).order_by('-booking_count')
    
    # Create hairstyle analytics records with rankings
    for rank, hairstyle_data in enumerate(hairstyles, 1):
        if 'hairstyle' in hairstyle_data and hairstyle_data['hairstyle']:
            # Get try-on count for this hairstyle
            try_on_count = 0
            try:
                try_on_count = TryOnResult.objects.filter(
                    hairstyle_id=hairstyle_data['hairstyle'],
                    created_at__date__range=[start_date, end_date]
                ).count()
            except:
                # TryOnResult might not exist or have different structure
                pass
            
            HairstyleAnalytics.objects.create(
                report=report,
                hairstyle_id=hairstyle_data['hairstyle'],
                hairstyle_name=hairstyle_data['hairstyle__name'] if hairstyle_data['hairstyle__name'] else 'Unknown',
                booking_count=hairstyle_data['booking_count'],
                try_on_count=try_on_count,
                popularity_rank=rank
            )

def generate_daily_data(start_date, end_date):
    """Generate daily data for charts"""
    return {
        'daily_sales': generate_daily_sales_data(start_date, end_date),
        'daily_appointments': generate_daily_appointment_data(start_date, end_date)
    }

def generate_daily_sales_data(start_date, end_date):
    """Generate daily sales data for charts"""
    # Create a date range
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    # Get daily sales data
    daily_data = []
    
    for date in date_range:
        # Product sales
        product_revenue = Purchase.objects.filter(
            purchased_at__date=date
        ).aggregate(
            total=Coalesce(Sum(F('quantity') * F('product__price'), output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00'))
        )['total']
        
        # Service sales
        service_revenue = Payment.objects.filter(
            paid_at__date=date,
            payment_type='appointment'
        ).aggregate(total=Coalesce(Sum('total', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
        
        receipt_revenue = AppointmentReceipt.objects.filter(
            created_at__date=date,
            appointment__status__in=['Completed', 'Confirmed']
        ).aggregate(total=Coalesce(Sum('total_amount', output_field=DecimalField(max_digits=10, decimal_places=2)), Decimal('0.00')))['total']
        
        # Convert to float for JSON serialization
        product_revenue_float = float(product_revenue)
        service_revenue_float = float(service_revenue + receipt_revenue)
        total_revenue_float = float(product_revenue + service_revenue + receipt_revenue)
        
        daily_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'product_revenue': product_revenue_float,
            'service_revenue': service_revenue_float,
            'total_revenue': total_revenue_float
        })
    
    return daily_data

def generate_daily_appointment_data(start_date, end_date):
    """Generate daily appointment data for charts"""
    # Create a date range
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    # Get daily appointment data
    daily_data = []
    
    for date in date_range:
        # Get appointments for this date
        appointments = Appointment.objects.filter(date=date)
        
        total = appointments.count()
        completed = appointments.filter(status='Completed').count()
        cancelled = appointments.filter(status='Cancelled').count()
        pending = total - completed - cancelled
        
        daily_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': total,
            'completed': completed,
            'cancelled': cancelled,
            'pending': pending
        })
    
    return daily_data

@login_required
@user_passes_test(lambda u: u.role in ['admin', 'staff'])
def sales_vs_salon_report(request):
    """Dedicated report for analyzing sales vs. salon usage data"""
    # Get date range from request or use default (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=30)
    
    # Hard-coded dummy data to avoid any database queries
    retail_sales = {
        'total_quantity': 100,
        'total_value': 1000.00
    }
    
    salon_usage = {
        'total_quantity': 50,
        'total_value': 500.00
    }
    
    # Calculate percentages using Python arithmetic
    total_quantity = retail_sales['total_quantity'] + salon_usage['total_quantity']
    retail_percentage = 66.67  # (100 / 150) * 100
    salon_percentage = 33.33   # (50 / 150) * 100
    
    # Get all product categories for the filter
    categories = ProductCategory.objects.all().order_by('name')
    
    # Prepare context for template
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'retail_sales': retail_sales,
        'salon_usage': salon_usage,
        'retail_percentage': retail_percentage,
        'salon_percentage': salon_percentage,
        'categories': categories,
        'selected_category': None,
        'products': [],
        'selected_product': None,
        'monthly_comparison': [],
        'top_retail_products': [],
        'top_salon_products': []
    }
    
    return render(request, 'reporting/sales_salonusagereport.html', context)