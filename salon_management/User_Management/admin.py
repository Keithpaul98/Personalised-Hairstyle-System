from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Purchase, CartItem, Receipt, ReceiptItem
from services.models import Service  # Import Service from services app


class CustomUserAdmin(UserAdmin):
    def get_fieldsets(self, request, obj=None):
        if obj and obj.role == 'staff':
            return (
                (None, {'fields': ('username', 'password')}),
                ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'address')}),
                ('Staff info', {
                    'fields': ('role', 'expertise', 'average_rating', 'total_ratings'),
                    'description': 'Select the hairstyles this staff member can perform'
                }),
                ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
            )
        elif obj and obj.role == 'customer':
            return (
                (None, {'fields': ('username', 'password')}),
                ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'address')}),
                ('Customer info', {'fields': ('role', 'loyalty_points', 'discount', 'discount_expiry')}),
                ('Permissions', {'fields': ('is_active', 'groups', 'user_permissions')}),
            )
        return super().get_fieldsets(request, obj)
    
    def add_view(self, request, form_url='', extra_context=None):
        # Get the URL path to check if we're adding a staff member
        path = request.path.strip('/').split('/')
        if len(path) > 3 and path[-1] == 'add' and request.GET.get('role') == 'staff':
            self.form = self.get_form(request, None, fields=('username', 'password1', 'password2', 'role', 'is_staff'))
            # Set initial values for staff
            initial = {'role': 'staff', 'is_staff': True}
            extra_context = extra_context or {}
            extra_context['initial'] = initial
        return super().add_view(request, form_url, extra_context)

    list_display = ('username', 'email', 'role', 'get_expertise')
    list_filter = ('role', 'is_staff')
    filter_horizontal = ('groups', 'user_permissions', 'expertise')
    actions = ['make_staff']
    
    def make_staff(self, request, queryset):
        queryset.update(role='staff', is_staff=True)
    make_staff.short_description = "Mark selected users as staff"
    
    def get_expertise(self, obj):
        if obj.role == 'staff':
            return ", ".join([f"{service.name} (${service.price})" for service in obj.expertise.all()])
        return "-"
    get_expertise.short_description = 'Expertise'

# Register your models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Purchase)
admin.site.register(CartItem)
admin.site.register(Receipt)
admin.site.register(ReceiptItem)