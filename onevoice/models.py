from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class OVClient(models.Model):
    PROGRAM_TYPE_CHOICES = [
        ('onevoice', 'One Voice'),
        ('geofencing', 'Fusion Geofencing'),
    ]
    TIER_CHOICES = [
        ('onevoice_295', 'One Voice $295/mo'),
        ('fusion_addon', 'Fusion with One Voice Add-on'),
    ]
    CALL_SESSION_MODE_CHOICES = [
        (1, 'Mode 1 — Full Session'),
        (2, 'Mode 2 — One Appointment at a Time'),
    ]
    STATUS_CHOICES = [
        ('onboarding', 'Onboarding'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='ov_client_profile',
        limit_choices_to={'roles__role': 'ov_client'},
        null=True, blank=True,
    )
    prospect = models.OneToOneField(
        'prospects.Prospect', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ov_client',
    )
    program_type = models.CharField(max_length=20, choices=PROGRAM_TYPE_CHOICES, default='onevoice')
    lab_name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=200, blank=True)
    membership_tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='onevoice_295')
    call_session_mode = models.IntegerField(choices=CALL_SESSION_MODE_CHOICES, default=1)
    mailing_list_size = models.IntegerField(default=100, help_text='Included dentists in monthly fee')
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='onboarding')
    internal_notes = models.TextField(blank=True, help_text='Visible to Admin and Super-Admin only')
    assigned_csrs = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='ov_assigned_clients',
        limit_choices_to={'roles__role': 'csr'},
    )
    onboarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['lab_name']
        verbose_name = 'One Voice Client'

    def __str__(self):
        return self.lab_name

    def get_active_dentist_count(self):
        return self.dentists.exclude(status='removed').count()

    def get_overage_count(self):
        active = self.get_active_dentist_count()
        return max(0, active - self.mailing_list_size)

    def get_overage_amount(self):
        return self.get_overage_count() * 1.50


class OVAgreement(models.Model):
    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='agreements')
    agreement_text = models.TextField(help_text='Full agreement text at time of signing')
    signature_name = models.CharField(max_length=200, blank=True)
    signature_date = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signed = models.BooleanField(default=False)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ov_agreements_sent',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Agreement for {self.client} — {"Signed" if self.signed else "Unsigned"}'

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = OVAgreement.objects.get(pk=self.pk)
                if old.signed:
                    raise ValueError('Signed agreements cannot be modified.')
            except OVAgreement.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class OVListImport(models.Model):
    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='list_imports')
    file_name = models.CharField(max_length=255)
    total_rows = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    filtered_count = models.IntegerField(default=0, help_text='Removed by specialty filter')
    duplicate_count = models.IntegerField(default=0)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
    )
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-imported_at']

    def __str__(self):
        return f'{self.file_name} — {self.imported_count} imported'


class OVDentist(models.Model):
    STATUS_CHOICES = [
        ('never_called', 'Never Called'),
        ('no_answer', 'No Answer'),
        ('email_captured', 'Email Captured'),
        ('called_no_email', 'Called / No Email'),
        ('appointment', 'Appointment Booked'),
        ('do_not_contact', 'Do Not Contact'),
        ('removed', 'Removed'),
    ]
    SPECIALTY_CHOICES = [
        ('gp', 'General Practice'),
        ('prostho', 'Prosthodontist'),
        ('endo', 'Endodontist'),
        ('ortho', 'Orthodontist'),
        ('oralsurg', 'Oral Surgeon'),
        ('perio', 'Periodontist'),
        ('pedo', 'Pediatric Dentist'),
        ('other', 'Other'),
    ]

    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='dentists')
    assigned_csr = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ov_assigned_dentists',
        limit_choices_to={'roles__role': 'csr'},
    )
    list_import = models.ForeignKey(
        OVListImport, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='dentists',
    )

    # Contact info from Data Axle CSV
    name = models.CharField(max_length=200)
    practice_name = models.CharField(max_length=300, blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    office_manager = models.CharField(max_length=200, blank=True)
    specialty = models.CharField(max_length=20, choices=SPECIALTY_CHOICES, default='gp')
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(max_length=200, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='never_called')
    callback_flag = models.BooleanField(default=False)
    callback_date = models.DateField(null=True, blank=True)
    callback_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # Record locking
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ov_locked_dentists',
    )
    locked_at = models.DateTimeField(null=True, blank=True)

    # Client correction/removal requests
    correction_requested = models.BooleanField(default=False)
    correction_notes = models.TextField(blank=True)
    removal_flagged = models.BooleanField(default=False)

    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.practice_name})' if self.practice_name else self.name

    def is_locked(self):
        if not self.locked_by or not self.locked_at:
            return False
        return (timezone.now() - self.locked_at) < timedelta(minutes=5)

    def acquire_lock(self, user):
        if self.is_locked() and self.locked_by != user:
            return False
        self.locked_by = user
        self.locked_at = timezone.now()
        self.save(update_fields=['locked_by', 'locked_at'])
        return True

    def release_lock(self):
        self.locked_by = None
        self.locked_at = None
        self.save(update_fields=['locked_by', 'locked_at'])

    def get_status_color(self):
        colors = {
            'never_called': '#9ca3af',
            'no_answer': '#eab308',
            'email_captured': '#3b82f6',
            'called_no_email': '#f97316',
            'appointment': '#22c55e',
            'do_not_contact': '#ef4444',
            'removed': '#9ca3af',
        }
        return colors.get(self.status, '#9ca3af')


