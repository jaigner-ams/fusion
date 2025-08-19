from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Dentist, DefaultPriceList, PriceList, CustomUser, CreditPurchase
from decimal import Decimal

class DentistForm(forms.ModelForm):
    class Meta:
        model = Dentist
        fields = ['name', 'lab']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter dentist name'}),
            'lab': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_admin_user():
            self.fields.pop('lab', None)
        elif 'lab' in self.fields:
            self.fields['lab'].queryset = CustomUser.objects.filter(user_type='lab')

class DefaultPriceForm(forms.ModelForm):
    class Meta:
        model = DefaultPriceList
        fields = ['lab', 'applied_after', 'price', 'type']
        widgets = {
            'lab': forms.Select(attrs={'class': 'form-control'}),
            'applied_after': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'type': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_admin_user():
            self.fields.pop('lab', None)
        elif 'lab' in self.fields:
            self.fields['lab'].queryset = CustomUser.objects.filter(user_type='lab')

class CustomPriceForm(forms.ModelForm):
    class Meta:
        model = PriceList
        fields = ['applied_after', 'price', 'type']
        widgets = {
            'applied_after': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'type': forms.Select(attrs={'class': 'form-control'})
        }

class CustomUserCreationForm(UserCreationForm):
    user_type = forms.ChoiceField(
        choices=CustomUser.USER_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'user_type', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'

class AdminUserCreationForm(CustomUserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_type'].initial = 'admin'
        self.fields['user_type'].widget = forms.HiddenInput()

class LabUserCreationForm(CustomUserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_type'].initial = 'lab'
        self.fields['user_type'].widget = forms.HiddenInput()

class DentistUserCreationForm(CustomUserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_type'].initial = 'dentist'
        self.fields['user_type'].widget = forms.HiddenInput()

class DentistWithUserForm(forms.ModelForm):
    create_user_account = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Create a user account for this dentist to allow them to log in'
    )
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username for dentist login'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    password1 = forms.CharField(
        label='Password',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    
    class Meta:
        model = Dentist
        fields = ['name', 'lab']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter dentist name'}),
            'lab': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_admin_user():
            self.fields.pop('lab', None)
        elif 'lab' in self.fields:
            self.fields['lab'].queryset = CustomUser.objects.filter(user_type='lab')
        
        # If editing existing dentist with user account
        if self.instance.pk and self.instance.user:
            self.fields['create_user_account'].initial = True
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            # Hide password fields for existing users
            self.fields.pop('password1', None)
            self.fields.pop('password2', None)
    
    def clean(self):
        cleaned_data = super().clean()
        create_account = cleaned_data.get('create_user_account')
        
        if create_account:
            username = cleaned_data.get('username')
            email = cleaned_data.get('email')
            password1 = cleaned_data.get('password1')
            password2 = cleaned_data.get('password2')
            
            if not username:
                self.add_error('username', 'Username is required when creating a user account')
            elif CustomUser.objects.filter(username=username).exclude(pk=self.instance.user.pk if self.instance.user else None).exists():
                self.add_error('username', 'A user with this username already exists')
            
            if not email:
                self.add_error('email', 'Email is required when creating a user account')
            
            # Only validate passwords for new users
            if not self.instance.user:
                if not password1:
                    self.add_error('password1', 'Password is required when creating a user account')
                elif password1 != password2:
                    self.add_error('password2', 'Passwords do not match')
        
        return cleaned_data
    
    def save(self, commit=True):
        dentist = super().save(commit=False)
        
        if self.cleaned_data.get('create_user_account'):
            if not dentist.user:
                # Create new user account
                user = CustomUser.objects.create_user(
                    username=self.cleaned_data['username'],
                    email=self.cleaned_data['email'],
                    password=self.cleaned_data['password1'],
                    user_type='dentist'
                )
                user.first_name = dentist.name
                user.save()
                dentist.user = user
            else:
                # Update existing user account
                dentist.user.username = self.cleaned_data['username']
                dentist.user.email = self.cleaned_data['email']
                dentist.user.first_name = dentist.name
                dentist.user.save()
        elif dentist.user:
            # Remove user account if unchecked
            user = dentist.user
            dentist.user = None
            if commit:
                dentist.save()
            user.delete()
            return dentist
        
        if commit:
            dentist.save()
        
        return dentist

class CreditPurchaseForm(forms.ModelForm):
    class Meta:
        model = CreditPurchase
        fields = ['quantity', 'quality_type']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1',
                'placeholder': 'Enter number of credits'
            }),
            'quality_type': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        self.dentist = kwargs.pop('dentist', None)
        super().__init__(*args, **kwargs)
        
        if self.dentist:
            # Get available quality types based on configured prices
            available_types = set()
            
            # Check custom prices
            custom_prices = PriceList.objects.filter(dentist=self.dentist).values_list('type', flat=True).distinct()
            available_types.update(custom_prices)
            
            # Check default prices
            default_prices = DefaultPriceList.objects.filter(lab=self.dentist.lab).values_list('type', flat=True).distinct()
            available_types.update(default_prices)
            
            # Filter quality choices to only show available types
            if available_types:
                self.fields['quality_type'].choices = [
                    choice for choice in CreditPurchase.QUALITY_CHOICES 
                    if choice[0] in available_types
                ]
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity < 1:
            raise forms.ValidationError('Quantity must be at least 1')
        return quantity
    
    def get_price_info(self):
        """Get price information for the current quantity and quality type"""
        if not self.is_valid():
            return None
        
        quantity = self.cleaned_data['quantity']
        quality_type = self.cleaned_data['quality_type']
        
        # First check for custom prices
        custom_prices = PriceList.objects.filter(
            dentist=self.dentist,
            type=quality_type
        ).order_by('-applied_after')
        
        price_per_unit = Decimal('0')
        price_source = 'No price configured'
        
        if custom_prices.exists():
            for price in custom_prices:
                if quantity >= price.applied_after:
                    price_per_unit = price.price
                    price_source = f'Custom price: {quantity} credits @ ${price.price}/credit'
                    break
        
        # Fall back to default prices if no custom price found
        if price_per_unit == 0:
            default_prices = DefaultPriceList.objects.filter(
                lab=self.dentist.lab,
                type=quality_type
            ).order_by('-applied_after')
            
            for price in default_prices:
                if quantity >= price.applied_after:
                    price_per_unit = price.price
                    price_source = f'Default price: {quantity} credits @ ${price.price}/credit'
                    break
        
        total_price = price_per_unit * quantity
        
        return {
            'quantity': quantity,
            'quality_type': quality_type,
            'price_per_unit': price_per_unit,
            'total_price': total_price,
            'price_source': price_source
        }