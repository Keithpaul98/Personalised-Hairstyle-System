import stripe
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from User_Management.models import CartItem, Receipt, ReceiptItem, Purchase, CustomUser
from Stock_Management.models import Product, StockTransaction
from appointments.models import Appointment
from .models import Payment, AppointmentReceipt
from django.template.loader import get_template
from django.http import HttpResponse
import pdfkit
from datetime import timedelta

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(customer=request.user)
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('User_Management:view_cart')
    
    total = sum(item.total_price() for item in cart_items)
    
    if request.method == 'POST':
        try:
            # Create Stripe checkout session
            line_items = [{
                'price_data': {
                    'currency': 'mwk',
                    'unit_amount': int(item.product.price * 100),
                    'product_data': {
                        'name': item.product.name,
                    },
                },
                'quantity': item.quantity,
            } for item in cart_items]

            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri(
                    reverse('payments:payment_success')
                ),
                cancel_url=request.build_absolute_uri(
                    reverse('payments:payment_cancelled')
                ),
                metadata={
                    'customer_id':request.user.id,
                    'payment_type':'product'
                }
            )
            return redirect(session.url)
                
        except stripe.error.StripeError as e:
            messages.error(request, f'Payment error: {str(e)}')
            return redirect('User_Management:view_cart')
        
    return render(request, 'payments/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'stripe_publishable_key': settings.STRIPE_PUBLIC_KEY
    })

@login_required
def product_payment_success(request):
    messages.success(request, 'Payment successful! Thank you for your purchase.')
    return render(request, 'payments/product_payment_success.html')

@login_required
def product_payment_cancelled(request):
    messages.warning(request, 'Payment was cancelled.')
    return redirect('User_Management:view_cart')

@login_required
def view_product_receipt(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id, customer=request.user)
    return render(request, 'payments/product_receipt.html', {
        'receipt': receipt
    })

@login_required
def payment_success(request):
    cart_items = CartItem.objects.filter(customer=request.user)
    if not cart_items:
        messages.warning(request, 'No items in cart.')
        return redirect('User_Management:view_cart')
    
    total = sum(item.total_price() for item in cart_items)

    with transaction.atomic():
        # Create receipt in User_Management
        receipt = Receipt.objects.create(
            customer=request.user,
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
                notes=f"Sale to {request.user.username}",
                created_by=request.user
            )
            
            # Update product stock - use current_stock for Stock_Management products
            item.product.current_stock -= item.quantity
            item.product.save()

            # Create purchase record
            Purchase.objects.create(
                customer=request.user,
                product=item.product,
                quantity=item.quantity,
                total_price=item.total_price()
            )

        # Add loyalty points and handle discounts
        customer = request.user
        points_earned = 10
        customer.loyalty_points += points_earned
        
        # Check for discount eligibility
        points = customer.loyalty_points
        
        discount_tiers = [
            (4000, 100, 14),
            (2000, 100, 10),
            (1000, 100, 7),
            (500, 50, 7),
            (200, 20, 7),
            (100, 10, 7),
        ]

        for threshold, discount, days in discount_tiers:
            if points >= threshold:
                customer.discount = discount
                customer.discount_expiry = timezone.now() + timedelta(days=days)
                customer.loyalty_points = max(0, points - threshold)
                messages.success(
                    request,
                    f'Payment successful! You earned {points_earned} points and a {discount}% '
                    f'discount valid for {days} days! View your receipt in the receipts section.'
                )
                break
        else:
            # No discount earned
            messages.success(
                request,
                f'Payment successful! You earned {points_earned} points! '
                f'Current balance: {customer.loyalty_points} points. '
                f'View your receipt in the receipts section.'
            )
        
        customer.save()
        cart_items.delete()

    return redirect('User_Management:view_cart')

def payment_cancelled(request):
    messages.error(request, 'Payment was cancelled.')
    return redirect('User_Management:view_cart')

