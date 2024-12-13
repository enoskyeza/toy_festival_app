import csv
from django.core.management.base import BaseCommand
from scores.models import MainCategory, JudgingCriteria

class Command(BaseCommand):
    help = "Load categories and criteria from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file")

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        try:
            with open(csv_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    category_name = row['category'].strip()
                    criteria_name = row['criteria'].strip()

                    # Get or create MainCategory
                    category, created = MainCategory.objects.get_or_create(name=category_name)

                    # Create JudgingCriteria
                    JudgingCriteria.objects.create(
                        category=category,
                        name=criteria_name
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"Added criteria '{criteria_name}' under category '{category_name}'."
                    ))

            self.stdout.write(self.style.SUCCESS("All data loaded successfully!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error: {e}"))
