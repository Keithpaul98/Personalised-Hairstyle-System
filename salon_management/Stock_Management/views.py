from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, Q
from django.utils import timezone
from django.http import JsonResponse
from .models import Product, ProductCategory, StockTransaction, Supplier, PurchaseOrder, PurchaseOrderItem
from .forms import ProductForm, CategoryForm, StockTransactionForm, SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet
from django.template.defaulttags import register

@register.filter
def sub(value, arg):
    return value - arg

@register.filter 
def mul(value, arg):
    return value * arg

@register.filter
def div(value, arg):
    return value / arg

@register.filter
def index(sequence, position):
    return sequence[position]

@login_required
def dashboard(request):
    """Display stock management dashboard with key metrics"""
    # Get counts and summaries
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(current_stock__lte=F('minimum_stock'), is_active=True)
    low_stock_count = low_stock_products.count()
    out_of_stock = Product.objects.filter(current_stock=0, is_active=True).count()
    
    # Get recent transactions
    recent_transactions = StockTransaction.objects.order_by('-transaction_date')[:10]
    
    # Get pending purchase orders
    pending_orders = PurchaseOrder.objects.filter(status__in=['ordered', 'partial']).order_by('expected_delivery_date')[:5]
    
    # Calculate inventory value
    inventory_value = Product.objects.filter(is_active=True).aggregate(
        total=Sum(F('current_stock') * F('cost_price'))
    )['total'] or 0
    
    # Get today's sales data
    today = timezone.now().date()
    todays_sales = StockTransaction.objects.filter(
        transaction_type='sale',
        transaction_date__date=today
    ).aggregate(
        count=Sum('quantity'),
        value=Sum('total_amount')
    )
    todays_sales_count = todays_sales['count'] or 0
    todays_sales_value = todays_sales['value'] or 0
    
    # Get this week's sales data
    week_start = today - timezone.timedelta(days=today.weekday())
    weekly_sales = StockTransaction.objects.filter(
        transaction_type='sale',
        transaction_date__date__gte=week_start,
        transaction_date__date__lte=today
    ).aggregate(
        count=Sum('quantity'),
        value=Sum('total_amount')
    )
    weekly_sales_count = weekly_sales['count'] or 0
    weekly_sales_value = weekly_sales['value'] or 0
    
    # Get top selling products this month
    month_start = today.replace(day=1)
    top_selling_products = StockTransaction.objects.filter(
        transaction_type='sale',
        transaction_date__date__gte=month_start
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_value=Sum('total_amount')
    ).order_by('-total_quantity')[:5]
    
    # Get product stock data for chart (top 10 products by stock)
    product_stock_data = Product.objects.filter(
        is_active=True, 
        current_stock__gt=0
    ).order_by('-current_stock')[:10]
    
    product_stock_labels = [product.name for product in product_stock_data]
    product_stock_values = [product.current_stock for product in product_stock_data]
    
    # Convert chart data to JSON
    import json
    product_stock_data_json = json.dumps({
        'labels': product_stock_labels,
        'values': product_stock_values
    })
    
    # Get sales data by product for the last 30 days
    thirty_days_ago = today - timezone.timedelta(days=30)
    sales_by_product = StockTransaction.objects.filter(
        transaction_type='sale',
        transaction_date__date__gte=thirty_days_ago
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_value=Sum('total_amount')
    ).order_by('-total_quantity')[:10]
    
    sales_product_labels = [item['product__name'] for item in sales_by_product]
    sales_quantity_values = [item['total_quantity'] for item in sales_by_product]
    sales_value_values = [float(item['total_value']) for item in sales_by_product]
    
    # Convert chart data to JSON
    product_sales_data_json = json.dumps({
        'labels': sales_product_labels,
        'values': sales_quantity_values
    })
    
    # Create sample data for inventory trend charts
    # In a real implementation, you would query this from your database
    inventory_trends = [
        {'month': 'Jan', 'value': 15000},
        {'month': 'Feb', 'value': 17500},
        {'month': 'Mar', 'value': 16800},
        {'month': 'Apr', 'value': 18200},
        {'month': 'May', 'value': 19500},
        {'month': 'Jun', 'value': 22000},
        {'month': 'Jul', 'value': 24000},
        {'month': 'Aug', 'value': 25500},
        {'month': 'Sep', 'value': 27000},
        {'month': 'Oct', 'value': 28500},
        {'month': 'Nov', 'value': 30000},
        {'month': 'Dec', 'value': 32000}
    ]
    
    inventory_trends_json = json.dumps({
        'labels': [item['month'] for item in inventory_trends],
        'values': [item['value'] for item in inventory_trends]
    })
    
    # Sample quarterly data
    inventory_quarterly = [
        {'quarter': 'Q1', 'value': 16500},
        {'quarter': 'Q2', 'value': 19900},
        {'quarter': 'Q3', 'value': 25500},
        {'quarter': 'Q4', 'value': 30000}
    ]
    
    inventory_quarterly_json = json.dumps({
        'labels': [item['quarter'] for item in inventory_quarterly],
        'values': [item['value'] for item in inventory_quarterly]
    })
    
    # Sample category distribution data
    category_values = [
        {'category': 'Hair Care', 'value': 12500},
        {'category': 'Skin Care', 'value': 9800},
        {'category': 'Makeup', 'value': 7500},
        {'category': 'Nail Care', 'value': 5200},
        {'category': 'Fragrances', 'value': 4300},
        {'category': 'Other', 'value': 2700}
    ]
    
    category_values_json = json.dumps({
        'labels': [item['category'] for item in category_values],
        'values': [item['value'] for item in category_values]
    })
    
    # Sample monthly usage data
    monthly_usage = [
        {'month': 'Jan', 'total': 120},
        {'month': 'Feb', 'total': 145},
        {'month': 'Mar', 'total': 132},
        {'month': 'Apr', 'total': 165},
        {'month': 'May', 'total': 178},
        {'month': 'Jun', 'total': 195},
        {'month': 'Jul', 'total': 210},
        {'month': 'Aug', 'total': 230},
        {'month': 'Sep', 'total': 245},
        {'month': 'Oct', 'total': 260},
        {'month': 'Nov', 'total': 275},
        {'month': 'Dec', 'total': 290}
    ]
    
    monthly_usage_json = json.dumps({
        'labels': [item['month'] for item in monthly_usage],
        'values': [item['total'] for item in monthly_usage]
    })
    
    # Sample usage comparison data
    monthly_comparison = [
        {'month': 'Jan', 'retail': 80, 'salon': 40},
        {'month': 'Feb', 'retail': 95, 'salon': 50},
        {'month': 'Mar', 'retail': 85, 'salon': 47},
        {'month': 'Apr', 'retail': 110, 'salon': 55},
        {'month': 'May', 'retail': 120, 'salon': 58},
        {'month': 'Jun', 'retail': 130, 'salon': 65},
        {'month': 'Jul', 'retail': 140, 'salon': 70},
        {'month': 'Aug', 'retail': 155, 'salon': 75},
        {'month': 'Sep', 'retail': 165, 'salon': 80},
        {'month': 'Oct', 'retail': 175, 'salon': 85},
        {'month': 'Nov', 'retail': 185, 'salon': 90},
        {'month': 'Dec', 'retail': 195, 'salon': 95}
    ]
    
    monthly_comparison_json = json.dumps({
        'labels': [item['month'] for item in monthly_comparison],
        'retail': [item['retail'] for item in monthly_comparison],
        'salon': [item['salon'] for item in monthly_comparison]
    })
    
    context = {
        'total_products': total_products,
        'active_products': active_products,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_count,
        'out_of_stock': out_of_stock,
        'recent_transactions': recent_transactions,
        'pending_orders': pending_orders,
        'inventory_value': inventory_value,
        'todays_sales_count': todays_sales_count,
        'todays_sales_value': todays_sales_value,
        'weekly_sales_count': weekly_sales_count,
        'weekly_sales_value': weekly_sales_value,
        'top_selling_products': top_selling_products,
        'product_stock_labels': product_stock_labels,
        'product_stock_values': product_stock_values,
        'product_stock_data_json': product_stock_data_json,
        'sales_product_labels': sales_product_labels,
        'sales_quantity_values': sales_quantity_values,
        'sales_value_values': sales_value_values,
        'product_sales_data_json': product_sales_data_json,
        'inventory_trends': inventory_trends,
        'inventory_quarterly': inventory_quarterly,
        'inventory_trends_json': inventory_trends_json,
        'inventory_quarterly_json': inventory_quarterly_json,
        'category_values': category_values,
        'category_values_json': category_values_json,
        'monthly_usage': monthly_usage,
        'monthly_usage_json': monthly_usage_json,
        'monthly_comparison': monthly_comparison,
        'monthly_comparison_json': monthly_comparison_json,
        'page_title': 'Stock Management Dashboard',
        'last_updated': timezone.now(),
        'today': today
    }
    
    return render(request, 'Stock_Management/dashboard.html', context)

