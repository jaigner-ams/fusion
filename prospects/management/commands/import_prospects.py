import csv
from datetime import date
from django.core.management.base import BaseCommand
from prospects.models import Prospect, Mailer
import openpyxl


class Command(BaseCommand):
    help = 'Import prospects from Excel (.xlsx) or CSV (.csv) files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/var/www/fusion/fusion.xlsx',
            help='Path to Excel or CSV file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without saving'
        )
        parser.add_argument(
            '--mailer-date',
            type=str,
            default='',
            help='Mailer date (YYYY-MM-DD). Creates a Mailer batch and links prospects. Defaults to today.'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='prospect',
            help='Status to assign to imported prospects (default: prospect). Use "mailed" for mailer imports.'
        )

    def read_xlsx(self, file_path):
        """Read rows from Excel file (old format: lab_name, contact, phone, address, city, state, zip, email)"""
        wb = openpyxl.load_workbook(file_path)
        sheet = wb.active
        rows = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            lab_name, contact, phone, address, city, state, zip_code, email = row
            rows.append({
                'lab_name': lab_name or '',
                'person_name': contact or '',
                'phone': phone or '',
                'address': address or '',
                'city': city or '',
                'state': state or '',
                'zip_code': str(zip_code) if zip_code else '',
                'email': email or '',
            })
        return rows

    def read_csv(self, file_path):
        """Read rows from CSV file (labs.csv format with header row)"""
        rows = []
        # Try UTF-8 first, fall back to latin-1
        for encoding in ['utf-8-sig', 'latin-1']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()
                break
            except UnicodeDecodeError:
                continue
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            for row in reader:
                first = (row.get('First Name') or '').strip()
                last = (row.get('Last Name') or '').strip()
                person_name = f"{first} {last}".strip()

                rows.append({
                    'lab_name': (row.get('Practice') or '').strip(),
                    'person_name': person_name,
                    'phone': (row.get('Phone') or '').strip(),
                    'address': (row.get('Address') or '').strip(),
                    'city': (row.get('City') or '').strip(),
                    'state': (row.get('ST') or '').strip(),
                    'zip_code': str(row.get('Zip') or '').strip(),
                    'email': (row.get('email 1') or '').strip(),
                })
        return rows

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        mailer_date_str = options['mailer_date']
        import_status = options['status']

        self.stdout.write(f'Reading from: {file_path}')

        # Parse mailer date
        if mailer_date_str:
            try:
                mailer_date = date.fromisoformat(mailer_date_str)
            except ValueError:
                self.stderr.write(self.style.ERROR(f'Invalid date format: {mailer_date_str}. Use YYYY-MM-DD.'))
                return
        else:
            mailer_date = date.today()

        # Read file based on extension
        if file_path.lower().endswith('.csv'):
            rows = self.read_csv(file_path)
        else:
            rows = self.read_xlsx(file_path)

        self.stdout.write(f'Found {len(rows)} rows in file')

        created_count = 0
        skipped_count = 0

        for row_data in rows:
            lab_name = row_data['lab_name']

            # Skip empty rows
            if not lab_name:
                continue

            # Check if prospect already exists
            if Prospect.objects.filter(lab_name=lab_name).exists():
                self.stdout.write(f'  Skipping (exists): {lab_name}')
                skipped_count += 1
                continue

            phone = row_data['phone']
            if not isinstance(phone, str):
                phone = str(phone)

            if dry_run:
                self.stdout.write(f'  Would create: {lab_name} ({row_data["person_name"]})')
            else:
                Prospect.objects.create(
                    lab_name=lab_name,
                    person_name=row_data['person_name'],
                    address=row_data['address'],
                    city=row_data['city'],
                    state=row_data['state'],
                    zip_code=row_data['zip_code'],
                    phone=phone,
                    email=row_data['email'],
                    status=import_status,
                )
                self.stdout.write(self.style.SUCCESS(f'  Created: {lab_name}'))

            created_count += 1

        # Create Mailer batch if prospects were imported and not a dry run
        if not dry_run and created_count > 0:
            mailer = Mailer.objects.create(
                date=mailer_date,
                description=f'Import from {file_path.split("/")[-1]}',
                prospect_count=created_count,
            )
            # Link all just-created prospects that have no mailer yet
            Prospect.objects.filter(
                status=import_status,
                mailer__isnull=True
            ).update(mailer=mailer)
            self.stdout.write(self.style.SUCCESS(f'Created Mailer batch: {mailer}'))

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN - Would create {created_count} prospects, skip {skipped_count}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nImported {created_count} prospects, skipped {skipped_count}'))
