"""
Management command to create Toy Festival rubrics for all age categories.

Usage:
    python manage.py create_toy_festival_rubrics <program_id>
    
Example:
    python manage.py create_toy_festival_rubrics 1
"""

from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from scores.models import Rubric, RubricCriteria, RubricCategory
from register.models import Program


# Rubric definitions for each age category
# Keys should match the category_value in Registration model exactly
RUBRIC_DEFINITIONS = {
    "3-7": {
        "display_name": "Ages 3-7",
        "total_points": 100,
        "criteria": [
            {
                "name": "Creativity & Originality",
                "description": "Imagination & uniqueness",
                "max_score": 30,
                "weight": Decimal("0.30"),
                "order": 1,
            },
            {
                "name": "Functionality / Play Value",
                "description": "Suitable and playable",
                "max_score": 25,
                "weight": Decimal("0.25"),
                "order": 2,
            },
            {
                "name": "Craftsmanship",
                "description": "Neatness & effort",
                "max_score": 20,
                "weight": Decimal("0.20"),
                "order": 3,
            },
            {
                "name": "Effort & Participation",
                "description": "Enthusiasm & involvement",
                "max_score": 25,
                "weight": Decimal("0.25"),
                "order": 4,
            },
        ],
    },
    "8-12": {
        "display_name": "Ages 8-12",
        "total_points": 100,
        "criteria": [
            {
                "name": "Creativity & Originality",
                "description": "Unique thinking",
                "max_score": 25,
                "weight": Decimal("0.25"),
                "order": 1,
            },
            {
                "name": "Design & Functionality",
                "description": "Usability, safety",
                "max_score": 20,
                "weight": Decimal("0.20"),
                "order": 2,
            },
            {
                "name": "Exploration",
                "description": "Discovery",
                "max_score": 20,
                "weight": Decimal("0.20"),
                "order": 3,
            },
            {
                "name": "Craftsmanship",
                "description": "Build quality",
                "max_score": 15,
                "weight": Decimal("0.15"),
                "order": 4,
            },
            {
                "name": "Presentation",
                "description": "Clarity in explanation",
                "max_score": 10,
                "weight": Decimal("0.10"),
                "order": 5,
            },
            {
                "name": "Impact & Relevance",
                "description": "Learning/social value",
                "max_score": 10,
                "weight": Decimal("0.10"),
                "order": 6,
            },
        ],
    },
    "13-17": {
        "display_name": "Ages 13-17",
        "total_points": 100,
        "criteria": [
            {
                "name": "Creativity & Originality",
                "description": "Fresh concept",
                "max_score": 25,
                "weight": Decimal("0.25"),
                "order": 1,
            },
            {
                "name": "Innovation & Problem-Solving",
                "description": "Effectiveness of solution",
                "max_score": 25,
                "weight": Decimal("0.25"),
                "order": 2,
            },
            {
                "name": "Design & Functionality",
                "description": "Technical soundness",
                "max_score": 20,
                "weight": Decimal("0.20"),
                "order": 3,
            },
            {
                "name": "Impact & Relevance",
                "description": "Community/environment value",
                "max_score": 15,
                "weight": Decimal("0.15"),
                "order": 4,
            },
            {
                "name": "Craftsmanship",
                "description": "Construction quality",
                "max_score": 10,
                "weight": Decimal("0.10"),
                "order": 5,
            },
            {
                "name": "Presentation & Communication",
                "description": "Pitch quality",
                "max_score": 5,
                "weight": Decimal("0.05"),
                "order": 6,
            },
        ],
    },
    "18-25": {
        "display_name": "Ages 18-25",
        "total_points": 100,
        "criteria": [
            {
                "name": "Creativity & Originality",
                "description": "Novelty & imagination",
                "max_score": 15,
                "weight": Decimal("0.15"),
                "order": 1,
            },
            {
                "name": "Innovation & Problem-Solving",
                "description": "Clear problem-solving",
                "max_score": 25,
                "weight": Decimal("0.25"),
                "order": 2,
            },
            {
                "name": "Design, Engineering & Functionality",
                "description": "Technical strength",
                "max_score": 25,
                "weight": Decimal("0.25"),
                "order": 3,
            },
            {
                "name": "Impact & Sustainability",
                "description": "Long-term social value",
                "max_score": 15,
                "weight": Decimal("0.15"),
                "order": 4,
            },
            {
                "name": "Feasibility & Scalability",
                "description": "Practicality & growth",
                "max_score": 10,
                "weight": Decimal("0.10"),
                "order": 5,
            },
            {
                "name": "Presentation & Professionalism",
                "description": "Confidence & communication",
                "max_score": 10,
                "weight": Decimal("0.10"),
                "order": 6,
            },
        ],
    },
}


class Command(BaseCommand):
    help = "Create Toy Festival rubrics for all age categories"

    def add_arguments(self, parser):
        parser.add_argument(
            "program_id",
            type=int,
            help="The ID of the program to create rubrics for",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force recreation of rubrics (deactivates existing ones)",
        )

    def handle(self, *args, **options):
        program_id = options["program_id"]
        force = options["force"]

        # Get the program
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            raise CommandError(f"Program with ID {program_id} does not exist")

        self.stdout.write(f"Creating rubrics for program: {program.name}")

        # Get or create a default RubricCategory for organizing criteria
        default_category, _ = RubricCategory.objects.get_or_create(
            name="General",
            defaults={
                "description": "General judging criteria",
                "order": 0,
            },
        )

        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for category_value, rubric_data in RUBRIC_DEFINITIONS.items():
                # Check if rubric already exists
                existing_rubric = Rubric.objects.filter(
                    program=program,
                    category_value=category_value,
                    is_active=True,
                ).first()

                if existing_rubric:
                    if force:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Deactivating existing rubric for '{category_value}'"
                            )
                        )
                        existing_rubric.is_active = False
                        existing_rubric.save()
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Skipping '{category_value}' - rubric already exists (use --force to recreate)"
                            )
                        )
                        skipped_count += 1
                        continue

                # Create rubric
                display_name = rubric_data.get("display_name", category_value)
                rubric = Rubric.objects.create(
                    program=program,
                    category_value=category_value,
                    name=f"{program.name} - {display_name}",
                    description=f"Scoring rubric for {display_name} participants",
                    total_possible_points=Decimal(str(rubric_data["total_points"])),
                    is_active=True,
                )

                self.stdout.write(f"  Created rubric: {rubric.name}")

                # Create criteria
                for criterion in rubric_data["criteria"]:
                    RubricCriteria.objects.create(
                        rubric=rubric,
                        category=default_category,
                        name=criterion["name"],
                        description=criterion["description"],
                        max_score=Decimal(str(criterion["max_score"])),
                        weight=criterion["weight"],
                        order=criterion["order"],
                    )
                    self.stdout.write(
                        f"    - {criterion['name']} (max: {criterion['max_score']})"
                    )

                created_count += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Done! Created {created_count} rubrics, skipped {skipped_count}")
        )
        
        if created_count > 0:
            self.stdout.write("")
            self.stdout.write("Next steps:")
            self.stdout.write("  1. Ensure the program's category_options match these age groups")
            self.stdout.write("  2. Registrations should have category_value set to one of:")
            for cat in RUBRIC_DEFINITIONS.keys():
                self.stdout.write(f"     - '{cat}'")
