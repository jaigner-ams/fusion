from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Dentist, DefaultPriceList, PriceList, CustomUser, CreditPurchase, CreditTransaction, FileUpload
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

class LabProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'email', 'phone', 'address', 'website', 'lab_logo']
        labels = {
            'first_name': 'Lab Name',
            'email': 'Contact Email',
            'phone': 'Phone Number',
            'address': 'Business Address',
            'website': 'Website URL',
            'lab_logo': 'Lab Logo'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter lab name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter business address', 'rows': 3}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
            'lab_logo': forms.FileInput(attrs={'class': 'form-control'})
        }

class DefaultPriceForm(forms.ModelForm):
    class Meta:
        model = DefaultPriceList
        fields = ['lab', 'is_cod', 'applied_after', 'price', 'type', 'product_description', 'notes']
        widgets = {
            'lab': forms.Select(attrs={'class': 'form-control'}),
            'is_cod': forms.CheckboxInput(attrs={'class': 'form-check-input cod-checkbox'}),
            'applied_after': forms.NumberInput(attrs={'class': 'form-control applied-after-input', 'min': '0'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'type': forms.Select(attrs={'class': 'form-control type-select'}),
            'product_description': forms.TextInput(attrs={'class': 'form-control product-desc', 'placeholder': 'e.g., Layered Zirconia, Emax Layered'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Additional notes (economy only)'})
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
        fields = ['is_cod', 'applied_after', 'price', 'type', 'product_description']
        widgets = {
            'is_cod': forms.CheckboxInput(attrs={'class': 'form-check-input cod-checkbox'}),
            'applied_after': forms.NumberInput(attrs={'class': 'form-control applied-after-input', 'min': '0'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'type': forms.Select(attrs={'class': 'form-control type-select'}),
            'product_description': forms.TextInput(attrs={'class': 'form-control product-desc', 'placeholder': 'e.g., Layered Zirconia, Emax Layered'})
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
    # Optional fields to update the auto-generated user account
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username (optional - will be auto-generated if left blank)'}),
        help_text='Leave blank to auto-generate a username'
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address (optional)'}),
        help_text='Leave blank to use default email'
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
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            # Also update the widget value attribute for proper display
            self.fields['username'].widget.attrs['value'] = self.instance.user.username
            self.fields['email'].widget.attrs['value'] = self.instance.user.email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Check if username already exists (excluding current user if editing)
            existing = CustomUser.objects.filter(username=username)
            if self.instance.pk and self.instance.user:
                existing = existing.exclude(pk=self.instance.user.pk)
            if existing.exists():
                raise forms.ValidationError('A user with this username already exists')
        return username
    
    def save(self, commit=True):
        dentist = super().save(commit=False)
        
        # If this is a new dentist, pass custom username/email to the model
        if not self.instance.pk:
            username = self.cleaned_data.get('username')
            email = self.cleaned_data.get('email')
            
            if username:
                dentist._custom_username = username
            if email:
                dentist._custom_email = email
        
        # Update existing user account if dentist already has one
        elif self.instance.user:
            username = self.cleaned_data.get('username')
            email = self.cleaned_data.get('email')
            
            # Update username if provided or keep existing
            if username:
                dentist.user.username = username
            
            # Update email - allow empty string to clear email
            if email is not None:  # Check for None, not empty string
                dentist.user.email = email
            
            # Always update the first name to match dentist name
            dentist.user.first_name = dentist.name
            dentist.user.save()
        
        if commit:
            dentist.save()
            # Note: For new dentists, the signal will automatically create a user account
        
        return dentist

class CreditPurchaseForm(forms.ModelForm):
    class Meta:
        model = CreditPurchase
        fields = ['quantity', 'quality_type']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '5',
                'placeholder': 'Enter number of crown credits (minimum 5)'
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
        if quantity and quantity < 5:
            raise forms.ValidationError('Minimum purchase is 5 crown credits')
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
                    price_source = f'Custom price: {quantity} crown credits @ ${price.price}/crown credit'
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
                    price_source = f'Default price: {quantity} crown credits @ ${price.price}/crown credit'
                    break
        
        total_price = price_per_unit * quantity
        
        return {
            'quantity': quantity,
            'quality_type': quality_type,
            'price_per_unit': price_per_unit,
            'total_price': total_price,
            'price_source': price_source
        }

class CreditDeductionForm(forms.ModelForm):
    class Meta:
        model = CreditTransaction
        fields = ['credit_type', 'amount', 'reason', 'notes']
        widgets = {
            'credit_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1',
                'placeholder': 'Enter number of crown credits to deduct'
            }),
            'reason': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Reason for crown credit deduction'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.lab_user = kwargs.pop('lab_user', None)
        super().__init__(*args, **kwargs)
        
        # Set field labels and help text
        self.fields['credit_type'].label = 'Crown Credit Type'
        self.fields['credit_type'].help_text = f'Economy: {self.user.economy_credits if self.user else 0} | Premium: {self.user.premium_credits if self.user else 0}'
        self.fields['amount'].label = 'Crown Credits to Deduct'
        self.fields['reason'].label = 'Reason'
        self.fields['reason'].help_text = 'Please provide a reason for this deduction'
        self.fields['notes'].label = 'Notes'
        self.fields['notes'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        credit_type = cleaned_data.get('credit_type')
        
        if amount and amount < 1:
            raise forms.ValidationError('Amount must be at least 1 crown credit')
        
        if self.user and amount and credit_type:
            if credit_type == 'premium':
                available = self.user.premium_credits
            else:
                available = self.user.economy_credits
            
            if amount > available:
                raise forms.ValidationError(f'Cannot deduct {amount} {credit_type} crown credits. User only has {available} {credit_type} crown credits available.')
        
        return cleaned_data
    
    def clean_reason(self):
        reason = self.cleaned_data.get('reason')
        if not reason or len(reason.strip()) < 3:
            raise forms.ValidationError('Please provide a clear reason for the deduction (minimum 3 characters)')
        return reason.strip()
    
    def save(self, commit=True):
        transaction = super().save(commit=False)
        transaction.user = self.user
        transaction.created_by = self.lab_user
        transaction.transaction_type = 'deduction'
        transaction.amount = -abs(transaction.amount)  # Make sure it's negative for deduction
        
        if commit:
            transaction.save()
        
        return transaction

class DentistPasswordChangeForm(forms.Form):
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        help_text="Password must be at least 8 characters long"
    )
    new_password2 = forms.CharField(
        label="Confirm Password", 
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        help_text="Enter the same password as before, for verification"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.lab_user = kwargs.pop('lab_user', None)
        super().__init__(*args, **kwargs)
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        
        if not password:
            raise forms.ValidationError('Password is required')
        
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long')
        
        # Basic password strength validation
        if password.isdigit():
            raise forms.ValidationError('Password cannot be entirely numeric')
        
        if password.lower() in ['password', '12345678', 'password123']:
            raise forms.ValidationError('This password is too common')
        
        return password
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('The two password fields didn\'t match')
        
        return password2
    
    def save(self):
        """Change the user's password"""
        if not self.user:
            raise ValueError("No user specified")
        
        new_password = self.cleaned_data['new_password1']
        self.user.set_password(new_password)
        self.user.save()
        
        return self.user

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '*/*'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description of the file'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.dentist = kwargs.pop('dentist', None)
        super().__init__(*args, **kwargs)
        
        self.fields['file'].label = 'Select File'
        self.fields['file'].help_text = 'Choose a file to upload for the lab'
        self.fields['description'].required = False
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (limit to 500MB)
            if file.size > 500 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 500MB')
        return file
    
    def save(self, commit=True):
        upload = super().save(commit=False)
        upload.uploaded_by = self.user
        upload.dentist = self.dentist
        upload.lab = self.dentist.lab
        upload.original_filename = self.cleaned_data['file'].name
        
        if commit:
            upload.save()
        
        return upload