@login_required
def product_list(request):
    """Display list of all products"""
    categories = ProductCategory.objects.all()
    
    # Filter products based on query parameters
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    products = Product.objects.all()
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if status:
        if status == 'active':
            products = products.filter(is_active=True)
        elif status == 'inactive':
            products = products.filter(is_active=False)
        elif status == 'low_stock':
            products = products.filter(current_stock__lte=F('minimum_stock'), is_active=True)
        elif status == 'out_of_stock':
            products = products.filter(current_stock=0, is_active=True)
    
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) | 
            Q(barcode__icontains=search)
        )
    
    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_id,
        'selected_status': status,
        'search_query': search,
        'page_title': 'Product Inventory'
    }
    
    return render(request, 'Stock_Management/product_list.html', context)

@login_required
def product_detail(request, product_id):
    """Display details of a specific product"""
    product = get_object_or_404(Product, id=product_id)
    transactions = product.transactions.order_by('-transaction_date')[:20]
    
    context = {
        'product': product,
        'transactions': transactions,
        'page_title': product.name
    }
    
    return render(request, 'Stock_Management/product_detail.html', context)

@login_required
def add_product(request):
    """Add a new product to inventory"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            
            # Create initial stock transaction if stock is provided
            initial_stock = form.cleaned_data.get('initial_stock')
            if initial_stock and initial_stock > 0:
                StockTransaction.objects.create(
                    product=product,
                    transaction_type='purchase',
                    quantity=initial_stock,
                    unit_price=product.cost_price,
                    total_amount=initial_stock * product.cost_price,
                    notes="Initial stock",
                    created_by=request.user
                )
            
            messages.success(request, f"Product '{product.name}' added successfully")
            return redirect('Stock_Management:product_detail', product_id=product.id)
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Product'
    }
    
    return render(request, 'Stock_Management/product_form.html', context)

@login_required
def edit_product(request, product_id):
    """Edit an existing product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully")
            return redirect('Stock_Management:product_detail', product_id=product.id)
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'page_title': f'Edit {product.name}'
    }
    
    return render(request, 'Stock_Management/product_form.html', context)