@login_required
def appointment_checkout(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, customer=request.user)
    
    # Check if a receipt already exists for this appointment
    existing_receipt = AppointmentReceipt.objects.filter(appointment=appointment).first()
    if existing_receipt:
        messages.info(request, "This appointment has already been processed for payment.")
        return redirect('appointments:appointment_success', appointment_id=appointment.id)
    
    if request.method == 'POST':
        # Check if the user selected cash payment
        payment_method = request.POST.get('payment_method')
        
        if payment_method == 'cash':
            # Handle cash payment - mark appointment as confirmed
            with transaction.atomic():
                # Update appointment status to Confirmed
                appointment.status = 'Confirmed'
                appointment.save()
                
                # Create payment record for cash payment
                payment = Payment.objects.create(
                    customer=request.user,
                    payment_type='appointment',
                    payment_method='cash',
                    total=appointment.service.price,
                    stripe_payment_id='cash_payment'
                )
                
                # Generate receipt - check again inside transaction to prevent race conditions
                if not AppointmentReceipt.objects.filter(appointment=appointment).exists():
                    receipt = AppointmentReceipt.objects.create(
                        customer=request.user,
                        appointment=appointment,
                        payment_method='cash',
                        total_amount=appointment.service.price
                    )
                
                # Add loyalty points (10 points per appointment) ONLY for confirmed appointments
                customer = request.user
                points_earned = 10
                points_added, discount_message = customer.add_loyalty_points(points_earned)
                
                # NOTE: We don't call notify_stylist_of_appointment here to avoid duplicate notifications
                # The notification was already created when the appointment was initially booked
                
                success_message = "Your appointment has been confirmed with cash payment option. Please pay at the salon."
                if discount_message:
                    success_message += f" {discount_message}"
                else:
                    success_message += f" You earned {points_earned} loyalty points! Current balance: {customer.loyalty_points}"
                
                messages.success(request, success_message)
                return redirect('appointments:appointment_success', appointment_id=appointment.id)
        else:
            # Handle online payment with Stripe
            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'mwk',
                            'unit_amount': int(appointment.service.price * 100),
                            'product_data': {
                                'name': f"Appointment: {appointment.service.name}",
                            },
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.build_absolute_uri(
                        reverse('payments:appointment_payment_success', kwargs={'appointment_id': appointment.id})
                    ) + '?session_id={CHECKOUT_SESSION_ID}',
                    cancel_url=request.build_absolute_uri(
                        reverse('payments:appointment_payment_cancelled', kwargs={'appointment_id': appointment.id})
                    ),
                )
                return redirect(session.url)
            except stripe.error.StripeError as e:
                messages.error(request, f'Error: {str(e)}')
                return redirect('appointments:appointment_details', appointment_id=appointment.id)
    
    return render(request, 'payments/appointment_checkout.html', {
        'appointment': appointment,
        'stripe_publishable_key': settings.STRIPE_PUBLIC_KEY
    })

@login_required
def appointment_payment_success(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, customer=request.user)
    
    # Check if payment has already been processed
    existing_receipt = AppointmentReceipt.objects.filter(appointment=appointment).first()
    if existing_receipt:
        messages.info(request, "This appointment has already been processed for payment.")
        return redirect('payments:view_appointment_receipt', receipt_id=existing_receipt.id)
    
    # Get session ID from URL
    session_id = request.GET.get('session_id', None)
    
    if not session_id:
        messages.error(request, 'No payment session found.')
        return redirect('appointments:appointment_details', appointment_id=appointment.id)
    
    try:
        # Retrieve the session
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify payment was successful
        if session.payment_status != 'paid':
            messages.error(request, 'Payment was not successful. Please try again.')
            return redirect('appointments:appointment_details', appointment_id=appointment.id)
        
        with transaction.atomic():
            # Create payment record
            payment = Payment.objects.create(
                customer=request.user,
                payment_type='appointment',
                payment_method='card',
                total=appointment.service.price,
                stripe_payment_id=session_id
            )
            
            # Generate receipt
            receipt = AppointmentReceipt.objects.create(
                customer=request.user,
                appointment=appointment,
                payment_method='card',
                total_amount=appointment.service.price
            )
            
            # Update appointment status to Confirmed
            appointment.status = 'Confirmed'
            appointment.save()
            
            # Add loyalty points (10 points per appointment) ONLY for confirmed appointments
            customer = request.user
            points_earned = 10
            points_added, discount_message = customer.add_loyalty_points(points_earned)
            
            # NOTE: We don't call notify_stylist_of_appointment here to avoid duplicate notifications
            # The notification was already created when the appointment was initially booked
            
            # Set success message
            base_message = f'Payment successful! Your appointment has been confirmed. You earned {points_earned} loyalty points!'
            if discount_message:
                base_message += f' {discount_message}'
            else:
                base_message += f' Current points balance: {customer.loyalty_points}'
                
            messages.success(request, base_message)
    
    except stripe.error.StripeError as e:
        messages.error(request, f'Error processing payment: {str(e)}')
        return redirect('appointments:appointment_details', appointment_id=appointment.id)
        
    return redirect('payments:view_appointment_receipt', receipt_id=receipt.id)

@login_required
def view_appointment_receipt(request, receipt_id):
    receipt = get_object_or_404(AppointmentReceipt, 
                               id=receipt_id,
                               customer=request.user)
    
    context = {
        'receipt': receipt,
        'points_earned': 10,  # Fixed points per appointment
        'loyalty_points': request.user.loyalty_points,
        'discount': request.user.discount,
        'discount_expiry': request.user.discount_expiry,
    }
    
    return render(request, 'payments/appointment_receipt.html', context)

@login_required
def download_appointment_receipt(request, receipt_id):
    receipt = get_object_or_404(AppointmentReceipt, 
                               id=receipt_id,
                               customer=request.user)
    template = get_template('payments/appointment_receipt_pdf.html')
    html = template.render({'receipt': receipt})

    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    pdf = pdfkit.from_string(html, False, configuration=config)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="appointment_receipt_{receipt.id}.pdf"'
    return response

@login_required
def appointment_payment_cancelled(request, appointment_id):
    messages.error(request, 'Payment was cancelled.')
    return redirect('appointments:appointment_details', appointment_id=appointment_id)
