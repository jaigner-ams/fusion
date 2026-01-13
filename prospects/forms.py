from django import forms
from .models import Prospect, ProspectNote, ProspectServiceType


class ProspectForm(forms.ModelForm):
    """Form for creating and editing prospects"""

    # Service types as checkboxes (multiple select)
    service_types = forms.MultipleChoiceField(
        choices=ProspectServiceType.SERVICE_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label='Service Types'
    )

    class Meta:
        model = Prospect
        fields = [
            'status', 'monthly_fee', 'lab_name', 'person_name',
            'address', 'city', 'state', 'zip_code',
            'has_mill', 'dentists_requested', 'next_contact_date',
            'zip_protect_1', 'zip_protect_2', 'zip_protect_3',
            'zip_protect_4', 'zip_protect_5', 'zip_protect_6',
            'zip_protect_7', 'zip_protect_8', 'zip_protect_9', 'zip_protect_10'
        ]
        widgets = {
            'status': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'monthly_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Monthly Fee'
            }),
            'lab_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lab Name'
            }),
            'person_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact Person Name'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Zip Code'
            }),
            'has_mill': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dentists_requested': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Number of Dentists'
            }),
            'next_contact_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'zip_protect_1': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 1'
            }),
            'zip_protect_2': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 2'
            }),
            'zip_protect_3': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 3'
            }),
            'zip_protect_4': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 4'
            }),
            'zip_protect_5': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 5'
            }),
            'zip_protect_6': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 6'
            }),
            'zip_protect_7': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 7'
            }),
            'zip_protect_8': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 8'
            }),
            'zip_protect_9': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 9'
            }),
            'zip_protect_10': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Zip 10'
            }),
        }


class ProspectNoteForm(forms.ModelForm):
    """Form for adding notes to a prospect"""

    class Meta:
        model = ProspectNote
        fields = ['note_text']
        widgets = {
            'note_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': '500',
                'placeholder': 'Enter note (max 500 characters)'
            })
        }
        labels = {
            'note_text': 'Add New Note'
        }


class NextContactDateForm(forms.ModelForm):
    """Form for editing next contact date on detail page"""

    class Meta:
        model = Prospect
        fields = ['next_contact_date']
        widgets = {
            'next_contact_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
        labels = {
            'next_contact_date': 'Next Contact Date'
        }
