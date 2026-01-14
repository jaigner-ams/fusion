from django.core.management.base import BaseCommand
from prospects.models import Prospect
import openpyxl


class Command(BaseCommand):
    help = 'Import prospects from fusion.xlsx'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='/var/www/fusion/fusion.xlsx',
            help='Path to Excel file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without saving'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']

        self.stdout.write(f'Reading from: {file_path}')

        wb = openpyxl.load_workbook(file_path)
        sheet = wb.active

        created_count = 0
        skipped_count = 0

        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            lab_name, contact, phone, address, city, state, zip_code, email = row

            # Skip empty rows
            if not lab_name:
                continue

            # Check if prospect already exists
            if Prospect.objects.filter(lab_name=lab_name).exists():
                self.stdout.write(f'  Skipping (exists): {lab_name}')
                skipped_count += 1
                continue

            # Clean up data
            zip_code = str(zip_code) if zip_code else ''
            contact = contact or ''
            address = address or ''
            city = city or ''
            state = state or ''
            phone = phone or ''
            email = email or ''

            if dry_run:
                self.stdout.write(f'  Would create: {lab_name} ({contact})')
            else:
                # Create the prospect with phone and email fields
                Prospect.objects.create(
                    lab_name=lab_name,
                    person_name=contact,
                    address=address.strip(),
                    city=city.strip(),
                    state=state.strip(),
                    zip_code=zip_code.strip(),
                    phone=phone.strip() if isinstance(phone, str) else str(phone),
                    email=email.strip(),
                    status='prospect'
                )

                self.stdout.write(self.style.SUCCESS(f'  Created: {lab_name}'))

            created_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN - Would create {created_count} prospects, skip {skipped_count}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nImported {created_count} prospects, skipped {skipped_count}'))
