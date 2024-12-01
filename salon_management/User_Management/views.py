from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerRegistrationForm, AdminRegistrationForm, CustomLoginForm, ProductForm, StaffForm
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, CustomUser, Receipt, CartItem
from django.http import HttpResponse
import pdfkit
from django.template.loader import get_template

# Create your views here.


def home(request):
    return render(request, 'home.html')


def customer_registration(request):
    form = CustomerRegistrationForm()
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('custom_login')
    return render(request, 'user_management/customer_registration.html', {'form': form})

def custom_login(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome {username}')
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                else: 
                    return redirect('customer_products')
            else:
                messages.error(request, 'Invalid username or password')
        else: 
            messages.error(request, 'error in form submisiion.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomLoginForm()
    return render(request, 'user_management/login.html', {'form': form})
    
         
def custom_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('custom_login')

def admin_registration(request):
    if request.method == 'POST':
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            admin = form.save(commit=False)
            admin.role = 'admin'
            admin.save()
            messages.success(request, 'Admin created successfully')
            return redirect('custom_login')
    else:
        form = AdminRegistrationForm()
    return render(request, 'user_management/admin_registration.html', {'form': form})

def customer_products(request): 
    products = Product.objects.all() 
    return render(request, 'user_management/customer_products.html', {'products': products})

def admin_dashboard(request): 
    if request.method == 'POST':
        if 'add_product' in request.POST:
             form = ProductForm(request.POST)
             if form.is_valid():
                form.save()
                messages.success(request, 'Product added successfully!')
                return redirect('admin_dashboard')
             else:
                messages.error(request, 'Error adding product.')
        elif 'add_staff in request.POST':
            staff_form = StaffForm(request.POST)
            if staff_form.is_valid():
                staff = staff_form.save(commit=False)
                staff.role = 'staff'
                staff.save()
                messages.success(request, 'Staff added successfully!')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Error adding staff.')
    else:
        form = ProductForm() 
        staff_form = StaffForm()

    products = Product.objects.all()
    customers = CustomUser.objects.filter(role='customer')
    
    product_names = [product.name for product in products]
    product_stocks = [product.stock for product in products]
    
    context = { 
        'form': form, 
        'products': products, 
        'staff_form': staff_form,
        'customers': customers,
        'product_names': product_names, 
        'product_stocks': product_stocks, 
    }
    
    return render(request, 'user_management/admin_dashboard.html', context)

@receiver(post_save, sender=Product)
def check_stock(sender, instance, **kwargs):
    if instance.stock <= instance.stock * 0.5:
        # Send email or notification to the manager
        pass

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity'))
    
    cart_item, created = CartItem.objects.get_or_create(customer=request.user, product=product)
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()
    
    messages.success(request, f'{product.name} added to cart.')
    return redirect('customer_products')

@login_required
def view_cart(request):
    cart_items = CartItem.objects.filter(customer=request.user)
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'user_management/cart.html', {'cart_items': cart_items, 'total':total})

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, customer=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('view_cart')

@login_required
def profile(request): 
    receipts = Receipt.objects.filter(customer=request.user) 
    return render(request, 'user_management/profile.html', {'receipts': receipts})
#download and view receipts
def download_receipt(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id, customer=request.user)
    template = get_template('User_Management/receipt_pdf.html')
    html = template.render({'receipt': receipt})

    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    pdf = pdfkit.from_string(html, False, configuration=config)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{receipt.id}.pdf"'
    return response

@login_required
def view_receipts(request):
    receipts = Receipt.objects.filter(customer=request.user)
    return render(request, 'user_management/receipts.html', {'receipts': receipts})