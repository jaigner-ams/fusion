import datetime
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from prospects.models import ProspectNote
from mgmt.models import CustomUser


class Command(BaseCommand):
    help = 'Send daily caller activity summary email to Keith'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to report on (YYYY-MM-DD). Defaults to yesterday.',
        )
        parser.add_argument(
            '--to',
            type=str,
            default='keith@americasmiles.com',
            help='Email recipient. Defaults to keith@americasmiles.com',
        )

    def handle(self, *args, **options):
        # Determine report date
        if options['date']:
            report_date = datetime.date.fromisoformat(options['date'])
        else:
            report_date = timezone.now().date()

        recipient = options['to']

        # Build timezone-aware date range
        day_start = timezone.make_aware(datetime.datetime.combine(report_date, datetime.time.min))
        day_end = timezone.make_aware(datetime.datetime.combine(report_date, datetime.time.max))

        # Get all caller users
        callers = CustomUser.objects.filter(user_type='caller')

        if not callers.exists():
            self.stdout.write('No caller users found. Skipping.')
            return

        # Build report
        report_lines = []
        total_notes = 0
        total_prospects = 0

        for caller in callers:
            notes = ProspectNote.objects.filter(
                created_by=caller,
                created_at__gte=day_start,
                created_at__lte=day_end,
            ).select_related('prospect').order_by('created_at')

            note_count = notes.count()
            prospects_touched = notes.values('prospect').distinct().count()
            total_notes += note_count
            total_prospects += prospects_touched

            caller_name = caller.get_full_name() or caller.username

            report_lines.append(f'--- {caller_name} ---')
            report_lines.append(f'Notes taken: {note_count}')
            report_lines.append(f'Prospects touched: {prospects_touched}')
            report_lines.append('')

            if notes.exists():
                for note in notes:
                    local_time = timezone.localtime(note.created_at)
                    time_str = local_time.strftime('%I:%M %p')
                    report_lines.append(f'  {time_str} | {note.prospect.lab_name}')
                    report_lines.append(f'           {note.note_text}')
                    report_lines.append('')
            else:
                report_lines.append('  No activity')
                report_lines.append('')

        # Build email
        date_str = report_date.strftime('%A, %B %d, %Y')
        subject = f'AMS Caller Activity Report - {report_date.strftime("%m/%d/%Y")}'

        body = f'Caller Activity Report for {date_str}\n'
        body += '=' * 50 + '\n\n'
        body += f'Total notes: {total_notes}\n'
        body += f'Total prospects touched: {total_prospects}\n\n'
        body += '\n'.join(report_lines)
        body += '\n\n--\n'
        body += f'View full details: {settings.SITE_URL}/prospects/caller-activity/?date={report_date.isoformat()}\n'

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(
                f'Activity report for {report_date} sent to {recipient} '
                f'({total_notes} notes, {total_prospects} prospects)'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {e}'))
