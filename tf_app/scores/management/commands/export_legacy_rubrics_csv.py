import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from scores.models import MainCategory, JudgingCriteria


class Command(BaseCommand):
    help = (
        "Export legacy MainCategory/JudgingCriteria into a CSV suitable for building new rubrics. "
        "The CSV is written to Django BASE_DIR by default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="legacy_rubrics.csv",
            help="Output CSV filename (relative to BASE_DIR or absolute path)",
        )
        parser.add_argument(
            "--no-even-weights",
            action="store_true",
            help="Do not compute even weights; leave weight column blank",
        )
        parser.add_argument(
            "--max-score",
            type=Decimal,
            default=Decimal("10.00"),
            help="Default max_score for each criterion (Decimal)",
        )

    def handle(self, *args, **options):
        output = options["output"]
        leave_weights_blank = options["no_even_weights"]
        default_max = options["max_score"]

        # Resolve output path
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = Path(settings.BASE_DIR) / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Collect data
        categories = (
            MainCategory.objects.all()
            .order_by("name")
            .prefetch_related("criteria")
        )

        # Flatten all criteria to count
        all_criteria_ids = list(
            JudgingCriteria.objects.values_list("id", flat=True)
        )
        total_criteria = len(all_criteria_ids)

        if total_criteria == 0:
            self.stdout.write(self.style.WARNING("No JudgingCriteria found. Nothing to export."))
            return

        # Compute even weights across all criteria if requested
        weights = {}
        if not leave_weights_blank:
            # Use 3 decimal places (RubricCriteria.weight has decimal_places=3)
            base_weight = (Decimal("1.000") / Decimal(total_criteria)).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
            running_sum = Decimal("0.000")
            criteria_qs = JudgingCriteria.objects.order_by("category__name", "name")
            for idx, crit in enumerate(criteria_qs, start=1):
                if idx < total_criteria:
                    weights[crit.id] = base_weight
                    running_sum += base_weight
                else:
                    # Make the last one the remainder to ensure exact sum of 1.000
                    remainder = (Decimal("1.000") - running_sum).quantize(
                        Decimal("0.001"), rounding=ROUND_HALF_UP
                    )
                    weights[crit.id] = remainder

        # Write CSV
        fieldnames = [
            "category",
            "category_order",
            "criteria",
            "criteria_order",
            "description",
            "guidelines",
            "max_score",
            "weight",
        ]

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            category_order = 0
            for category in categories:
                criteria_qs = category.criteria.all().order_by("name")
                criteria_order = 0
                for crit in criteria_qs:
                    writer.writerow(
                        {
                            "category": category.name.strip(),
                            "category_order": category_order,
                            "criteria": crit.name.strip(),
                            "criteria_order": criteria_order,
                            "description": (crit.description or "").strip(),
                            "guidelines": "",
                            "max_score": f"{default_max:.2f}",
                            "weight": (
                                "" if leave_weights_blank else f"{weights.get(crit.id, Decimal('0.000')):.3f}"
                            ),
                        }
                    )
                    criteria_order += 1
                category_order += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {total_criteria} criteria across {categories.count()} categories to: {output_path}"
            )
        )
