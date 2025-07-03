from django import forms
from .models import Product, ProductCategory, StockTransaction, Supplier, PurchaseOrder, PurchaseOrderItem
from django.forms import inlineformset_factory

class ProductForm(forms.ModelForm):
    initial_stock = forms.IntegerField(
        required=False, 
        min_value=0,
        help_text="Initial stock quantity (optional)"
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'cost_price',
            'minimum_stock', 'image', 'barcode', 'usage_type', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = [
            'product', 'transaction_type', 'quantity', 
            'unit_price', 'total_amount', 'reference_number', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'transaction_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        
        if product:
            self.fields['product'].initial = product
            self.fields['product'].widget = forms.HiddenInput()
        
        # Make total_amount optional as it will be calculated
        self.fields['total_amount'].required = False

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_person', 'email', 'phone', 
            'address', 'is_active', 'products'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'products': forms.SelectMultiple(attrs={'class': 'select2'}),
        }

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'expected_delivery_date', 'status', 'notes'
        ]
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

# Create a formset for purchase order items
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    fields=('product', 'quantity_ordered', 'unit_price', 'total_price'),
    extra=1,
    can_delete=True,
    widgets={
        'product': forms.Select(attrs={'class': 'select2'}),
        'total_price': forms.HiddenInput(),
    }
)