@login_required
def add_transaction(request, product_id=None):
    """Add a stock transaction"""
    product = None
    if product_id:
        product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = StockTransactionForm(request.POST, product=product)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            
            try:
                transaction.save()
                messages.success(request, "Stock transaction recorded successfully")
                
                if product_id:
                    return redirect('Stock_Management:product_detail', product_id=product_id)
                return redirect('Stock_Management:transaction_list')
            except ValueError as e:
                messages.error(request, str(e))
    else:
        initial = {}
        if product:
            initial['product'] = product
            initial['unit_price'] = product.cost_price
        
        form = StockTransactionForm(initial=initial, product=product)
    
    # Convert product data to JSON for use in template
    import json
    
    product_data = None
    if product:
        product_data = {
            'id': product.id,
            'name': product.name,
            'current_stock': product.current_stock,
            'cost_price': float(product.cost_price) if product.cost_price else 0,
            'retail_price': float(product.retail_price) if product.retail_price else 0
        }
    
    form_data = {
        'quantity_id': form['quantity'].id_for_label,
        'unit_price_id': form['unit_price'].id_for_label,
        'transaction_type_id': form['transaction_type'].id_for_label
    }
    
    context = {
        'form': form,
        'product': product,
        'product_data_json': json.dumps(product_data) if product_data else 'null',
        'form_data_json': json.dumps(form_data),
        'page_title': 'Record Stock Transaction'
    }
    
    return render(request, 'Stock_Management/transaction_form.html', context)

