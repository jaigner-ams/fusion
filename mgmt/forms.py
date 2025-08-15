from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Dentist, DefaultPriceList, PriceList, CustomUser

class DentistForm(forms.ModelForm):
    class Meta:
        model = Dentist
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter dentist name'})
        }

class DefaultPriceForm(forms.ModelForm):
    class Meta:
        model = DefaultPriceList
        fields = ['applied_after', 'price', 'type']
        widgets = {
            'applied_after': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'type': forms.Select(attrs={'class': 'form-control'})
        }

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