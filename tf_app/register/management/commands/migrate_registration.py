import uuid
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from register.models import (
    ProgramType,
    Program,
    Contestant,
    Participant,
    Registration,
    Guardian,
    ParticipantGuardian,
)


class Command(BaseCommand):
    help = (
        "Migrate legacy Contestant data into registrations for the Toy making & Innovation Festival program."
    )

    def handle(self, *args, **options):
        # Create or get the ProgramType
        program_type, _ = ProgramType.objects.get_or_create(
            name="Toy making & Innovation Festival",
            defaults={
                'description': (
                    "Annual toy making competition organised by Wokober that involves children in 3 categories "
                    "based on age from 3-17 years. Winners get awards, sponsorship, scholastic materials and cash prizes."
                )
            }
        )

        # Create or get the 2024 Program
        program, _ = Program.objects.get_or_create(
            name="Toy making & Innovation Festival",
            year=2024,
            defaults={
                'type': program_type,
                'start_date': datetime(2024, 12, 15).date(),
                'end_date': datetime(2024, 12, 16).date(),
                'registration_fee': 20000.00,
                'age_min': 3,
                'age_max': 18,
                'capacity': None,
                'requires_ticket': True,
            }
        )

        created_count = 0
        failed = []

        for contestant in Contestant.objects.all():
            with transaction.atomic():
                try:
                    participant = Participant.objects.get(
                        first_name__iexact=contestant.first_name,
                        last_name__iexact=contestant.last_name,
                        age=contestant.age,
                    )
                except Participant.DoesNotExist:
                    failed.append((contestant.id, "No matching participant found"))
                    continue
                except Participant.MultipleObjectsReturned:
                    try:
                        qs = Participant.objects.filter(
                            first_name__iexact=contestant.first_name,
                            last_name__iexact=contestant.last_name,
                            age=contestant.age,
                        ).order_by('id')
                        participant = qs.first()
                        self.stdout.write(self.style.WARNING(
                            f"Multiple participants for {contestant.first_name} {contestant.last_name}. Using ID={participant.id}."
                        ))
                    except Exception as e:
                        failed.append((contestant.id, f"Error selecting from multiple participants: {str(e)}"))
                        continue

                try:
                    primary_link = ParticipantGuardian.objects.filter(
                        participant=participant,
                        is_primary=True
                    ).select_related('guardian').first()
                    guardian = primary_link.guardian if primary_link else participant.guardians.first()

                    defaults = {
                        'guardian_at_registration': guardian,
                        'school_at_registration': participant.current_school,
                        'age_at_registration': contestant.age,
                        'status': (
                            Registration.Status.PAID if contestant.payment_status == 'paid'
                            else Registration.Status.CANCELLED
                        ),
                        'created_at': contestant.created_at,
                    }

                    reg, created = Registration.objects.get_or_create(
                        participant=participant,
                        program=program,
                        defaults=defaults
                    )
                    if created:
                        Registration.objects.filter(pk=reg.pk).update(created_at=contestant.created_at)
                        created_count += 1
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"Skipped existing registration for Participant ID={participant.id}."
                        ))
                except Exception as e:
                    failed.append((contestant.id, f"{str(e)}"))

        self.stdout.write(self.style.SUCCESS(
            f"Created {created_count} new registrations."
        ))

        if failed:
            for cid, reason in failed:
                self.stdout.write(self.style.WARNING(
                    f"Failed to migrate contestant ID={cid}: {reason}"
                ))
