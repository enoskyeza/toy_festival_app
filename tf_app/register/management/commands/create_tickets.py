from django.core.management.base import BaseCommand
from register.models import Contestant, Ticket

class Command(BaseCommand):
    help = "Generate tickets for contestants with payment status as 'paid' and no ticket."

    def handle(self, *args, **kwargs):
        # Fetch all contestants with payment status as 'paid' and no ticket
        eligible_contestants = Contestant.objects.filter(payment_status='paid').exclude(ticket__isnull=False)

        if not eligible_contestants.exists():
            self.stdout.write(self.style.SUCCESS("No eligible contestants found."))
            return

        created_tickets = 0

        for contestant in eligible_contestants:
            try:
                # Create a ticket for the contestant
                ticket = Ticket(participant=contestant)
                ticket.save()
                created_tickets += 1
                self.stdout.write(self.style.SUCCESS(f"Ticket created for {contestant.first_name} {contestant.last_name}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to create ticket for {contestant.first_name} {contestant.last_name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully created {created_tickets} tickets."))
