from django import forms
from mgmt.models import CustomUser
from .models import (
    OVClient, OVAgreement, OVDentist, OVCallRecord, OVAppointment,
    OVClientAvailability, OVMailingSchedule, OVCallSession,
    OVPostcardDesign, OVPostcardComment,
)


class OVClientForm(forms.ModelForm):
    class Meta:
        model = OVClient
        fields = [
            'lab_name', 'owner_name', 'address', 'city', 'state', 'zip_code',
            'phone', 'email', 'membership_tier', 'call_session_mode',
            'mailing_list_size', 'monthly_fee', 'internal_notes',
        ]
        widgets = {
            'lab_name': forms.TextInput(attrs={'class': 'form-control'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'membership_tier': forms.Select(attrs={'class': 'form-control'}),
            'call_session_mode': forms.Select(attrs={'class': 'form-control'}),
            'mailing_list_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'monthly_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'internal_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class OVClientEditForm(OVClientForm):
    """Extends OVClientForm with status field for editing existing clients."""
    class Meta(OVClientForm.Meta):
        fields = OVClientForm.Meta.fields + ['status']
        widgets = {
            **OVClientForm.Meta.widgets,
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class OVAgreementSendForm(forms.ModelForm):
    class Meta:
        model = OVAgreement
        fields = ['agreement_text']
        widgets = {
            'agreement_text': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 12,
                'placeholder': 'Enter the full agreement text...',
            }),
        }


class OVStaffUserForm(forms.ModelForm):
    OV_STAFF_TYPES = [
        ('ov_admin', 'OV Admin'),
        ('csr', 'CSR'),
        ('designer', 'Designer'),
    ]

    user_type = forms.ChoiceField(choices=OV_STAFF_TYPES, widget=forms.Select(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='Confirm Password')

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'user_type']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password_confirm'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


class OVMailingScheduleForm(forms.ModelForm):
    class Meta:
        model = OVMailingSchedule
        fields = ['scheduled_date', 'description']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description...'}),
        }


class OVCallSessionForm(forms.ModelForm):
    class Meta:
        model = OVCallSession
        fields = ['scheduled_date', 'scheduled_time', 'csr', 'notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'csr': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['csr'].queryset = CustomUser.objects.filter(user_type='csr')


class OVCallSessionEditForm(forms.ModelForm):
    class Meta:
        model = OVCallSession
        fields = ['scheduled_date', 'scheduled_time', 'csr', 'status', 'notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'csr': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['csr'].queryset = CustomUser.objects.filter(user_type='csr')


class OVCallRecordForm(forms.ModelForm):
    class Meta:
        model = OVCallRecord
        fields = ['outcome', 'notes', 'email_captured', 'callback_date', 'callback_time']
        widgets = {
            'outcome': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': 1000}),
            'email_captured': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'callback_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'callback_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class OVAppointmentForm(forms.ModelForm):
    class Meta:
        model = OVAppointment
        fields = ['appointment_date', 'appointment_time']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class OVClientAvailabilityForm(forms.ModelForm):
    class Meta:
        model = OVClientAvailability
        fields = ['availability_type', 'day_of_week', 'specific_date', 'start_time', 'end_time']
        widgets = {
            'availability_type': forms.Select(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'specific_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class OVDentistCorrectionForm(forms.Form):
    correction_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the correction needed...'}),
        max_length=1000,
    )


class OVAppointmentFollowupForm(forms.ModelForm):
    class Meta:
        model = OVAppointment
        fields = ['case_status', 'client_notes', 'followup_date', 'followup_notes']
        widgets = {
            'case_status': forms.RadioSelect,
            'client_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'followup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'followup_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class OVPostcardCommentForm(forms.ModelForm):
    class Meta:
        model = OVPostcardComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add a revision comment...'}),
        }