class OVDentistStatusHistory(models.Model):
    dentist = models.ForeignKey(OVDentist, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.dentist} — {self.old_status} -> {self.new_status}'


class OVCallRecord(models.Model):
    OUTCOME_CHOICES = [
        ('confirmed_active', 'Confirmed Active'),
        ('no_answer', 'No Answer'),
        ('spoke_callback', 'Callback'),
        ('spoke_email_captured', 'Email Captured'),
        ('spoke_appointment', 'Appointment Booked'),
        ('do_not_contact', 'Do Not Contact'),
        ('out_of_business', 'Out of Business'),
        ('address_changed', 'Address Changed'),
        ('voicemail', 'Left Voicemail'),
        ('spoke_not_interested', 'Not Interested'),
        ('wrong_number', 'Wrong Number'),
        ('disconnected', 'Disconnected'),
        ('other', 'Other'),
    ]

    dentist = models.ForeignKey(OVDentist, on_delete=models.CASCADE, related_name='call_records')
    csr = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ov_call_records',
    )
    session = models.ForeignKey(
        'OVCallSession', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='call_records',
    )
    outcome = models.CharField(max_length=30, choices=OUTCOME_CHOICES)
    notes = models.TextField(blank=True, max_length=1000)
    email_captured = models.EmailField(blank=True)
    callback_date = models.DateField(null=True, blank=True)
    callback_time = models.TimeField(null=True, blank=True)
    called_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-called_at']

    def __str__(self):
        return f'{self.dentist} — {self.get_outcome_display()} by {self.csr}'


class OVAppointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    CASE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('won', 'Won'),
        ('not_yet', 'Not Yet'),
        ('lost', 'Lost'),
    ]

    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='appointments')
    dentist = models.ForeignKey(OVDentist, on_delete=models.CASCADE, related_name='appointments')
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='ov_booked_appointments',
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    case_status = models.CharField(max_length=20, choices=CASE_STATUS_CHOICES, default='pending')
    client_notes = models.TextField(blank=True)
    followup_date = models.DateField(null=True, blank=True, help_text='Auto-set to 1 week after appointment')
    followup_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date', 'appointment_time']
        constraints = [
            models.UniqueConstraint(
                fields=['client', 'appointment_date', 'appointment_time'],
                name='unique_client_appointment_slot',
            )
        ]

    def __str__(self):
        return f'{self.dentist} — {self.appointment_date} {self.appointment_time}'

    def save(self, *args, **kwargs):
        if not self.followup_date and self.appointment_date:
            self.followup_date = self.appointment_date + timedelta(days=7)
        super().save(*args, **kwargs)


