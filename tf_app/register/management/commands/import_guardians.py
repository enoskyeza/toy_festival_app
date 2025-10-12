import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from register.models import Guardian


class Command(BaseCommand):
    help = 'Import guardian data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            required=True,
            help='Path to the CSV file containing guardian data.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse the CSV and report changes without writing to the database.',
        )

    def handle(self, *args, **options):
        csv_path = Path(options['file']).expanduser().resolve()
        dry_run = options['dry_run']

        if not csv_path.exists():
            raise CommandError(f'File "{csv_path}" does not exist.')

        created = 0
        updated = 0

        with csv_path.open(mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            required_columns = {'first_name', 'last_name'}
            missing = required_columns - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f'Missing required columns: {", ".join(sorted(missing))}')

            for row in reader:
                data = {
                    'first_name': row.get('first_name', '').strip(),
                    'last_name': row.get('last_name', '').strip(),
                    'profession': row.get('profession', '').strip() or None,
                    'address': row.get('address', '').strip() or '',
                    'email': row.get('email', '').strip() or None,
                    'phone_number': row.get('phone_number', '').strip() or '',
                }

                lookup = {}
                if data['phone_number']:
                    lookup['phone_number'] = data['phone_number']
                elif data['email']:
                    lookup['email'] = data['email']
                else:
                    lookup = {
                        'first_name': data['first_name'],
                        'last_name': data['last_name'],
                    }

                if dry_run:
                    if Guardian.objects.filter(**lookup).exists():
                        updated += 1
                    else:
                        created += 1
                    continue

                guardian, created_flag = Guardian.objects.update_or_create(
                    defaults=data,
                    **lookup,
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'Dry-run complete. Would create {created} and update {updated} guardians.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Import complete. Created {created} and updated {updated} guardians.'))
