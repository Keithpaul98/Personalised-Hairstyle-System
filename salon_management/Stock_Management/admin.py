from django.contrib import admin
from .models import (
    ProductCategory, 
    Product, 
    StockTransaction, 
    Supplier, 
    PurchaseOrder, 
    PurchaseOrderItem
)

class StockTransactionInline(admin.TabularInline):
    model = StockTransaction
    extra = 0
    readonly_fields = ['transaction_date', 'created_by']
    fields = ['transaction_type', 'quantity', 'unit_price', 'total_amount', 'transaction_date', 'created_by', 'notes']
    can_delete = False

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ['product', 'quantity_ordered', 'quantity_received', 'unit_price', 'total_price']

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'current_stock', 'stock_status', 'is_active']
    list_filter = ['category', 'is_active', 'usage_type']
    search_fields = ['name', 'description', 'barcode']
    readonly_fields = ['current_stock', 'created_at', 'updated_at']
    fieldsets = [
        (None, {'fields': ['name', 'category', 'description']}),
        ('Pricing', {'fields': ['price', 'cost_price']}),
        ('Stock Information', {'fields': ['current_stock', 'minimum_stock']}),
        ('Product Details', {'fields': ['image', 'barcode', 'usage_type', 'is_active']}),
        ('Timestamps', {'fields': ['created_at', 'updated_at'], 'classes': ['collapse']}),
    ]
    inlines = [StockTransactionInline]

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'transaction_type', 'quantity', 'unit_price', 'total_amount', 'transaction_date', 'created_by']
    list_filter = ['transaction_type', 'transaction_date', 'created_by']
    search_fields = ['product__name', 'reference_number', 'notes']
    readonly_fields = ['transaction_date', 'created_by']
    date_hierarchy = 'transaction_date'

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'contact_person', 'email', 'phone']
    filter_horizontal = ['products']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier', 'order_date', 'expected_delivery_date', 'status', 'total_amount', 'created_by']
    list_filter = ['status', 'order_date', 'supplier']
    search_fields = ['supplier__name', 'notes']
    readonly_fields = ['created_by', 'total_amount']
    date_hierarchy = 'order_date'
    inlines = [PurchaseOrderItemInline]
