import stripe
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from User_Management.models import CartItem, Receipt, ReceiptItem
from django.contrib.auth.decorators import login_required
from django.db import transaction


stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(customer=request.user)
    total = sum(item.total_price() for item in cart_items)
    
    if request.method == 'POST':
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                       'price_data': {
                           'currency': 'usd',
                           'unit_amount': int(item.product.price * 100), # Amount in cents
                           'product_data': { 
                               'name': item.product.name, 
                           } ,
                        }, 
                        'quantity': item.quantity, 
                    } for item in cart_items
                ],
                mode='payment',
                success_url=request.build_absolute_uri(reverse('payment_success')),
                cancel_url=request.build_absolute_uri(reverse('payment_cancelled')),
            )
            return redirect(session.url)
        except stripe.error.StripeError as e: 
            messages.error(request, f'Error: {str(e)}') 
            return redirect('checkout')
        
    return render(request, 'payments/checkout.html', {'cart_items': cart_items, 'total': total, 'stripe_publishable_key': settings.STRIPE_PUBLIC_KEY})

@login_required
def payment_success(request):
    cart_items = CartItem.objects.filter(customer=request.user)
    total = sum(item.total_price() for item in cart_items)

    with transaction.atomic():
        receipt = Receipt.objects.create(customer=request.user, total=total)
        for item in cart_items:
            ReceiptItem.objects.create(
                receipt=receipt,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            item.product.stock -= item.quantity
            item.product.save()
        cart_items.delete()

    messages.success(request, 'Payment successful. Your receipt is available in your profile.')
    return redirect('customer_products')

def payment_cancelled(request):
    messages.error(request, 'Payment was cancelled.')
    return redirect('view_cart')
