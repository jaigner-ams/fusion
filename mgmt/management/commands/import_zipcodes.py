"""
Management command to import US zip codes from GeoNames data.

Usage:
    python manage.py import_zipcodes /path/to/US.txt

Download the data from: http://download.geonames.org/export/zip/US.zip
"""

from django.core.management.base import BaseCommand
from mgmt.models import ZipCode


class Command(BaseCommand):
    help = 'Import US zip codes from GeoNames data file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the US.txt file from GeoNames'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing zip codes before importing'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']

        if options['clear']:
            self.stdout.write('Clearing existing zip codes...')
            ZipCode.objects.all().delete()

        self.stdout.write(f'Reading zip codes from {file_path}...')

        # GeoNames US.txt format (tab-separated):
        # 0: country code (US)
        # 1: postal code
        # 2: place name (city)
        # 3: state name
        # 4: state code
        # 5: county name
        # 6: county code
        # 7: (empty)
        # 8: (empty)
        # 9: latitude
        # 10: longitude
        # 11: accuracy

        zip_codes = []
        updated = 0
        created = 0
        errors = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    parts = line.strip().split('\t')
                    if len(parts) < 11:
                        continue

                    zip_code = parts[1].strip()
                    city = parts[2].strip()
                    state = parts[3].strip()
                    state_abbr = parts[4].strip()
                    latitude = float(parts[9])
                    longitude = float(parts[10])

                    # Skip invalid entries
                    if not zip_code or not latitude or not longitude:
                        continue

                    zip_codes.append(ZipCode(
                        zip_code=zip_code,
                        city=city,
                        state=state,
                        state_abbr=state_abbr,
                        latitude=latitude,
                        longitude=longitude
                    ))

                    # Batch insert every 1000 records
                    if len(zip_codes) >= 1000:
                        self._bulk_upsert(zip_codes)
                        created += len(zip_codes)
                        zip_codes = []
                        self.stdout.write(f'  Processed {line_num} lines...')

                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        self.stderr.write(f'Error on line {line_num}: {e}')

        # Insert remaining records
        if zip_codes:
            self._bulk_upsert(zip_codes)
            created += len(zip_codes)

        total = ZipCode.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Import complete! {total} zip codes in database. {errors} errors.'
        ))

    def _bulk_upsert(self, zip_codes):
        """Bulk insert zip codes, ignoring duplicates."""
        ZipCode.objects.bulk_create(
            zip_codes,
            ignore_conflicts=True
        )
