"""
Management command to fix receipts with zero amounts.

For receipts with amount=0, this script will:
1. Check if there's a linked approval with a non-zero amount -> use that
2. Otherwise, if registration is fully paid, use program fee
3. Log all changes for audit

Usage:
    python manage.py fix_receipt_amounts          # Dry run (no changes)
    python manage.py fix_receipt_amounts --apply  # Apply changes
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from register.models import Receipt, Approval, Registration


class Command(BaseCommand):
    help = "Fix receipts that have amount=0 by inferring from approvals or program fee"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually apply the fixes. Without this flag, only a dry-run report is shown.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        
        if apply:
            self.stdout.write(self.style.WARNING("Running in APPLY mode - changes will be saved."))
        else:
            self.stdout.write(self.style.NOTICE("Running in DRY-RUN mode - no changes will be made."))
        
        # Find all receipts with amount = 0 or NULL
        zero_receipts = Receipt.objects.filter(amount__lte=Decimal("0")).select_related(
            "registration__program"
        )
        
        self.stdout.write(f"\nFound {zero_receipts.count()} receipts with amount <= 0")
        
        fixed_count = 0
        skipped_count = 0
        
        for receipt in zero_receipts:
            reg = receipt.registration
            program_fee = reg.program.registration_fee or Decimal("0")
            
            # Method 1: Check if there's a linked approval via OneToOne
            linked_approval = getattr(receipt, 'approval', None)
            if linked_approval and linked_approval.amount and linked_approval.amount > Decimal("0"):
                new_amount = linked_approval.amount
                source = f"linked approval #{linked_approval.id}"
            else:
                # Method 2: Find any approval for this registration with matching receipt
                try:
                    approval = Approval.objects.get(receipt=receipt)
                    if approval.amount and approval.amount > Decimal("0"):
                        new_amount = approval.amount
                        source = f"approval #{approval.id} (FK match)"
                    else:
                        new_amount = None
                        source = None
                except Approval.DoesNotExist:
                    new_amount = None
                    source = None
                except Approval.MultipleObjectsReturned:
                    # Shouldn't happen with OneToOne, but handle it
                    approval = Approval.objects.filter(receipt=receipt).first()
                    if approval and approval.amount and approval.amount > Decimal("0"):
                        new_amount = approval.amount
                        source = f"first approval #{approval.id}"
                    else:
                        new_amount = None
                        source = None
            
            # Method 3: If no approval amount found, check registration status
            if not new_amount:
                if reg.status == Registration.Status.PAID:
                    # Fully paid - receipt should be the full fee (or remaining at time)
                    # Count how many receipts exist for this registration
                    receipt_count = reg.receipts.count()
                    if receipt_count == 1:
                        # Single receipt = full payment
                        new_amount = program_fee
                        source = "program fee (single receipt, fully paid)"
                    else:
                        # Multiple receipts - need to calculate share
                        total_other_receipts = reg.receipts.exclude(pk=receipt.pk).aggregate(
                            total=Sum("amount")
                        )["total"] or Decimal("0")
                        new_amount = program_fee - total_other_receipts
                        if new_amount <= Decimal("0"):
                            new_amount = None
                            source = None
                        else:
                            source = f"remaining after {receipt_count-1} other receipts"
                elif reg.status == Registration.Status.PARTIALLY_PAID:
                    # Can't determine exact amount for partial without approval record
                    new_amount = None
                    source = None
            
            if new_amount and new_amount > Decimal("0"):
                self.stdout.write(
                    f"  Receipt #{receipt.id} (Reg #{reg.id}, {reg.participant}): "
                    f"{receipt.amount} -> {new_amount} (source: {source})"
                )
                if apply:
                    receipt.amount = new_amount
                    receipt.save(update_fields=["amount"])
                fixed_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Receipt #{receipt.id} (Reg #{reg.id}): SKIPPED - could not determine amount"
                    )
                )
                skipped_count += 1
        
        # Summary
        self.stdout.write("")
        if apply:
            self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} receipts, skipped {skipped_count}"))
        else:
            self.stdout.write(self.style.NOTICE(
                f"DRY RUN: Would fix {fixed_count} receipts, skip {skipped_count}. "
                f"Run with --apply to make changes."
            ))
        
        # Also show receipts that already have correct amounts for context
        good_receipts = Receipt.objects.filter(amount__gt=Decimal("0")).count()
        self.stdout.write(f"\nReceipts with amount > 0: {good_receipts}")
