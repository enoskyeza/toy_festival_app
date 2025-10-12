import csv
from datetime import datetime

from django.core.management.base import BaseCommand

from register.models import School


class Command(BaseCommand):
    help = 'Export school data to a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Optional path (including filename) for the generated CSV file.',
        )

    def handle(self, *args, **options):
        filename = options.get('output') or f'schools_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        fields = ['name', 'address', 'email', 'phone_number']
        schools = School.objects.all()

        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(fields)

            for school in schools:
                writer.writerow([
                    school.name,
                    school.address or '',
                    school.email or '',
                    school.phone_number or '',
                ])

        self.stdout.write(self.style.SUCCESS(f'CSV file "{filename}" created successfully.'))
