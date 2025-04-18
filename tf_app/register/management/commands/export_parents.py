import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from register.models import Parent

class Command(BaseCommand):
    help = 'Export parent data to a CSV file'

    def handle(self, *args, **kwargs):
        # Define the filename with a timestamp
        filename = f'parents_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        # Fields to include in the CSV
        fields = ['first_name', 'last_name', 'profession', 'address', 'email', 'phone_number']

        # Query all parent records
        parents = Parent.objects.all()

        # Open the file and write to it
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            # Write header row
            writer.writerow(fields)

            # Write parent rows
            for parent in parents:
                writer.writerow([
                    parent.first_name,
                    parent.last_name,
                    parent.profession or '',
                    parent.address,
                    parent.email or '',
                    parent.phone_number,
                ])

        self.stdout.write(self.style.SUCCESS(f'CSV file "{filename}" created successfully.'))
