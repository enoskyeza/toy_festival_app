from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Contestant, Ticket

@receiver(post_save, sender=Contestant)
def create_ticket_for_paid_contestant(sender, instance, created, **kwargs):
    """
    Signal to create a ticket for contestants when payment is marked as 'paid'.
    """
    if instance.payment_status == Contestant.PaymentStatus.PAID:
        # Check if the contestant already has a ticket
        if not hasattr(instance, 'ticket'):
            # Create a ticket for the contestant
            Ticket.objects.create(participant=instance)
