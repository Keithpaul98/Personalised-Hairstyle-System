from django.contrib import admin
from .models import Stylist, Appointment, Rating
from User_Management.models import CustomUser

@admin.register(Stylist)
class StylistAdmin(admin.ModelAdmin):
    list_display = ['user', 'available', 'rating']
    filter_horizontal = ['expertise']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = CustomUser.objects.filter(role='staff')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['customer', 'stylist', 'service', 'date', 'time', 'status']

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'customer', 'stylist', 'rating']