@login_required
def transaction_list(request):
    """Display list of all stock transactions"""
    transactions = StockTransaction.objects.all().order_by('-transaction_date')
    
    # Filter by transaction type
    transaction_type = request.GET.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Filter by product
    product_id = request.GET.get('product')
    if product_id:
        transactions = transactions.filter(product_id=product_id)
    
    # Filter by date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        try:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__date__gte=start_date_obj)
        except ValueError:
            messages.error(request, "Invalid start date format. Please use YYYY-MM-DD.")
    
    if end_date:
        try:
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            transactions = transactions.filter(transaction_date__date__lte=end_date_obj)
        except ValueError:
            messages.error(request, "Invalid end date format. Please use YYYY-MM-DD.")
    
    # Get all products for filter dropdown
    products = Product.objects.filter(is_active=True).order_by('name')
    
    # Calculate totals for filtered transactions
    totals = transactions.aggregate(
        total_quantity=Sum('quantity'),
        total_amount=Sum('total_amount')
    )
    
    context = {
        'transactions': transactions,
        'transaction_types': StockTransaction.TRANSACTION_TYPES,
        'products': products,
        'selected_type': transaction_type,
        'selected_product': product_id,
        'start_date': start_date,
        'end_date': end_date,
        'total_quantity': totals['total_quantity'] or 0,
        'total_amount': totals['total_amount'] or 0,
        'page_title': 'Stock Transactions'
    }
    
    return render(request, 'Stock_Management/transaction_list.html', context)

@login_required
def category_list(request):
    """Display list of product categories"""
    categories = ProductCategory.objects.all()
    
    context = {
        'categories': categories,
        'page_title': 'Product Categories'
    }
    
    return render(request, 'Stock_Management/category_list.html', context)

@login_required
def add_category(request):
    """Add a new product category"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' added successfully")
            return redirect('Stock_Management:category_list')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Category'
    }
    
    return render(request, 'Stock_Management/category_form.html', context)

@login_required
def edit_category(request, category_id):
    """Edit an existing category"""
    category = get_object_or_404(ProductCategory, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully")
            return redirect('Stock_Management:category_list')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'page_title': f'Edit {category.name}'
    }
    
    return render(request, 'Stock_Management/category_form.html', context)

@login_required
def supplier_list(request):
    """Display a list of suppliers with filtering options"""
    suppliers = Supplier.objects.all()
    all_products = Product.objects.filter(is_active=True).order_by('name')
    
    # Apply filters
    name_filter = request.GET.get('name')
    product_filter = request.GET.get('product')
    status_filter = request.GET.get('status')
    
    if name_filter:
        suppliers = suppliers.filter(name__icontains=name_filter)
    
    if product_filter:
        suppliers = suppliers.filter(products__id=product_filter).distinct()
    
    if status_filter:
        if status_filter == 'active':
            suppliers = suppliers.filter(is_active=True)
        elif status_filter == 'inactive':
            suppliers = suppliers.filter(is_active=False)
    
    context = {
        'suppliers': suppliers,
        'all_products': all_products,
        'page_title': 'Suppliers'
    }
    
    return render(request, 'Stock_Management/supplier_list.html', context)

@login_required
def supplier_detail(request, supplier_id):
    """Display detailed information about a supplier"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    # Get products supplied by this supplier
    products = supplier.products.all()
    
    # Get purchase orders for this supplier
    purchase_orders = PurchaseOrder.objects.filter(supplier=supplier).order_by('-order_date')
    
    context = {
        'supplier': supplier,
        'products': products,
        'purchase_orders': purchase_orders,
        'page_title': supplier.name
    }
    
    return render(request, 'Stock_Management/supplier_detail.html', context)

