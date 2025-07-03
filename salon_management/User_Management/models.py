from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import datetime, timedelta
from django.utils.timezone import now, timezone
import logging
from services.models import Service  # Import from correct location

logger = logging.getLogger(__name__)

class CustomUser(AbstractUser):
    ROLES = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
        ('staff', 'Staff'),
    )
    is_staff = models.BooleanField(
        'staff status',
        default=False,
        help_text='Designates whether the user can log into this admin site.',
    )
    is_superuser = models.BooleanField(
        'superuser status',
        default=False,
        help_text='Designates that this user has all permissions without explicitly assigning them.',
    )
    role = models.CharField(max_length=20, choices=ROLES, default='customer')
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_ratings = models.PositiveIntegerField(default=0)
    expertise = models.ManyToManyField('services.Service', blank=True, related_name='expert_staff')
    address = models.CharField(max_length=150, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Customer-specific fields
    loyalty_points = models.PositiveIntegerField(default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    discount_expiry = models.DateField(blank=True, null=True)
    # Track total earned points separately from current available points
    total_earned_points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.username
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_customer(self):
        return self.role == 'customer'
    
    def is_staff_member(self):
        return self.role == 'staff'
    
    def update_rating(self, new_rating):
        # Calculate new average rating
        total = self.average_rating * self.total_ratings
        total += new_rating
        self.total_ratings += 1
        self.average_rating = total / self.total_ratings
        self.save()
        
    def check_discount_expiry(self):
        """
        Check if the user's discount has expired and handle points accordingly.
        Returns True if discount was expired and handled, False otherwise.
        """
        today = now().date()
        
        # If there's no expiry date or discount, nothing to do
        if not self.discount_expiry or self.discount <= 0:
            return False
            
        # If discount has expired
        if today > self.discount_expiry:
            logger.info(f"Discount expired for user {self.username}")
            # Reset discount
            self.discount = 0
            self.discount_expiry = None
            self.save()
            return True
            
        return False
        
    def add_loyalty_points(self, points_to_add):
        """
        Add loyalty points to the user's account and update total earned points.
        Also checks for discount eligibility.
        
        Returns a tuple: (points_added, discount_message)
        """
        # First check if any existing discount has expired
        self.check_discount_expiry()
        
        # Add points
        self.loyalty_points += points_to_add
        self.total_earned_points += points_to_add
        
        # Check for discount eligibility
        discount_message = ""
        points = self.loyalty_points
        
        # Loyalty discount tiers (points, discount percentage, valid days)
        discount_tiers = [
            (4000, 100, 14),  # 100% off for 14 days at 4000 points
            (2000, 100, 10),  # 100% off for 10 days at 2000 points
            (1000, 100, 7),   # 100% off for 7 days at 1000 points
            (500, 50, 7),     # 50% off for 7 days at 500 points
            (200, 20, 7),     # 20% off for 7 days at 200 points
            (100, 10, 7),     # 10% off for 7 days at 100 points
        ]
        
        for threshold, discount, days in discount_tiers:
            if points >= threshold:
                self.discount = discount
                # Use timezone.now() instead of now() to ensure timezone awareness
                expiry_date = timezone.now().date() + timedelta(days=days)
                self.discount_expiry = expiry_date
                self.loyalty_points = points - threshold  # Only subtract the threshold, not reset to 0
                
                # Format the expiry date in the message
                formatted_expiry = expiry_date.strftime("%B %d, %Y")
                discount_message = (
                    f"Congratulations! You've earned a {discount}% discount "
                    f"valid until {formatted_expiry}!"
                )
                break
                
        self.save()
        return points_to_add, discount_message
        
    def revoke_loyalty_points(self, points_to_revoke):
        """
        Revoke loyalty points from the user's account when an appointment is cancelled.
        Ensures points don't go below zero.
        
        Returns the actual number of points revoked.
        """
        # First check if any existing discount has expired
        self.check_discount_expiry()
        
        # Calculate how many points to actually revoke
        actual_points_to_revoke = min(points_to_revoke, self.loyalty_points)
        
        # Revoke points
        self.loyalty_points -= actual_points_to_revoke
        
        # Don't reduce total_earned_points, as that tracks lifetime points
        # But we do need to ensure the user doesn't have more points than they should
        
        self.save()
        return actual_points_to_revoke


class Purchase(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey('Stock_Management.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchased_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)

            # Update the loyalty points
            self.customer.loyalty_points += 10
            logger.debug(f'Added {10} points. Total points now: {self.customer.loyalty_points}')
            self.customer.save(update_fields=['loyalty_points'])

            # Check if discount needs to be updated
            self.check_discount()

    def check_discount(self):
        points = self.customer.loyalty_points
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
                self.customer.discount = discount
                self.customer.discount_expiry = now() + timedelta(days=days)
                self.customer.loyalty_points = max(0, points - threshold)
                logger.debug(f'New discount: {discount}%, expires on: {self.customer.discount_expiry}')
                break
        self.customer.save(update_fields=['discount', 'discount_expiry', 'loyalty_points'])


class CartItem(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey('Stock_Management.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.customer.username}'s cart: {self.product.name} x {self.quantity}"
    
    def total_price(self):
        return self.product.price * self.quantity
    

class Receipt(models.Model): 
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True) 
    
    def __str__(self): 
        return f"Receipt #{self.id} - Customer: {self.customer.username}" 
    
    
class ReceiptItem(models.Model): 
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Stock_Management.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def total_price(self): 
        return self.quantity * self.price 
    
    def __str__(self): 
        return f"{self.product.name} x {self.quantity} on {self.receipt}"
