from django.contrib import admin
from .models import (
    Report, 
    StylistPerformance, 
    ServiceAnalytics, 
    CustomerAnalytics, 
    ProductAnalytics, 
    HairstyleAnalytics
)

class StylistPerformanceInline(admin.TabularInline):
    model = StylistPerformance
    extra = 0

class ServiceAnalyticsInline(admin.TabularInline):
    model = ServiceAnalytics
    extra = 0

class CustomerAnalyticsInline(admin.TabularInline):
    model = CustomerAnalytics
    extra = 0

class ProductAnalyticsInline(admin.TabularInline):
    model = ProductAnalytics
    extra = 0

class HairstyleAnalyticsInline(admin.TabularInline):
    model = HairstyleAnalytics
    extra = 0

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'date_generated', 'generated_by', 'total_revenue')
    list_filter = ('report_type', 'date_generated')
    search_fields = ('title', 'generated_by__username')
    readonly_fields = ('date_generated',)
    inlines = [
        StylistPerformanceInline,
        ServiceAnalyticsInline,
        CustomerAnalyticsInline,
        ProductAnalyticsInline,
        HairstyleAnalyticsInline,
    ]

@admin.register(StylistPerformance)
class StylistPerformanceAdmin(admin.ModelAdmin):
    list_display = ('stylist', 'report', 'appointments_count', 'revenue_generated', 'average_rating')
    list_filter = ('report__date_generated',)
    search_fields = ('stylist__username', 'stylist__first_name', 'stylist__last_name')

@admin.register(ServiceAnalytics)
class ServiceAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('service_name', 'report', 'booking_count', 'revenue_generated', 'popularity_rank')
    list_filter = ('report__date_generated', 'popularity_rank')
    search_fields = ('service_name',)

@admin.register(CustomerAnalytics)
class CustomerAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('report', 'total_customers', 'new_customers', 'average_spend', 'loyalty_points_issued')
    list_filter = ('report__date_generated',)

@admin.register(ProductAnalytics)
class ProductAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'report', 'quantity_sold', 'revenue_generated', 'current_stock', 'popularity_rank')
    list_filter = ('report__date_generated', 'popularity_rank')
    search_fields = ('product_name',)

@admin.register(HairstyleAnalytics)
class HairstyleAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('hairstyle_name', 'report', 'try_on_count', 'booking_count', 'popularity_rank')
    list_filter = ('report__date_generated', 'popularity_rank')
    search_fields = ('hairstyle_name',)
