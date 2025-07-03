from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator
import random
import string

class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Product Categories"
    
    def __str__(self):
        return self.name

class Product(models.Model):
    USAGE_CHOICES = [
        ('salon', 'Salon Use Only'),
        ('retail', 'Retail Only'),
        ('both', 'Both Salon and Retail')
    ]
    
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost price per unit")
    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=5, help_text="Minimum stock level before alert")
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    usage_type = models.CharField(max_length=10, choices=USAGE_CHOICES, default='both')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock
    
    def stock_status(self):
        if self.current_stock <= 0:
            return "Out of Stock"
        elif self.is_low_stock():
            return "Low Stock"
        else:
            return "In Stock"

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('salon_usage', 'Salon Usage')
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    transaction_date = models.DateTimeField(default=timezone.now)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='stock_transactions')
    
    def __str__(self):
        return f"{self.transaction_type} - {self.product.name} ({self.quantity})"
    
    def generate_reference_number(self):
        """Generate a unique reference number for the transaction"""
        # Format: TR-{transaction_type first letter}-{random 6 chars}-{timestamp}
        transaction_type_code = self.transaction_type[0].upper()
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        timestamp = timezone.now().strftime('%Y%m%d%H%M')
        return f"TR-{transaction_type_code}-{random_chars}-{timestamp}"
    
    def save(self, *args, **kwargs):
        # Calculate total amount if not provided
        if not self.total_amount:
            self.total_amount = self.quantity * self.unit_price
        
        # Generate reference number for new transactions if not provided
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        
        # Update product stock based on transaction type
        if self.transaction_type in ['purchase', 'return']:
            self.product.current_stock += self.quantity
        elif self.transaction_type in ['sale', 'salon_usage']:
            if self.product.current_stock >= self.quantity:
                self.product.current_stock -= self.quantity
            else:
                raise ValueError("Not enough stock available")
        elif self.transaction_type == 'adjustment':
            # For adjustments, quantity can be positive or negative
            self.product.current_stock += self.quantity
        
        self.product.save()
        super().save(*args, **kwargs)

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, related_name='suppliers', blank=True)
    
    def __str__(self):
        return self.name

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ordered', 'Ordered'),
        ('partial', 'Partially Received'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled')
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateTimeField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='purchase_orders')
    
    def __str__(self):
        return f"PO-{self.id} - {self.supplier.name} ({self.order_date.strftime('%Y-%m-%d')})"
    
    def update_total(self):
        self.total_amount = sum(item.total_price for item in self.items.all())
        self.save()

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_ordered = models.PositiveIntegerField()
    quantity_received = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity_ordered} units"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)
        self.purchase_order.update_total()