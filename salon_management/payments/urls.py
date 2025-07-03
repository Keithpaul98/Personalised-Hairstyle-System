from django.urls import path
from . import views, webhooks

app_name = 'payments'

urlpatterns = [
    # Product payment paths (redirects to User_Management for receipts)
    path('checkout/', views.checkout, name='checkout'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancelled/', views.payment_cancelled, name='payment_cancelled'),
    
    # Appointment payment and receipt paths
    path('appointment/<int:appointment_id>/checkout/', 
         views.appointment_checkout, 
         name='appointment_checkout'),
    path('appointment/<int:appointment_id>/success/', 
         views.appointment_payment_success, 
         name='appointment_payment_success'),
    path('appointment/<int:appointment_id>/cancelled/', 
         views.appointment_payment_cancelled, 
         name='appointment_payment_cancelled'),
    path('appointment/receipt/<int:receipt_id>/', 
         views.view_appointment_receipt, 
         name='view_appointment_receipt'),
    path('appointment/receipt/<int:receipt_id>/download/', 
         views.download_appointment_receipt, 
         name='download_appointment_receipt'),
    path('webhook/', webhooks.stripe_webhook, name='webhook'), 
]
