import csv
from datetime import datetime

from django.core.management.base import BaseCommand

from register.models import Guardian


class Command(BaseCommand):
    help = 'Export guardian data to a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Optional path (including filename) for the generated CSV file.',
        )

    def handle(self, *args, **options):
        filename = options.get('output') or f'guardians_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        fields = ['first_name', 'last_name', 'profession', 'address', 'email', 'phone_number']
        guardians = Guardian.objects.all()

        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(fields)

            for guardian in guardians:
                writer.writerow([
                    guardian.first_name,
                    guardian.last_name,
                    guardian.profession or '',
                    guardian.address or '',
                    guardian.email or '',
                    guardian.phone_number or '',
                ])

        self.stdout.write(self.style.SUCCESS(f'CSV file "{filename}" created successfully.'))
