from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('lab', 'Lab'),
        ('dentist', 'Dentist'),
    ]
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='dentist')
    lab_profile_id = models.IntegerField(null=True, blank=True, help_text="Link to labprofile.labID in external database")
    credits = models.IntegerField(default=0, help_text="User account credits")
    
    def is_admin_user(self):
        return self.user_type == 'admin'
    
    def is_lab_user(self):
        return self.user_type == 'lab'
    
    def is_dentist_user(self):
        return self.user_type == 'dentist'
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class Dentist(models.Model):
    name = models.CharField(max_length=128)
    lab = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'user_type': 'lab'}, related_name='lab_dentists')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'user_type': 'dentist'}, related_name='dentist_profile', help_text="Optional: Link to a user account for this dentist")
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class DefaultPriceList(models.Model):
    TYPE_CHOICES = [
        ('economy', 'Economy'),
        ('premium', 'Premium Quality'),
    ]
    
    lab = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'user_type': 'lab'})
    applied_after = models.IntegerField(help_text="Number of units after which this price applies")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='economy', help_text="Price type")
    
    def __str__(self):
        return f"Default ({self.get_type_display()}): {self.applied_after}+ units @ ${self.price}"
    
    class Meta:
        ordering = ['type', 'applied_after']
        verbose_name = "Default Price"
        verbose_name_plural = "Default Prices"

class PriceList(models.Model):
    TYPE_CHOICES = [
        ('economy', 'Economy'),
        ('premium', 'Premium Quality'),
    ]
    
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='custom_prices')
    applied_after = models.IntegerField(help_text="Number of units after which this price applies")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='economy', help_text="Price type")
    
    def __str__(self):
        return f"{self.dentist.name} ({self.get_type_display()}): {self.applied_after}+ units @ ${self.price}"
    
    class Meta:
        ordering = ['dentist', 'type', 'applied_after']
        verbose_name = "Custom Price"
        verbose_name_plural = "Custom Prices"
        unique_together = ['dentist', 'applied_after', 'type']

class CreditPurchase(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    QUALITY_CHOICES = [
        ('economy', 'Economy'),
        ('premium', 'Premium Quality'),
    ]
    
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='credit_purchases')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchases_made')
    quantity = models.IntegerField(help_text="Number of credits to purchase")
    quality_type = models.CharField(max_length=10, choices=QUALITY_CHOICES, default='economy')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per credit at time of purchase")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total price for this purchase")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Optional notes about the purchase")
    
    def __str__(self):
        return f"{self.dentist.name} - {self.quantity} credits @ ${self.unit_price} ({self.get_status_display()})"
    
    def calculate_price(self):
        """Calculate the price based on quantity and applicable pricing tiers"""
        # First check for custom prices for this dentist
        custom_prices = PriceList.objects.filter(
            dentist=self.dentist,
            type=self.quality_type
        ).order_by('-applied_after')
        
        if custom_prices.exists():
            for price in custom_prices:
                if self.quantity >= price.applied_after:
                    return price.price
        
        # Fall back to default prices
        default_prices = DefaultPriceList.objects.filter(
            lab=self.dentist.lab,
            type=self.quality_type
        ).order_by('-applied_after')
        
        for price in default_prices:
            if self.quantity >= price.applied_after:
                return price.price
        
        # If no price found, return 0 (should not happen if prices are set correctly)
        return 0
    
    def complete_purchase(self):
        """Mark purchase as completed and add credits to user"""
        if self.status == 'pending':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            
            # Add credits to user account
            if self.user:
                self.user.credits += self.quantity
                self.user.save()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Credit Purchase"
        verbose_name_plural = "Credit Purchases"