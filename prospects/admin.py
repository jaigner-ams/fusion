from django.contrib import admin
from .models import Prospect, ProspectNote, ProspectServiceType, Mailer, LeadReferral


class ProspectNoteInline(admin.TabularInline):
    model = ProspectNote
    extra = 1
    readonly_fields = ['created_at']


class ProspectServiceTypeInline(admin.TabularInline):
    model = ProspectServiceType
    extra = 1


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = ['lab_name', 'person_name', 'status', 'next_contact_date', 'created_at']
    list_filter = ['status', 'has_mill', 'next_contact_date']
    search_fields = ['lab_name', 'person_name', 'city', 'state']
    inlines = [ProspectServiceTypeInline, ProspectNoteInline]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Status', {
            'fields': ('status', 'mailer')
        }),
        ('Contact Information', {
            'fields': ('lab_name', 'person_name', 'address', 'city', 'state', 'zip_code')
        }),
        ('Business Details', {
            'fields': ('monthly_fee', 'has_mill', 'dentists_requested')
        }),
        ('Protected Zip Codes', {
            'fields': (
                ('zip_protect_1', 'zip_protect_2', 'zip_protect_3', 'zip_protect_4', 'zip_protect_5'),
                ('zip_protect_6', 'zip_protect_7', 'zip_protect_8', 'zip_protect_9', 'zip_protect_10'),
            ),
            'classes': ('collapse',)
        }),
        ('Scheduling', {
            'fields': ('next_contact_date',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ProspectNote)
class ProspectNoteAdmin(admin.ModelAdmin):
    list_display = ['prospect', 'note_text', 'created_at']
    list_filter = ['created_at']
    search_fields = ['prospect__lab_name', 'note_text']
    readonly_fields = ['created_at']


@admin.register(Mailer)
class MailerAdmin(admin.ModelAdmin):
    list_display = ['date', 'description', 'prospect_count', 'created_at']
    list_filter = ['date']
    search_fields = ['description']
    readonly_fields = ['created_at']


@admin.register(LeadReferral)
class LeadReferralAdmin(admin.ModelAdmin):
    list_display = ['prospect', 'contact_person', 'appointment_date', 'appointment_time', 'referred_by', 'sms_reminder_sent']
    list_filter = ['appointment_date', 'sms_reminder_sent']
    search_fields = ['prospect__lab_name', 'contact_person']
    readonly_fields = ['created_at']
