from django.urls import path
from . import views

app_name = 'Stock_Management'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Product management
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    
    # Stock transactions
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
    path('products/<int:product_id>/add-transaction/', views.add_transaction, name='add_product_transaction'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    
    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/<int:supplier_id>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:supplier_id>/edit/', views.edit_supplier, name='edit_supplier'),
    
    # Purchase orders
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', views.create_purchase_order, name='create_purchase_order'),
    path('purchase-orders/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:po_id>/edit/', views.edit_purchase_order, name='edit_purchase_order'),
    path('purchase-orders/<int:po_id>/receive/', views.receive_purchase_order, name='receive_purchase_order'),
    
    # Reports
    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
    path('reports/inventory-value/', views.inventory_value_report, name='inventory_value_report'),
    path('reports/product-usage/', views.product_usage_report, name='product_usage_report'),
    
    # AJAX endpoints
    path('ajax/check-stock/', views.check_stock, name='check_stock'),
]