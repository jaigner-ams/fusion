from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('lab', 'Lab'),
        ('dentist', 'Dentist'),
    ]
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='dentist')
    lab_profile_id = models.IntegerField(null=True, blank=True, help_text="Link to labprofile.labID in external database")
    
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