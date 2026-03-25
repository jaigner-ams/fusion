from django.contrib import admin
from .models import (
    OVClient, OVAgreement, OVDentist, OVDentistStatusHistory,
    OVCallRecord, OVAppointment, OVClientAvailability, OVCallSession,
    OVPostcardDesign, OVPostcardComment, OVPostcardInventory,
    OVMailingSchedule, OVListImport, OVNotification, OVPrintOrder,
    OVBillingSnapshot,
)


@admin.register(OVClient)
class OVClientAdmin(admin.ModelAdmin):
    list_display = ('lab_name', 'owner_name', 'status', 'membership_tier', 'call_session_mode', 'created_at')
    list_filter = ('status', 'membership_tier', 'program_type')
    search_fields = ('lab_name', 'owner_name', 'email')


@admin.register(OVAgreement)
class OVAgreementAdmin(admin.ModelAdmin):
    list_display = ('client', 'signed', 'signature_name', 'signature_date', 'created_at')
    list_filter = ('signed',)
    readonly_fields = ('signature_name', 'signature_date', 'ip_address', 'agreement_text')


@admin.register(OVDentist)
class OVDentistAdmin(admin.ModelAdmin):
    list_display = ('name', 'practice_name', 'client', 'status', 'specialty', 'assigned_csr')
    list_filter = ('status', 'specialty', 'client')
    search_fields = ('name', 'practice_name', 'email')


@admin.register(OVCallRecord)
class OVCallRecordAdmin(admin.ModelAdmin):
    list_display = ('dentist', 'csr', 'outcome', 'called_at')
    list_filter = ('outcome', 'csr')


@admin.register(OVAppointment)
class OVAppointmentAdmin(admin.ModelAdmin):
    list_display = ('client', 'dentist', 'appointment_date', 'appointment_time', 'status', 'case_status')
    list_filter = ('status', 'case_status')


@admin.register(OVCallSession)
class OVCallSessionAdmin(admin.ModelAdmin):
    list_display = ('client', 'csr', 'scheduled_date', 'status')
    list_filter = ('status',)


@admin.register(OVPostcardDesign)
class OVPostcardDesignAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'is_master_template', 'status', 'locked')
    list_filter = ('status', 'is_master_template', 'locked')


@admin.register(OVNotification)
class OVNotificationAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'recipient', 'title', 'read', 'email_sent', 'created_at')
    list_filter = ('notification_type', 'read', 'email_sent')


admin.site.register(OVDentistStatusHistory)
admin.site.register(OVClientAvailability)
admin.site.register(OVPostcardComment)
admin.site.register(OVPostcardInventory)
admin.site.register(OVMailingSchedule)
admin.site.register(OVListImport)
admin.site.register(OVPrintOrder)
admin.site.register(OVBillingSnapshot)
