import csv
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from register.models import Program
from scores.models import RubricCategory
from scores.services import RubricService


class Command(BaseCommand):
    help = (
        "Create a new Rubric (Phase 2) for a Program from a CSV exported by "
        "export_legacy_rubrics_csv."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to CSV containing columns: category,category_order,criteria,criteria_order,description,guidelines,max_score,weight",
        )
        parser.add_argument(
            "program_id",
            type=int,
            help="Program ID for which to create the rubric",
        )
        parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Optional rubric name. If omitted, a name will be generated.",
        )
        parser.add_argument(
            "--total-points",
            type=Decimal,
            default=Decimal("100.00"),
            help="Rubric total_possible_points (Decimal)",
        )
        parser.add_argument(
            "--normalize-weights",
            action="store_true",
            help="If provided, normalize weights to sum to 1.000 even if the CSV slightly deviates.",
        )
        parser.add_argument(
            "--strict-unique",
            action="store_true",
            help=(
                "If set, error when duplicate criterion names are found (default behavior dedupes by appending category name)."
            ),
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"]).expanduser()
        program_id = options["program_id"]
        rubric_name = options["name"]
        total_points = options["total_points"]
        normalize = options["normalize_weights"]
        strict_unique = options["strict_unique"]

        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            raise CommandError(f"Program with id={program_id} does not exist")

        if not rubric_name:
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            rubric_name = f"Imported Rubric from {csv_path.name} ({timestamp})"

        # Parse CSV rows
        required_cols = {
            "category",
            "criteria",
            "max_score",
            "weight",
        }
        rows = []
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing_cols = required_cols - set((reader.fieldnames or []))
            if missing_cols:
                raise CommandError(
                    f"CSV missing required columns: {', '.join(sorted(missing_cols))}"
                )
            for row in reader:
                # Clean core fields
                category_name = (row.get("category") or "").strip()
                criteria_name = (row.get("criteria") or "").strip()
                if not category_name or not criteria_name:
                    # skip any malformed/blank lines
                    continue
                try:
                    max_score = Decimal((row.get("max_score") or "10").strip())
                except (InvalidOperation, AttributeError):
                    raise CommandError(
                        f"Invalid max_score value for criterion '{criteria_name}'"
                    )
                weight_raw = (row.get("weight") or "").strip()
                weight = None
                if weight_raw:
                    try:
                        weight = Decimal(weight_raw)
                    except InvalidOperation:
                        raise CommandError(
                            f"Invalid weight value '{weight_raw}' for criterion '{criteria_name}'"
                        )
                description = (row.get("description") or "").strip()
                guidelines = (row.get("guidelines") or "").strip()
                try:
                    category_order = int((row.get("category_order") or 0))
                except ValueError:
                    category_order = 0
                try:
                    criteria_order = int((row.get("criteria_order") or 0))
                except ValueError:
                    criteria_order = 0

                rows.append(
                    {
                        "category_name": category_name,
                        "category_order": category_order,
                        "criteria_name": criteria_name,
                        "criteria_order": criteria_order,
                        "description": description,
                        "guidelines": guidelines,
                        "max_score": max_score,
                        "weight": weight,  # may be None
                    }
                )

        if not rows:
            raise CommandError("CSV has no valid rows to import.")

        # Ensure RubricCategory existence and collect mapping
        category_cache = {}
        for r in rows:
            name = r["category_name"]
            if name not in category_cache:
                cat, created = RubricCategory.objects.get_or_create(
                    name=name,
                    defaults={"order": r["category_order"]},
                )
                # Optionally update order if different
                if not created and r["category_order"] is not None:
                    try:
                        order_val = int(r["category_order"])
                        if order_val != cat.order:
                            cat.order = order_val
                            cat.save(update_fields=["order"]) \
                                if hasattr(cat, "order") else None
                    except Exception:
                        pass
                category_cache[name] = cat

        # Build criteria list for service
        criteria_list = []
        provided_weights = []
        for r in rows:
            cat = category_cache[r["category_name"]]
            criteria_list.append(
                {
                    "category": cat,  # model instance is fine for objects.create
                    "name": r["criteria_name"],
                    "description": r["description"],
                    "guidelines": r["guidelines"],
                    "max_score": r["max_score"],
                    "weight": r["weight"] if r["weight"] is not None else Decimal("0.000"),
                    "order": r["criteria_order"],
                }
            )
            if r["weight"] is not None:
                provided_weights.append(r["weight"])

        # Handle weights: if any weight is missing, compute even weights across all criteria
        if len(provided_weights) != len(criteria_list):
            n = len(criteria_list)
            base = (Decimal("1.000") / Decimal(n)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            running = Decimal("0.000")
            for i in range(n - 1):
                criteria_list[i]["weight"] = base
                running += base
            criteria_list[-1]["weight"] = (Decimal("1.000") - running).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        else:
            total = sum(Decimal(str(c["weight"])) for c in criteria_list)
            if normalize:
                # Normalize by total if non-zero, then re-quantize ensuring sum to ~1.000
                if total == 0:
                    raise CommandError("All provided weights are zero; cannot normalize.")
                scaled = []
                running = Decimal("0.000")
                for i, c in enumerate(criteria_list):
                    if i < len(criteria_list) - 1:
                        w = (Decimal(c["weight"]) / total).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
                        scaled.append(w)
                        running += w
                    else:
                        w = (Decimal("1.000") - running).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
                        scaled.append(w)
                for c, w in zip(criteria_list, scaled):
                    c["weight"] = w
            else:
                # Let service validate; provide a clearer error if sum far off
                if abs(total - Decimal("1.000")) > Decimal("0.050"):
                    raise CommandError(
                        f"Weights sum to {total:.3f}. Provide --normalize-weights or fix the CSV to sum to 1.000."
                    )

        # Ensure unique criterion names within the rubric
        # If --strict-unique is set, raise on duplicates. Otherwise, auto-dedupe by appending category name,
        # and if still duplicated, append an incremental numeric suffix.
        used_names = set()
        duplicates_found = set()
        for c in criteria_list:
            original = c["name"].strip()
            key = original.lower()
            if key in used_names:
                duplicates_found.add(original)
            used_names.add(key)

        if duplicates_found and strict_unique:
            dup_list = ", ".join(sorted(duplicates_found))
            raise CommandError(
                f"Duplicate criterion names found in CSV (names must be unique within a rubric): {dup_list}"
            )

        if duplicates_found and not strict_unique:
            self.stdout.write(
                self.style.WARNING(
                    "Duplicate criterion names detected; auto-renaming to ensure uniqueness within the rubric."
                )
            )
            used = set()
            for c in criteria_list:
                base_name = c["name"].strip()
                candidate = base_name
                lc = candidate.lower()
                if lc in used:
                    # Try appending category first
                    category_label = c["category"].name.strip()
                    candidate = f"{base_name} ({category_label})"
                    lc = candidate.lower()
                    idx = 2
                    while lc in used:
                        candidate = f"{base_name} ({category_label}) #{idx}"
                        lc = candidate.lower()
                        idx += 1
                    c["name"] = candidate
                    self.stdout.write(
                        self.style.WARNING(
                            f"Renamed criterion '{base_name}' -> '{candidate}'"
                        )
                    )
                used.add(lc)

        # Create rubric via service (handles deactivating any existing active rubric)
        rubric = RubricService.create_rubric(
            program=program,
            name=rubric_name,
            criteria_list=criteria_list,
            created_by=None,
            total_points=total_points,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Created rubric '{rubric.name}' for program '{program.name}' with {rubric.criteria_count} criteria."
        ))
