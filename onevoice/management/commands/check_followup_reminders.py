from django.core.management.base import BaseCommand
from django.utils import timezone
from onevoice.models import OVAppointment
from onevoice.notifications import send_ov_notification


class Command(BaseCommand):
    help = 'Send 1-week post-appointment follow-up reminders to clients'

    def handle(self, *args, **options):
        today = timezone.now().date()

        # Find appointments where followup_date is today
        followups = OVAppointment.objects.filter(
            followup_date=today,
            case_status='pending',
        ).select_related('client', 'dentist')

        for appt in followups:
            if appt.client.user:
                send_ov_notification(
                    'followup_reminder', appt.client.user, client=appt.client,
                    title=f'Follow-up Reminder: {appt.dentist.name}',
                    message=f'It\'s been one week since your appointment with {appt.dentist.name}. Follow up with them to discuss next steps.',
                )
                self.stdout.write(f'Follow-up reminder sent: {appt.client.lab_name} - {appt.dentist.name}')

        self.stdout.write(self.style.SUCCESS(f'Follow-up check complete. {followups.count()} reminders sent.'))
