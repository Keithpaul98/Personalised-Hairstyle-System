import stripe
import json
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from User_Management.models import CartItem, Receipt, ReceiptItem, Purchase, CustomUser
from Stock_Management.models import Product, StockTransaction
from appointments.models import Appointment
from .models import Payment, AppointmentReceipt
from django.db import transaction

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)
    
    # Handle the event
    if event.type == 'checkout.session.completed':
        session = event.data.object
        
        # Process the payment
        handle_successful_payment(session)
    
    return HttpResponse(status=200)

def handle_successful_payment(session):
    """
    Process a successful payment from Stripe webhook
    """
    # Get customer and payment type from session metadata
    customer_id = session.metadata.get('customer_id')
    payment_type = session.metadata.get('payment_type')
    
    try:
        customer = CustomUser.objects.get(id=customer_id)
        
        if payment_type == 'product':
            process_product_payment(customer, session)
        elif payment_type == 'appointment':
            appointment_id = session.metadata.get('appointment_id')
            if appointment_id:
                appointment = Appointment.objects.get(id=appointment_id)
                process_appointment_payment(customer, appointment, session)
    except CustomUser.DoesNotExist:
        # Log error: Customer not found
        pass
    except Appointment.DoesNotExist:
        # Log error: Appointment not found
        pass
    except Exception as e:
        # Log general error
        pass

@transaction.atomic
def process_product_payment(customer, session):
    """
    Process product payment after successful Stripe payment
    """
    cart_items = CartItem.objects.filter(customer=customer)
    if not cart_items:
        return
    
    total = sum(item.total_price() for item in cart_items)
    
    # Create receipt
    receipt = Receipt.objects.create(
        customer=customer,
        total=total
    )
    
    # Process each cart item
    for item in cart_items:
        ReceiptItem.objects.create(
            receipt=receipt,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )
        
        # Create a stock transaction to record the sale
        StockTransaction.objects.create(
            product=item.product,
            transaction_type='sale',
            quantity=item.quantity,
            unit_price=item.product.price,
            total_amount=item.quantity * item.product.price,
            reference_number=f"SALE-{receipt.id}",
            notes=f"Sale to {customer.username}",
            created_by=customer
        )
        
        # Update product stock
        item.product.current_stock -= item.quantity
        item.product.save()
        
        # Create purchase record
        Purchase.objects.create(
            customer=customer,
            product=item.product,
            quantity=item.quantity,
            total_price=item.total_price()
        )
    
    # Create payment record
    Payment.objects.create(
        customer=customer,
        payment_type='product',
        total=total,
        stripe_payment_id=session.payment_intent
    )
    
    # Clear the cart
    cart_items.delete()

@transaction.atomic
def process_appointment_payment(customer, appointment, session):
    """
    Process appointment payment after successful Stripe payment
    """
    # Create appointment receipt
    receipt = AppointmentReceipt.objects.create(
        customer=customer,
        appointment=appointment,
        total_amount=appointment.service.price,
        payment_method='Card'
    )
    
    # Create payment record
    Payment.objects.create(
        customer=customer,
        payment_type='appointment',
        total=appointment.service.price,
        stripe_payment_id=session.payment_intent,
        appointment=appointment
    )
    
    # Update appointment status
    appointment.status = 'confirmed'
    appointment.save()