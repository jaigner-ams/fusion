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
        ('caller', 'Caller'),
    ]

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='dentist')
    lab_profile_id = models.IntegerField(null=True, blank=True, help_text="Link to labprofile.labID in external database")
    credits = models.IntegerField(default=0, help_text="DEPRECATED - Use economy_credits and premium_credits instead")
    economy_credits = models.IntegerField(default=0, help_text="Economy crown credit balance")
    premium_credits = models.IntegerField(default=0, help_text="Premium crown credit balance")
    lab_logo = models.ImageField(upload_to='lab_logos/', null=True, blank=True, help_text="Lab logo image")

    # Zip code protection fields (for lab users)
    zip_protect_1 = models.CharField(max_length=20, blank=True)
    zip_protect_2 = models.CharField(max_length=20, blank=True)
    zip_protect_3 = models.CharField(max_length=20, blank=True)
    zip_protect_4 = models.CharField(max_length=20, blank=True)
    zip_protect_5 = models.CharField(max_length=20, blank=True)
    zip_protect_6 = models.CharField(max_length=20, blank=True)
    zip_protect_7 = models.CharField(max_length=20, blank=True)
    zip_protect_8 = models.CharField(max_length=20, blank=True)
    zip_protect_9 = models.CharField(max_length=20, blank=True)
    zip_protect_10 = models.CharField(max_length=20, blank=True)

    zip_qty_1 = models.IntegerField(null=True, blank=True)
    zip_qty_2 = models.IntegerField(null=True, blank=True)
    zip_qty_3 = models.IntegerField(null=True, blank=True)
    zip_qty_4 = models.IntegerField(null=True, blank=True)
    zip_qty_5 = models.IntegerField(null=True, blank=True)
    zip_qty_6 = models.IntegerField(null=True, blank=True)
    zip_qty_7 = models.IntegerField(null=True, blank=True)
    zip_qty_8 = models.IntegerField(null=True, blank=True)
    zip_qty_9 = models.IntegerField(null=True, blank=True)
    zip_qty_10 = models.IntegerField(null=True, blank=True)

    # Contact info fields (primarily for labs)
    phone = models.CharField(max_length=50, blank=True, help_text="Phone number")
    street_address = models.CharField(max_length=255, blank=True, help_text="Street address")
    city = models.CharField(max_length=100, blank=True, help_text="City")
    state = models.CharField(max_length=50, blank=True, help_text="State")
    zip_code = models.CharField(max_length=20, blank=True, help_text="Zip code")
    website = models.URLField(blank=True, help_text="Website URL")

    def is_admin_user(self):
        return self.user_type == 'admin'
    
    def is_lab_user(self):
        return self.user_type == 'lab'
    
    def is_dentist_user(self):
        return self.user_type == 'dentist'

    def is_caller_user(self):
        return self.user_type == 'caller'
    
    def get_total_credits(self):
        """Get total crown credits (economy + premium)"""
        return self.economy_credits + self.premium_credits
    
    def add_credits(self, amount, credit_type='economy'):
        """Add crown credits of specified type"""
        if credit_type == 'premium':
            self.premium_credits += amount
        else:
            self.economy_credits += amount
        self.save()
    
    def deduct_credits(self, amount, credit_type='economy'):
        """Deduct crown credits of specified type. Returns True if successful, False if insufficient credits."""
        if credit_type == 'premium':
            if self.premium_credits >= amount:
                self.premium_credits -= amount
                self.save()
                return True
            return False
        else:
            if self.economy_credits >= amount:
                self.economy_credits -= amount
                self.save()
                return True
            return False
    
    def has_sufficient_credits(self, amount, credit_type='economy'):
        """Check if user has sufficient crown credits of specified type"""
        if credit_type == 'premium':
            return self.premium_credits >= amount
        else:
            return self.economy_credits >= amount

    def get_protected_zip_codes(self):
        """Return list of non-empty protected zip codes"""
        zips = []
        for i in range(1, 11):
            zip_code = getattr(self, f'zip_protect_{i}', '')
            if zip_code:
                zips.append(zip_code)
        return zips

    def get_protected_zips_with_qty(self):
        """Return list of (zip_code, quantity) tuples for non-empty zip codes"""
        zips_with_qty = []
        for i in range(1, 11):
            zip_code = getattr(self, f'zip_protect_{i}', '')
            qty = getattr(self, f'zip_qty_{i}', None)
            if zip_code:
                zips_with_qty.append((zip_code, qty))
        return zips_with_qty

    def get_full_address(self):
        """Return formatted full address"""
        parts = []
        if self.street_address:
            parts.append(self.street_address)
        city_state_zip = []
        if self.city:
            city_state_zip.append(self.city)
        if self.state:
            city_state_zip.append(self.state)
        if city_state_zip:
            parts.append(', '.join(city_state_zip))
        if self.zip_code:
            if parts:
                parts[-1] = parts[-1] + ' ' + self.zip_code
            else:
                parts.append(self.zip_code)
        return '\n'.join(parts)

    @classmethod
    def find_lab_with_protected_zip(cls, zip_code):
        """Find a lab that has protected/claimed a specific zip code (exclusive match)"""
        if not zip_code:
            return None

        # Normalize the zip code (strip whitespace)
        zip_code = zip_code.strip()

        from django.db.models import Q

        # Build query for all zip_protect fields only (not the lab's own address zip)
        query = Q()
        for i in range(1, 11):
            query |= Q(**{f'zip_protect_{i}': zip_code})

        return cls.objects.filter(user_type='lab').filter(query).first()

    @classmethod
    def find_nearest_labs_by_zip(cls, zip_code, limit=3, include_distance=False):
        """Find the nearest labs by actual geographic distance.

        Uses the ZipCode database to look up coordinates and calculates
        distance using the Haversine formula.

        Args:
            zip_code: The zip code to search from
            limit: Maximum number of labs to return
            include_distance: If True, returns list of (lab, distance) tuples

        Returns:
            List of labs, or list of (lab, distance) tuples if include_distance=True
        """
        if not zip_code:
            return []

        # Normalize zip code
        zip_code = zip_code.strip()[:5]

        # Get coordinates for the search zip code
        target_coords = ZipCode.get_coordinates(zip_code)

        # Get all labs with valid zip codes
        labs = cls.objects.filter(user_type='lab').exclude(zip_code='')

        # Calculate distance for each lab
        labs_with_distance = []
        for lab in labs:
            lab_coords = ZipCode.get_coordinates(lab.zip_code)
            if target_coords and lab_coords:
                # Calculate actual geographic distance
                distance = ZipCode.haversine_distance(
                    target_coords[0], target_coords[1],
                    lab_coords[0], lab_coords[1]
                )
                labs_with_distance.append((lab, distance))
            elif lab_coords:
                # No target coords but lab has coords - use large distance
                labs_with_distance.append((lab, 99999))
            else:
                # Fall back to numeric comparison if no coordinates available
                try:
                    target_num = int(zip_code)
                    lab_num = int(lab.zip_code[:5])
                    distance = abs(target_num - lab_num)
                    labs_with_distance.append((lab, distance))
                except (ValueError, TypeError):
                    continue

        # Sort by distance and return top results
        labs_with_distance.sort(key=lambda x: x[1])
        results = labs_with_distance[:limit]

        if include_distance:
            return results
        return [lab for lab, distance in results]

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class ZipCode(models.Model):
    """US Zip code database for geographic distance calculations."""
    zip_code = models.CharField(max_length=10, unique=True, db_index=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    state_abbr = models.CharField(max_length=2)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"{self.zip_code} - {self.city}, {self.state_abbr}"

    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in miles using Haversine formula."""
        import math

        R = 3959  # Earth's radius in miles

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @classmethod
    def get_coordinates(cls, zip_code):
        """Get lat/long for a zip code."""
        try:
            zc = cls.objects.get(zip_code=zip_code.strip()[:5])
            return (zc.latitude, zc.longitude)
        except cls.DoesNotExist:
            return None

    class Meta:
        verbose_name = 'Zip Code'
        verbose_name_plural = 'Zip Codes'


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
        ('economy', 'Economy Crowns'),
        ('premium', 'Premium Crowns'),
    ]

    lab = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'user_type': 'lab'})
    applied_after = models.IntegerField(default=0, help_text="Number of units after which this price applies")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='economy', help_text="Price type")
    product_description = models.CharField(max_length=100, blank=True, help_text="Product description (e.g., Layered Zirconia, Emax Layered)")
    is_cod = models.BooleanField(default=False, help_text="Collect on Delivery - flat rate pricing")
    notes = models.CharField(max_length=200, blank=True, help_text="Additional notes or specifics for this price")

    def __str__(self):
        desc = f" - {self.product_description}" if self.product_description else ""
        if self.is_cod:
            return f"Default ({self.get_type_display()}{desc}): COD @ ${self.price}"
        return f"Default ({self.get_type_display()}{desc}): {self.applied_after}+ units @ ${self.price}"
    
    class Meta:
        ordering = ['type', 'applied_after']
        verbose_name = "Default Price"
        verbose_name_plural = "Default Prices"

class PriceList(models.Model):
    TYPE_CHOICES = [
        ('economy', 'Economy Crowns'),
        ('premium', 'Premium Crowns'),
    ]

    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='custom_prices')
    applied_after = models.IntegerField(default=0, help_text="Number of units after which this price applies")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='economy', help_text="Price type")
    product_description = models.CharField(max_length=100, blank=True, help_text="Product description (e.g., Layered Zirconia, Emax Layered)")
    is_cod = models.BooleanField(default=False, help_text="Collect on Delivery - flat rate pricing")

    def __str__(self):
        desc = f" - {self.product_description}" if self.product_description else ""
        if self.is_cod:
            return f"{self.dentist.name} ({self.get_type_display()}{desc}): COD @ ${self.price}"
        return f"{self.dentist.name} ({self.get_type_display()}{desc}): {self.applied_after}+ units @ ${self.price}"
    
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
        ('economy', 'Economy Crowns'),
        ('premium', 'Premium Crowns'),
    ]

    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='credit_purchases')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchases_made')
    quantity = models.IntegerField(help_text="Number of crown credits to purchase")
    quality_type = models.CharField(max_length=10, choices=QUALITY_CHOICES, default='economy')
    product_description = models.CharField(max_length=100, blank=True, help_text="Product description for premium crowns")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per crown credit at time of purchase")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total price for this purchase")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Optional notes about the purchase")
    
    def __str__(self):
        return f"{self.dentist.name} - {self.quantity} crown credits @ ${self.unit_price} ({self.get_status_display()})"
    
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

            # Create a transaction record for this purchase
            # Note: CreditTransaction.save() automatically adds credits to user
            if self.user:
                CreditTransaction.objects.create(
                    user=self.user,
                    dentist=self.dentist,
                    transaction_type='purchase',
                    credit_type=self.quality_type,
                    amount=self.quantity,
                    reason=f"Crown credit purchase - {self.get_quality_type_display()}",
                    notes=f"Purchase ID: {self.id}",
                    created_by=self.user
                )
    
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
    
    CREDIT_TYPE_CHOICES = [
        ('economy', 'Economy Crowns'),
        ('premium', 'Premium Crowns'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_transactions')
    dentist = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='credit_transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    credit_type = models.CharField(max_length=10, choices=CREDIT_TYPE_CHOICES, default='economy', help_text="Type of crown credits")
    product_description = models.CharField(max_length=100, blank=True, help_text="Product description for premium crowns")
    amount = models.IntegerField(help_text="Crown credit amount (positive for addition, negative for deduction)")
    reason = models.CharField(max_length=255, help_text="Reason for the transaction")
    notes = models.TextField(blank=True, help_text="Additional notes about the transaction")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions_created')
    created_at = models.DateTimeField(auto_now_add=True)
    balance_after = models.IntegerField(help_text="DEPRECATED - Use economy_balance_after and premium_balance_after")
    economy_balance_after = models.IntegerField(default=0, help_text="Economy crown credit balance after transaction")
    premium_balance_after = models.IntegerField(default=0, help_text="Premium crown credit balance after transaction")
    reversed_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversal_of', help_text="Transaction that reversed this one")
    is_reversed = models.BooleanField(default=False, help_text="Whether this transaction has been reversed")
    
    def __str__(self):
        action = "+" if self.amount >= 0 else ""
        return f"{self.user.username} - {action}{self.amount} {self.get_credit_type_display()} crown credits ({self.get_transaction_type_display()})"
    
    def save(self, *args, **kwargs):
        # Update user's crown credit balance based on credit type
        if self.pk is None:  # New transaction
            if self.credit_type == 'premium':
                self.user.premium_credits += self.amount
                self.user.premium_credits = max(0, self.user.premium_credits)
                self.premium_balance_after = self.user.premium_credits
                self.economy_balance_after = self.user.economy_credits
            else:
                self.user.economy_credits += self.amount
                self.user.economy_credits = max(0, self.user.economy_credits)
                self.economy_balance_after = self.user.economy_credits
                self.premium_balance_after = self.user.premium_credits
            
            # Keep legacy field for backward compatibility
            self.balance_after = self.user.economy_credits + self.user.premium_credits
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
        
        # Create reversal transaction with same credit type
        reversal = CreditTransaction.objects.create(
            user=self.user,
            dentist=self.dentist,
            transaction_type='adjustment',
            credit_type=self.credit_type,  # Use same credit type as original
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