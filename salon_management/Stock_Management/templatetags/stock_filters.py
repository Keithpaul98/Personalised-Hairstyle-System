from django import template
import builtins
from Stock_Management.models import Product

register = template.Library()

@register.filter
def get_product_price(product_id):
    """
    Get the cost price of a product by its ID
    """
    try:
        if product_id:
            # Convert ModelChoiceIteratorValue to int if needed
            if hasattr(product_id, 'value'):
                product_id = product_id.value
                
            product = Product.objects.get(pk=product_id)
            return product.cost_price
        return 0
    except (Product.DoesNotExist, ValueError, TypeError):
        return 0

@register.filter
def abs_value(value):
    """
    Returns the absolute value of a number
    """
    try:
        return builtins.abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def get_product_current_stock(product_id):
    """
    Get the current stock of a product by its ID
    """
    try:
        if product_id:
            # Convert ModelChoiceIteratorValue to int if needed
            if hasattr(product_id, 'value'):
                product_id = product_id.value
                
            product = Product.objects.get(pk=product_id)
            return product.current_stock
        return 0
    except (Product.DoesNotExist, ValueError, TypeError):
        return 0

@register.filter
def get_product_min_stock(product_id):
    """
    Get the minimum stock level of a product by its ID
    """
    try:
        if product_id:
            # Convert ModelChoiceIteratorValue to int if needed
            if hasattr(product_id, 'value'):
                product_id = product_id.value
                
            product = Product.objects.get(pk=product_id)
            return product.minimum_stock
        return 0
    except (Product.DoesNotExist, ValueError, TypeError):
        return 0