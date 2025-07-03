from django.contrib import admin
from .models import Service, ServiceCategory, Product, Store

class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'duration_minutes', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')

class HairstyleAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_category', 'price', 'gender', 'is_active')
    list_filter = ('service_category', 'gender', 'is_active')

# Register all models
admin.site.register(ServiceCategory, ServiceCategoryAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Product)
admin.site.register(Store)
