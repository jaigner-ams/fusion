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

class CreditDeductionForm(forms.ModelForm):
    class Meta:
        model = CreditTransaction
        fields = ['amount', 'reason', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1',
                'placeholder': 'Enter number of credits to deduct'
            }),
            'reason': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Reason for credit deduction'
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
        self.fields['amount'].label = 'Credits to Deduct'
        self.fields['amount'].help_text = f'Current balance: {self.user.credits if self.user else 0} credits'
        self.fields['reason'].label = 'Reason'
        self.fields['reason'].help_text = 'Please provide a reason for this deduction'
        self.fields['notes'].label = 'Notes'
        self.fields['notes'].required = False
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount < 1:
            raise forms.ValidationError('Amount must be at least 1 credit')
        
        if self.user and amount > self.user.credits:
            raise forms.ValidationError(f'Cannot deduct {amount} credits. User only has {self.user.credits} credits available.')
        
        return amount
    
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
            # Check file size (limit to 50MB)
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 50MB')
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