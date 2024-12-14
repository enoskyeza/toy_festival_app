import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from register.models import Contestant

class Command(BaseCommand):
    help = 'Export paid contestants to a CSV file'

    def handle(self, *args, **kwargs):
        # Define the filename with a timestamp
        filename = f'paid_contestants_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        # Fields to include in the CSV
        fields = ['identifier', 'first_name', 'last_name', 'email', 'age', 'gender', 'school', 'age_category']

        # Filter contestants who have paid
        paid_contestants = Contestant.objects.filter(payment_status=Contestant.PaymentStatus.PAID)

        # Open the file and write to it
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            # Write header row
            writer.writerow(fields)

            # Write contestant rows
            for contestant in paid_contestants:
                writer.writerow([
                    contestant.identifier,
                    contestant.first_name,
                    contestant.last_name,
                    contestant.email,
                    contestant.age,
                    contestant.gender,
                    contestant.school,
                    contestant.age_category,
                ])

        self.stdout.write(self.style.SUCCESS(f'CSV file "{filename}" created successfully.'))


# import csv
# from datetime import datetime
# from django.core.management.base import BaseCommand
# from register.models import Contestant

# class Command(BaseCommand):
#     help = 'Export only the names of paid contestants to a CSV file'

#     def handle(self, *args, **kwargs):
#         # Define the filename with a timestamp
#         filename = f'paid_contestant_names_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

#         # Open the file and write to it
#         with open(filename, mode='w', newline='', encoding='utf-8') as file:
#             writer = csv.writer(file)

#             # Write the header row
#             writer.writerow(['name'])

#             # Filter contestants who have paid and write their names
#             paid_contestants = Contestant.objects.filter(payment_status=Contestant.PaymentStatus.PAID)
#             for contestant in paid_contestants:
#                 full_name = f"{contestant.first_name} {contestant.last_name}"
#                 writer.writerow([full_name])

#         self.stdout.write(self.style.SUCCESS(f'CSV file "{filename}" created successfully.'))




