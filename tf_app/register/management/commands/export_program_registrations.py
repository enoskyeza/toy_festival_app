import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from register.models import Program, Registration


class Command(BaseCommand):
    help = "Export registrations for a given program to a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--program-id",
            type=int,
            required=True,
            help="ID of the program whose registrations should be exported.",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Optional path (including filename) for the generated CSV file.",
        )

    def handle(self, *args, **options):
        program_id = options["program_id"]
        output = options.get("output")

        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            raise CommandError(f"Program with id {program_id} does not exist")

        filename = output or f"program_{program_id}_registrations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Define CSV columns
        fields = [
            "registration_id",
            "program_id",
            "program_name",
            "participant_id",
            "participant_first_name",
            "participant_last_name",
            "participant_gender",
            "age_at_registration",
            "category_value",
            "guardian_id",
            "guardian_name",
            "guardian_phone",
            "guardian_email",
            "school_id",
            "school_name",
            "status",
            "amount_due",
            "created_at",
        ]

        # Prefetch related objects to minimize queries
        registrations = (
            Registration.objects
            .select_related("participant", "guardian_at_registration", "school_at_registration", "program")
            .filter(program_id=program_id)
            .order_by("-created_at")
        )

        if not registrations.exists():
            self.stdout.write(self.style.WARNING(f"No registrations found for program id {program_id}."))

        with open(filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(fields)

            for reg in registrations:
                participant = reg.participant
                guardian = reg.guardian_at_registration
                school = reg.school_at_registration

                guardian_name = f"{guardian.first_name} {guardian.last_name}" if guardian else ""

                writer.writerow([
                    reg.id,
                    program.id,
                    program.name,
                    participant.id if participant else "",
                    getattr(participant, "first_name", ""),
                    getattr(participant, "last_name", ""),
                    getattr(participant, "gender", ""),
                    reg.age_at_registration,
                    reg.category_value or "",
                    guardian.id if guardian else "",
                    guardian_name,
                    getattr(guardian, "phone_number", ""),
                    getattr(guardian, "email", ""),
                    school.id if school else "",
                    getattr(school, "name", ""),
                    reg.status,
                    reg.amount_due,
                    reg.created_at.isoformat(),
                ])

        self.stdout.write(self.style.SUCCESS(f"CSV file '{filename}' created successfully for program '{program.name}' (id={program.id})."))