@login_required
def add_supplier(request):
    """Add a new supplier"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier '{supplier.name}' added successfully")
            return redirect('Stock_Management:supplier_detail', supplier_id=supplier.id)
    else:
        form = SupplierForm()
    
    context = {
        'form': form,
        'page_title': 'Add New Supplier'
    }
    
    return render(request, 'Stock_Management/supplier_form.html', context)

@login_required
def edit_supplier(request, supplier_id):
    """Edit an existing supplier"""
    supplier = get_object_or_404(Supplier, id=supplier_id)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{supplier.name}' updated successfully")
            return redirect('Stock_Management:supplier_detail', supplier_id=supplier.id)
    else:
        form = SupplierForm(instance=supplier)
    
    context = {
        'form': form,
        'supplier': supplier,
        'page_title': f'Edit {supplier.name}'
    }
    
    return render(request, 'Stock_Management/supplier_form.html', context)

@login_required
def purchase_order_list(request):
    """Display list of purchase orders"""
    purchase_orders = PurchaseOrder.objects.all().order_by('-order_date')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        purchase_orders = purchase_orders.filter(status=status)
    
    context = {
        'purchase_orders': purchase_orders,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
        'selected_status': status,
        'page_title': 'Purchase Orders'
    }
    
    return render(request, 'Stock_Management/purchase_order_list.html', context)

@login_required
def purchase_order_detail(request, po_id):
    """Display details of a specific purchase order"""
    purchase_order = get_object_or_404(PurchaseOrder, id=po_id)
    
    context = {
        'purchase_order': purchase_order,
        'page_title': f'Purchase Order #{purchase_order.id}'
    }
    
    return render(request, 'Stock_Management/purchase_order_detail.html', context)

@login_required
def create_purchase_order(request, supplier_id=None):
    """Create a new purchase order"""
    supplier = None
    if supplier_id:
        supplier = get_object_or_404(Supplier, id=supplier_id)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        
        if form.is_valid():
            purchase_order = form.save(commit=False)
            purchase_order.created_by = request.user
            if supplier:
                purchase_order.supplier = supplier
            purchase_order.save()
            
            formset = PurchaseOrderItemFormSet(request.POST, instance=purchase_order)
            if formset.is_valid():
                formset.save()
                purchase_order.update_total()
                messages.success(request, "Purchase order created successfully")
                return redirect('Stock_Management:purchase_order_detail', po_id=purchase_order.id)
            else:
                # If formset is invalid, we need to delete the purchase order to avoid orphaned records
                purchase_order.delete()
                messages.error(request, "There was an error with the order items. Please check and try again.")
        else:
            messages.error(request, "There was an error with the order information. Please check and try again.")
    else:
        initial_data = {}
        if supplier:
            initial_data['supplier'] = supplier.id
            
        form = PurchaseOrderForm(initial=initial_data)
        formset = PurchaseOrderItemFormSet()
    
    # Convert form data to JSON for use in template
    import json
    
    form_data = {
        'formset_prefix': formset.prefix,
        'formset_total_forms': formset.total_form_count()
    }
    
    context = {
        'form': form,
        'formset': formset,
        'supplier': supplier,
        'form_data_json': json.dumps(form_data),
        'page_title': 'Create Purchase Order'
    }
    
    return render(request, 'Stock_Management/purchase_order_form.html', context)

@login_required
def edit_purchase_order(request, po_id):
    """Edit an existing purchase order"""
    purchase_order = get_object_or_404(PurchaseOrder, id=po_id)
    
    if purchase_order.status not in ['draft', 'ordered']:
        messages.error(request, "Cannot edit purchase order that has been received or cancelled")
        return redirect('Stock_Management:purchase_order_detail', po_id=po_id)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=purchase_order)
        formset = PurchaseOrderItemFormSet(request.POST, instance=purchase_order)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            purchase_order.update_total()
            messages.success(request, "Purchase order updated successfully")
            return redirect('Stock_Management:purchase_order_detail', po_id=purchase_order.id)
        else:
            messages.error(request, "There was an error with the order information or items. Please check and try again.")
    else:
        form = PurchaseOrderForm(instance=purchase_order)
        formset = PurchaseOrderItemFormSet(instance=purchase_order)
    
    context = {
        'form': form,
        'formset': formset,
        'purchase_order': purchase_order,
        'page_title': f'Edit Purchase Order #{purchase_order.id}'
    }
    
    return render(request, 'Stock_Management/purchase_order_form.html', context)

@login_required
def receive_purchase_order(request, po_id):
    """Mark items in a purchase order as received"""
    purchase_order = get_object_or_404(PurchaseOrder, id=po_id)
    
    if purchase_order.status in ['received', 'cancelled']:
        messages.error(request, "Cannot receive items for a completed or cancelled order")
        return redirect('Stock_Management:purchase_order_detail', po_id=po_id)
    
    if request.method == 'POST':
        # Process received items
        items_received = False
        all_received = True
        
        for item in purchase_order.items.all():
            qty_key = f'received_{item.id}'
            if qty_key in request.POST:
                qty_received = int(request.POST.get(qty_key, 0))
                
                if qty_received > 0:
                    # Calculate remaining quantity to receive
                    remaining = item.quantity_ordered - item.quantity_received
                    
                    if qty_received > remaining:
                        qty_received = remaining
                    
                    if qty_received > 0:
                        # Update received quantity
                        item.quantity_received += qty_received
                        item.save()
                        
                        # Create stock transaction
                        StockTransaction.objects.create(
                            product=item.product,
                            transaction_type='purchase',
                            quantity=qty_received,
                            unit_price=item.unit_price,
                            total_amount=qty_received * item.unit_price,
                            reference_number=f"PO-{purchase_order.id}",
                            notes=f"Received from PO #{purchase_order.id}",
                            created_by=request.user
                        )
                        
                        items_received = True
                
                # Check if all items are fully received
                if item.quantity_received < item.quantity_ordered:
                    all_received = False
        
        if items_received:
            # Update purchase order status
            if all_received:
                purchase_order.status = 'received'
            else:
                purchase_order.status = 'partial'
            
            purchase_order.save()
            messages.success(request, "Items received successfully")
        
        return redirect('Stock_Management:purchase_order_detail', po_id=po_id)
    
    context = {
        'purchase_order': purchase_order,
        'page_title': f'Receive Items - PO #{purchase_order.id}'
    }
    
    return render(request, 'Stock_Management/receive_items.html', context)

@login_required
def low_stock_report(request):
    """Display report of products with low stock"""
    low_stock_products = Product.objects.filter(
        current_stock__lte=F('minimum_stock'),
        is_active=True
    ).order_by('current_stock')
    
    context = {
        'products': low_stock_products,
        'page_title': 'Low Stock Report'
    }
    
    return render(request, 'Stock_Management/low_stock_report.html', context)

@login_required
def inventory_value_report(request):
    """Display report of inventory value"""
    products = Product.objects.filter(is_active=True).order_by('category__name', 'name')
    
    # Calculate total inventory value
    total_value = sum(product.current_stock * product.cost_price for product in products)
    potential_retail_value = sum(product.current_stock * product.retail_price for product in products)
    potential_profit = potential_retail_value - total_value
    
    # Group by category
    categories = ProductCategory.objects.all()
    category_breakdown = []
    
    for category in categories:
        category_products = products.filter(category=category)
        category_value = sum(product.current_stock * product.cost_price for product in category_products)
        if total_value > 0:
            category_breakdown.append({
                'name': category.name,
                'inventory_value': category_value,
                'percentage': (category_value / total_value * 100) if total_value > 0 else 0
            })
    
    # Usage type breakdown
    salon_only_products = products.filter(usage_type='salon')
    retail_only_products = products.filter(usage_type='retail')
    both_products = products.filter(usage_type='both')
    
    salon_value = sum(p.current_stock * p.cost_price for p in salon_only_products)
    retail_value = sum(p.current_stock * p.cost_price for p in retail_only_products)
    both_value = sum(p.current_stock * p.cost_price for p in both_products)
    
    # Convert data to JSON for charts
    import json
    
    category_chart_data = {
        'labels': [item['name'] for item in category_breakdown],
        'values': [item['inventory_value'] for item in category_breakdown]
    }
    
    usage_type_data = {
        'labels': ['Salon Use Only', 'Retail Only', 'Both'],
        'values': [salon_value, retail_value, both_value]
    }
    
    context = {
        'products': products,
        'total_inventory_value': total_value,
        'potential_retail_value': potential_retail_value,
        'potential_profit': potential_profit,
        'category_breakdown': category_breakdown,
        'salon_value': salon_value,
        'retail_value': retail_value,
        'both_value': both_value,
        'category_chart_data_json': json.dumps(category_chart_data),
        'usage_type_data_json': json.dumps(usage_type_data),
        'page_title': 'Inventory Value Report'
    }
    
    return render(request, 'Stock_Management/inventory_value_report.html', context)

@login_required
def product_usage_report(request):
    """Display report of product usage in the salon"""
    start_date = request.GET.get('start_date', (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', timezone.now().strftime('%Y-%m-%d'))
    
    # Get salon usage transactions
    transactions = StockTransaction.objects.filter(
        transaction_type='salon_usage',
        transaction_date__gte=start_date,
        transaction_date__lte=end_date
    ).order_by('-transaction_date')
    
    # Aggregate by product
    product_usage = {}
    for transaction in transactions:
        product_id = transaction.product.id
        if product_id not in product_usage:
            product_usage[product_id] = {
                'product': transaction.product,
                'quantity': 0,
                'cost': 0
            }
        
        product_usage[product_id]['quantity'] += transaction.quantity
        product_usage[product_id]['cost'] += transaction.total_amount
    
    context = {
        'product_usage': product_usage.values(),
        'transactions': transactions,
        'start_date': start_date,
        'end_date': end_date,
        'page_title': 'Salon Product Usage Report'
    }
    
    return render(request, 'Stock_Management/product_usage_report.html', context)

def check_low_stock_and_notify():
    """
    Check for products with low stock and send notifications to admin users
    This function should be called whenever stock levels change
    """
    from notifications.utils import notify_low_stock
    from User_Management.models import CustomUser
    from .models import Product
    
    # Get all products with low stock
    low_stock_products = Product.objects.filter(
        current_stock__lte=models.F('minimum_stock'),
        is_active=True
    )
    
    if low_stock_products.exists():
        # Get all admin users
        admin_users = CustomUser.objects.filter(role='admin')
        
        # Use the centralized notification system
        for product in low_stock_products:
            notify_low_stock(product, admin_users)
            print(f"Low stock notification created for {product.name}")
    
    return low_stock_products.count()

@login_required
def check_stock(request):
    """AJAX endpoint to check current stock of a product"""
    if request.method == 'GET' and request.is_ajax():
        product_id = request.GET.get('product_id')
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                return JsonResponse({
                    'success': True,
                    'current_stock': product.current_stock,
                    'is_low_stock': product.is_low_stock(),
                    'stock_status': product.stock_status()
                })
            except Product.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Product not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})