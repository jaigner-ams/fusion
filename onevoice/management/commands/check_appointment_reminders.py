from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from mgmt.models import CustomUser
from onevoice.models import OVClient, OVAppointment, OVCallSession
from onevoice.notifications import send_ov_notification


class Command(BaseCommand):
    help = 'Check for Mode 2 resume alerts and upcoming appointment reminders'

    def handle(self, *args, **options):
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)

        # Mode 2: Check if latest appointment has passed and session should resume
        mode2_clients = OVClient.objects.filter(status='active', call_session_mode=2)
        for client in mode2_clients:
            latest_appt = OVAppointment.objects.filter(
                client=client, status='scheduled',
            ).order_by('-appointment_date').first()

            if latest_appt and latest_appt.appointment_date < today:
                # Appointment has passed, alert admin and CSRs to resume
                admins = CustomUser.objects.filter(roles__role__in=['ov_admin', 'superadmin']).distinct()
                for admin in admins:
                    send_ov_notification(
                        'appointment_passed', admin, client=client,
                        title=f'Resume Calls: {client.lab_name}',
                        message=f'Mode 2 appointment with {latest_appt.dentist.name} has passed. Resume call session.',
                    )
                for csr in client.assigned_csrs.all():
                    send_ov_notification(
                        'appointment_passed', csr, client=client,
                        title=f'Resume Calls: {client.lab_name}',
                        message=f'Appointment has passed. You may resume calling.',
                    )
                # Mark appointment as completed
                latest_appt.status = 'completed'
                latest_appt.save(update_fields=['status'])

                self.stdout.write(f'Mode 2 resume alert sent for {client.lab_name}')

        # Upcoming appointment reminders (tomorrow)
        tomorrow_appts = OVAppointment.objects.filter(
            appointment_date=tomorrow, status='scheduled',
        ).select_related('client', 'dentist')

        for appt in tomorrow_appts:
            if appt.client.user:
                send_ov_notification(
                    'appointment_reminder', appt.client.user, client=appt.client,
                    title=f'Appointment Tomorrow: {appt.dentist.name}',
                    message=f'Reminder: You have an appointment with {appt.dentist.name} ({appt.dentist.practice_name}) tomorrow at {appt.appointment_time.strftime("%I:%M %p")}.',
                )
                self.stdout.write(f'Reminder sent for {appt.client.lab_name} - {appt.dentist.name}')

        self.stdout.write(self.style.SUCCESS('Appointment check complete.'))
