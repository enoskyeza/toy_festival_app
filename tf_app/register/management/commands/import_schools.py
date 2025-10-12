import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from register.models import School


class Command(BaseCommand):
    help = 'Import school data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            required=True,
            help='Path to the CSV file containing school data.',
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
            required_columns = {'name'}
            missing = required_columns - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f'Missing required columns: {", ".join(sorted(missing))}')

            for row in reader:
                data = {
                    'name': row.get('name', '').strip(),
                    'address': row.get('address', '').strip() or '',
                    'email': row.get('email', '').strip() or None,
                    'phone_number': row.get('phone_number', '').strip() or None,
                }

                lookup = {'name': data['name']}

                if dry_run:
                    if School.objects.filter(**lookup).exists():
                        updated += 1
                    else:
                        created += 1
                    continue

                school, created_flag = School.objects.update_or_create(
                    defaults=data,
                    **lookup,
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f'Dry-run complete. Would create {created} and update {updated} schools.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Import complete. Created {created} and updated {updated} schools.'))