class OVClientAvailability(models.Model):
    TYPE_CHOICES = [
        ('recurring', 'Recurring Weekly'),
        ('specific', 'Specific Date'),
    ]
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='availability')
    availability_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    day_of_week = models.IntegerField(choices=DAY_CHOICES, null=True, blank=True)
    specific_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Client availabilities'

    def __str__(self):
        if self.availability_type == 'recurring':
            return f'{self.client} — {self.get_day_of_week_display()} {self.start_time}-{self.end_time}'
        return f'{self.client} — {self.specific_date} {self.start_time}-{self.end_time}'


class OVCallSession(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='call_sessions')
    csr = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='ov_call_sessions',
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_date']

    def __str__(self):
        return f'{self.client} — {self.scheduled_date} ({self.get_status_display()})'


class OVPostcardDesign(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Client Approval'),
        ('approved', 'Approved'),
        ('locked', 'Locked'),
    ]

    name = models.CharField(max_length=200)
    template_image = models.ImageField(upload_to='onevoice/postcard_templates/', null=True, blank=True)
    is_master_template = models.BooleanField(default=False, help_text='Part of the design library')
    client = models.ForeignKey(
        OVClient, on_delete=models.CASCADE,
        null=True, blank=True, related_name='postcard_designs',
    )
    customized_image = models.ImageField(upload_to='onevoice/postcard_customized/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by_client = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = OVPostcardDesign.objects.get(pk=self.pk)
                if old.locked and self.locked:
                    raise ValueError('Locked designs cannot be modified. Admin unlock required.')
            except OVPostcardDesign.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class OVPostcardComment(models.Model):
    design = models.ForeignKey(OVPostcardDesign, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment on {self.design} by {self.user}'


class OVPostcardInventory(models.Model):
    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='inventory')
    design = models.ForeignKey(OVPostcardDesign, on_delete=models.CASCADE, related_name='inventory_records')
    quantity_on_hand = models.IntegerField(default=0)
    reorder_threshold = models.IntegerField(default=50)
    last_restocked = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Postcard inventories'

    def __str__(self):
        return f'{self.client} — {self.design} ({self.quantity_on_hand} on hand)'

    def is_below_threshold(self):
        return self.quantity_on_hand < self.reorder_threshold


class OVMailingSchedule(models.Model):
    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='mailing_schedule')
    scheduled_date = models.DateField()
    description = models.CharField(max_length=300, blank=True)
    completed = models.BooleanField(default=False)
    postcard_design = models.ForeignKey(
        OVPostcardDesign, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_date']

    def __str__(self):
        return f'{self.client} — Mailing {self.scheduled_date}'


class OVNotification(models.Model):
    TYPE_CHOICES = [
        ('welcome', 'Client Onboarded'),
        ('agreement_sent', 'Agreement Sent'),
        ('list_ready', 'List Ready'),
        ('appointment_booked', 'Appointment Booked'),
        ('appointment_passed', 'Appointment Passed'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('followup_reminder', 'Follow-up Reminder'),
        ('session_done', 'CSR Session Done'),
        ('session_started', 'Call Session Started'),
        ('inventory_low', 'Inventory Low'),
        ('correction_request', 'Correction Request'),
        ('removal_request', 'Removal Request'),
    ]

    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='ov_notifications',
    )
    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=300)
    message = models.TextField()
    read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_notification_type_display()} — {self.title}'


class OVPrintOrder(models.Model):
    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='print_orders')
    design = models.ForeignKey(OVPostcardDesign, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.CharField(max_length=200, blank=True)
    confirmation_number = models.CharField(max_length=100, blank=True)
    mail_date = models.DateField(null=True, blank=True)
    expected_delivery = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Print order for {self.client} — {self.vendor or "TBD"}'


class OVBillingSnapshot(models.Model):
    client = models.ForeignKey(OVClient, on_delete=models.CASCADE, related_name='billing_snapshots')
    snapshot_date = models.DateField()
    active_list_size = models.IntegerField()
    included_size = models.IntegerField(help_text='From client mailing_list_size')
    overage_count = models.IntegerField(default=0)
    overage_rate = models.DecimalField(max_digits=6, decimal_places=2, default=1.50)
    overage_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    flagged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-snapshot_date']

    def __str__(self):
        return f'{self.client} — {self.snapshot_date} billing snapshot'
