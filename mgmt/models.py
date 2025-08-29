from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
import random
import string
from datetime import datetime

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

class CreditTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('purchase', 'Purchase'),
        ('deduction', 'Deduction'),
        ('adjustment', 'Adjustment'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_transactions')
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='credit_transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.IntegerField(help_text="Credit amount (positive for addition, negative for deduction)")
    reason = models.CharField(max_length=255, help_text="Reason for the transaction")
    notes = models.TextField(blank=True, help_text="Additional notes about the transaction")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions_created')
    created_at = models.DateTimeField(auto_now_add=True)
    balance_after = models.IntegerField(help_text="User's credit balance after this transaction")
    reversed_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversal_of', help_text="Transaction that reversed this one")
    is_reversed = models.BooleanField(default=False, help_text="Whether this transaction has been reversed")
    
    def __str__(self):
        action = "+" if self.amount >= 0 else ""
        return f"{self.user.username} - {action}{self.amount} credits ({self.get_transaction_type_display()})"
    
    def save(self, *args, **kwargs):
        # Update user's credit balance
        if self.pk is None:  # New transaction
            self.user.credits += self.amount
            self.user.credits = max(0, self.user.credits)  # Don't allow negative credits
            self.balance_after = self.user.credits
            self.user.save()
        super().save(*args, **kwargs)
    
    def can_be_reversed(self):
        """Check if this transaction can be reversed"""
        return (
            self.transaction_type == 'deduction' and 
            not self.is_reversed and 
            self.amount < 0  # Should be negative for deductions
        )
    
    def reverse_transaction(self, reversed_by_user, reason=None):
        """Create a reversal transaction"""
        if not self.can_be_reversed():
            raise ValueError("This transaction cannot be reversed")
        
        # Create reversal transaction
        reversal = CreditTransaction.objects.create(
            user=self.user,
            dentist=self.dentist,
            transaction_type='adjustment',
            amount=abs(self.amount),  # Positive amount to add credits back
            reason=reason or f"Reversal of deduction: {self.reason}",
            notes=f"Reversal of transaction #{self.id}",
            created_by=reversed_by_user
        )
        
        # Mark original transaction as reversed
        self.is_reversed = True
        self.reversed_by = reversal
        self.save()
        
        return reversal
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Credit Transaction"
        verbose_name_plural = "Credit Transactions"

class FileUpload(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('downloaded', 'Downloaded'),
    ]
    
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='uploaded_files')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='files_uploaded')
    lab = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'user_type': 'lab'}, related_name='received_files')
    file = models.FileField(upload_to='dentist_uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    description = models.TextField(blank=True, help_text="Optional description of the file")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    downloaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='files_downloaded')
    
    def __str__(self):
        return f"{self.dentist.name} - {self.original_filename} ({self.get_status_display()})"
    
    def mark_as_downloaded(self, user):
        if self.status == 'pending':
            self.status = 'downloaded'
            self.downloaded_at = timezone.now()
            self.downloaded_by = user
            self.save()
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "File Upload"
        verbose_name_plural = "File Uploads"


@receiver(post_save, sender=Dentist)
def create_user_for_dentist(sender, instance, created, **kwargs):
    """Automatically create a user account when a new dentist is created"""
    if created and not instance.user:
        # Check if custom username/email were provided (set by the form)
        if hasattr(instance, '_custom_username'):
            username = instance._custom_username
        else:
            # Generate a unique username from the dentist's name
            base_username = ''.join(instance.name.lower().split())[:20]  # Remove spaces, limit to 20 chars
            username = base_username
            counter = 1
            
            # Ensure username is unique
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
        
        # Use custom email if provided, otherwise use default
        if hasattr(instance, '_custom_email'):
            email = instance._custom_email
        else:
            email = f"{username}@dental-lab.com"
        
        # Generate a random password
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        # Create the user account
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type='dentist',
            first_name=instance.name
        )
        
        # Link the user to the dentist
        instance.user = user
        instance.save()
        
        # Store generated credentials temporarily (not persisted to DB)
        # This allows the view to access them for display
        instance._generated_username = username
        instance._generated_password = password
        
        # Send email with credentials if email is available
        if email and email != f"{username}@dental-lab.com":
            try:
                # Build the login URL
                login_url = f"{settings.DEFAULT_FROM_EMAIL.split('<')[0].strip()}/accounts/login/"
                if hasattr(settings, 'SITE_URL'):
                    login_url = f"{settings.SITE_URL}/accounts/login/"
                else:
                    login_url = "http://your-domain.com/accounts/login/"  # Update with actual domain
                
                # Prepare context for email template
                context = {
                    'dentist_name': instance.name,
                    'username': username,
                    'password': password,
                    'lab_name': instance.lab.first_name or instance.lab.username,
                    'login_url': login_url,
                    'current_year': datetime.now().year,
                }
                
                # Render email templates
                html_message = render_to_string('mgmt/email/new_dentist_credentials.html', context)
                plain_message = render_to_string('mgmt/email/new_dentist_credentials.txt', context)
                
                # Send email
                send_mail(
                    subject='Your AMS Fusion Account Has Been Created',
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                print(f"Credentials email sent to {email} for dentist {instance.name}")
            except Exception as e:
                print(f"Failed to send email to {email}: {str(e)}")
                # Don't fail the user creation if email fails
                pass