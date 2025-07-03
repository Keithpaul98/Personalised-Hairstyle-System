from django.template import library
from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def sub(value, arg):
    """Subtract the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def add(value, arg):
    """Add the argument to the value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def index(sequence, position):
    """Get an item from a sequence by index"""
    try:
        return sequence[int(position)]
    except (IndexError, TypeError, ValueError):
        return None

@register.filter
def max_value(value):
    """Return the maximum value in a list"""
    try:
        if not value or all(x == 0 for x in value):
            return 1  # Return 1 as minimum to prevent division by zero
        return max([float(x) for x in value if x is not None and x != 0])
    except (ValueError, TypeError):
        return 1  # Return 1 as minimum to prevent division by zero