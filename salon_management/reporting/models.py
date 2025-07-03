from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Report(models.Model):
    REPORT_TYPES = (
        ('business', 'Business Overview'),
        ('sales', 'Sales Analysis'),
        ('appointments', 'Appointment Analysis'),
        ('stylists', 'Stylist Performance'),
        ('customers', 'Customer Analysis'),
        ('inventory', 'Inventory Analysis'),
        ('services', 'Services Analysis'),
        ('system_wide', 'System-Wide Analysis'),
        ('custom', 'Custom Report'),
    )
    
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, default='business')
    date_generated = models.DateTimeField(auto_now_add=True)
    date_range_start = models.DateField(default=timezone.now)
    date_range_end = models.DateField(default=timezone.now)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Business Overview Fields
    total_products = models.IntegerField(default=0)
    products_sold = models.IntegerField(default=0)
    total_appointments = models.IntegerField(default=0)
    completed_appointments = models.IntegerField(default=0)
    cancelled_appointments = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    product_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Additional metadata
    json_data = models.JSONField(null=True, blank=True, 
                                help_text="Additional report data in JSON format")
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.date_generated.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-date_generated']


class StylistPerformance(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='stylist_performances')
    stylist = models.ForeignKey(User, on_delete=models.CASCADE)
    appointments_count = models.IntegerField(default=0)
    completed_appointments = models.IntegerField(default=0)
    cancelled_appointments = models.IntegerField(default=0)
    revenue_generated = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Performance of {self.stylist.get_full_name()} - {self.report.date_generated.strftime('%Y-%m-%d')}"


class ServiceAnalytics(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='service_analytics')
    service_name = models.CharField(max_length=100)
    service_id = models.IntegerField()
    booking_count = models.IntegerField(default=0)
    revenue_generated = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    popularity_rank = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Analytics for {self.service_name} - {self.report.date_generated.strftime('%Y-%m-%d')}"


class CustomerAnalytics(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='customer_analytics')
    total_customers = models.IntegerField(default=0)
    new_customers = models.IntegerField(default=0)
    returning_customers = models.IntegerField(default=0)
    average_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loyalty_points_issued = models.IntegerField(default=0)
    discounts_redeemed = models.IntegerField(default=0)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Customer Analytics - {self.report.date_generated.strftime('%Y-%m-%d')}"


class ProductAnalytics(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='product_analytics')
    product_name = models.CharField(max_length=100)
    product_id = models.IntegerField()
    quantity_sold = models.IntegerField(default=0)
    revenue_generated = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_stock = models.IntegerField(default=0)
    popularity_rank = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Analytics for {self.product_name} - {self.report.date_generated.strftime('%Y-%m-%d')}"


class HairstyleAnalytics(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='hairstyle_analytics')
    hairstyle_name = models.CharField(max_length=100)
    hairstyle_id = models.IntegerField()
    try_on_count = models.IntegerField(default=0)
    booking_count = models.IntegerField(default=0)
    popularity_rank = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Analytics for {self.hairstyle_name} - {self.report.date_generated.strftime('%Y-%m-%d')}"