from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.list_appointments, name='my_appointments'),
    path('confirm/', views.confirm_appointment, name='confirm_appointment'),
    path('accept_alternative/', views.accept_alternative, name='accept_alternative'),
    path('book/', views.book_appointment, name='book_appointment'),
    path('book/<int:service_id>/', views.book_appointment, name='book_service'),
    path('success/<int:appointment_id>/', views.appointment_success, name='appointment_success'),
    path('history/', views.appointment_history, name='appointment_history'),
    path('rate/<int:appointment_id>/', views.rate_appointment, name='rate_appointment'),
    path('admin/appointments/', views.admin_appointments, name='admin_appointments'),
    path('details/<int:appointment_id>/', views.appointment_details, name='appointment_details'),
    path('edit/<int:appointment_id>/', views.edit_appointment, name='edit_appointment'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('update-status/<int:appointment_id>/', views.update_appointment_status, name='update_appointment_status'),
]