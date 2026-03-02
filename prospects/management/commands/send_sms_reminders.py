from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from prospects.models import LeadReferral


class Command(BaseCommand):
    help = 'Send SMS reminders to Keith for tomorrow\'s lead appointments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview SMS without sending'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tomorrow = date.today() + timedelta(days=1)

        referrals = LeadReferral.objects.filter(
            appointment_date=tomorrow,
            sms_reminder_sent=False,
        ).select_related('prospect')

        if not referrals.exists():
            self.stdout.write('No appointments for tomorrow. No SMS to send.')
            return

        # Build summary message
        lines = [f"AMS Fusion - {referrals.count()} appointment(s) tomorrow ({tomorrow.strftime('%m/%d/%Y')}):"]
        for r in referrals:
            lines.append(
                f"- {r.prospect.lab_name} at {r.appointment_time.strftime('%I:%M %p')}, "
                f"ask for {r.contact_person}"
            )
        message = '\n'.join(lines)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - Would send SMS:'))
            self.stdout.write(message)
            return

        # Check Twilio settings
        if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN,
                     settings.TWILIO_FROM_NUMBER, settings.TWILIO_KEITH_NUMBER]):
            self.stderr.write(self.style.ERROR(
                'Twilio settings not configured. Set TWILIO_ACCOUNT_SID, '
                'TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, and TWILIO_KEITH_NUMBER in settings.py'
            ))
            return

        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

            sms = client.messages.create(
                body=message,
                from_=settings.TWILIO_FROM_NUMBER,
                to=settings.TWILIO_KEITH_NUMBER,
            )

            # Mark reminders as sent
            referrals.update(sms_reminder_sent=True)

            self.stdout.write(self.style.SUCCESS(
                f'SMS sent successfully (SID: {sms.sid}). '
                f'Reminded about {referrals.count()} appointment(s).'
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to send SMS: {str(e)}'))
