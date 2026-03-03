from django.db import models
from django.conf import settings
from django.utils import timezone


class Mailer(models.Model):
    """Tracks mailer batches sent out to prospects"""
    date = models.DateField()
    description = models.CharField(max_length=200, blank=True)
    prospect_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Mailer"
        verbose_name_plural = "Mailers"

    def __str__(self):
        return f"Mailer {self.date.strftime('%m/%d/%Y')} ({self.prospect_count} prospects)"


class Prospect(models.Model):
    """Main prospect/lead model for tracking potential dental lab customers"""

    STATUS_CHOICES = [
        ('prospect', 'Fusion Prospect'),
        ('member', 'Fusion Member'),
        ('declined', 'Fusion Declined'),
        ('corporate', 'Corporate Lab'),
        ('mailed', 'Mailed'),
        ('callback', 'Call Back'),
        ('sent_to_keith', 'Sent to Keith'),
        ('keith_closed', 'Keith Closed'),
        ('not_interested', 'Not Interested'),
        ('left_voicemail', 'Left Voicemail'),
    ]

    AMS_HISTORY_CHOICES = [
        ('current_ams_ed', 'Current AMS Ed'),
        ('current_onevoice', 'Current OneVoice'),
        ('current_member', 'Current Member'),
        ('past_member', 'Past Member'),
    ]

    SERVICE_TYPE_CHOICES = [
        ('crown_bridge', 'Crown and Bridge'),
        ('denture', 'Denture'),
        ('full_service', 'Full Service'),
    ]

    # AMS History - Radio button in form (optional)
    ams_history = models.CharField(max_length=20, choices=AMS_HISTORY_CHOICES, blank=True, default='')

    # Status - Radio button in form
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='prospect')

    # Link to created Lab user account (when prospect becomes a member)
    lab_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prospect_profile',
        help_text="Lab user account created for this prospect"
    )

    # Mailer batch link
    mailer = models.ForeignKey(
        Mailer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prospects',
        help_text="Mailer batch this prospect was imported from"
    )

    # Lead fields
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lab_name = models.CharField(max_length=200)
    person_name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=200, blank=True)

    # Service types - stored as separate model for multiple selection
    # (handled via ProspectServiceType model below)

    # Has Mill - Yes/No checkbox
    has_mill = models.BooleanField(default=False)

    # Number of Dentists Requested
    dentists_requested = models.IntegerField(default=0, null=True, blank=True)

    # Zip codes to protect (10 separate fields as requested by user)
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

    # Quantity of dentists for each protected zip code
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

    # Next Contact Date - Calendar picker
    next_contact_date = models.DateField(null=True, blank=True)
    next_contact_time = models.TimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Prospect"
        verbose_name_plural = "Prospects"

    def __str__(self):
        return f"{self.lab_name} - {self.get_status_display()}"

    def get_protected_zip_codes(self):
        """Return list of non-empty protected zip codes"""
        zips = []
        for i in range(1, 11):
            zip_code = getattr(self, f'zip_protect_{i}')
            if zip_code:
                zips.append(zip_code)
        return zips

    def get_protected_zips_with_qty(self):
        """Return list of tuples (zip_code, qty) for non-empty protected zip codes"""
        zips = []
        for i in range(1, 11):
            zip_code = getattr(self, f'zip_protect_{i}')
            qty = getattr(self, f'zip_qty_{i}')
            if zip_code:
                zips.append((zip_code, qty))
        return zips

    def get_service_types_display(self):
        """Return comma-separated list of service types"""
        service_types = self.service_types.all()
        return ', '.join([st.get_service_type_display() for st in service_types])


class ProspectServiceType(models.Model):
    """Service types selected for a prospect (checkbox multiple select)"""

    SERVICE_TYPE_CHOICES = [
        ('crown_bridge', 'Crown and Bridge'),
        ('denture', 'Denture'),
        ('full_service', 'Full Service'),
    ]

    prospect = models.ForeignKey(
        Prospect,
        on_delete=models.CASCADE,
        related_name='service_types'
    )
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES)

    class Meta:
        unique_together = ['prospect', 'service_type']
        verbose_name = "Prospect Service Type"
        verbose_name_plural = "Prospect Service Types"

    def __str__(self):
        return f"{self.prospect.lab_name} - {self.get_service_type_display()}"


class ProspectNote(models.Model):
    """Notes for a prospect with auto-populated date and 500 char limit"""

    prospect = models.ForeignKey(
        Prospect,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    note_text = models.CharField(max_length=500)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prospect_notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Prospect Note"
        verbose_name_plural = "Prospect Notes"

    def __str__(self):
        return f"{self.prospect.lab_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class LeadReferral(models.Model):
    """Created when a caller sends a prospect to Keith"""
    prospect = models.ForeignKey(
        Prospect,
        on_delete=models.CASCADE,
        related_name='lead_referrals'
    )
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referrals_made'
    )
    contact_person = models.CharField(max_length=200, help_text="Person at the lab Keith should ask for")
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    notes = models.TextField(blank=True)
    sms_reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
        verbose_name = "Lead Referral"
        verbose_name_plural = "Lead Referrals"

    def __str__(self):
        return f"{self.prospect.lab_name} → Keith ({self.appointment_date})"
