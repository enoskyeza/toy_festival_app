"""
Management command to reconcile duplicate/inconsistent approvals.

Fixes:
1. Registrations with duplicate paid approvals (e.g., one with amount, one with 0)
2. Ensures receipt exists for valid payment
3. Ensures ticket/coupon exists if program requires it
4. Marks registration status correctly (paid/partially_paid/pending)

Usage:
    python manage.py reconcile_approvals --dry-run  # Preview changes
    python manage.py reconcile_approvals            # Apply fixes
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from register.models import Registration, Approval, Receipt, Coupon


class Command(BaseCommand):
    help = 'Reconcile duplicate and inconsistent approval records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )
        parser.add_argument(
            '--registration-id',
            type=int,
            help='Only process a specific registration ID',
        )
        parser.add_argument(
            '--program-id',
            type=int,
            help='Only process registrations for a specific program',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        registration_id = options.get('registration_id')
        program_id = options.get('program_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE - No changes will be made ===\n'))

        # Build queryset
        # Note: 'coupon' is OneToOne (singular), 'receipts' is ForeignKey (plural)
        registrations = Registration.objects.select_related('program', 'participant', 'coupon').prefetch_related(
            'approvals', 'receipts'
        )

        if registration_id:
            registrations = registrations.filter(id=registration_id)
        if program_id:
            registrations = registrations.filter(program_id=program_id)

        stats = {
            'processed': 0,
            'duplicates_removed': 0,
            'receipts_created': 0,
            'coupons_created': 0,
            'status_fixed': 0,
            'errors': 0,
        }

        for reg in registrations:
            try:
                result = self.reconcile_registration(reg, dry_run)
                stats['processed'] += 1
                stats['duplicates_removed'] += result.get('duplicates_removed', 0)
                stats['receipts_created'] += result.get('receipts_created', 0)
                stats['coupons_created'] += result.get('coupons_created', 0)
                stats['status_fixed'] += result.get('status_fixed', 0)
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing registration {reg.id}: {e}')
                )

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('RECONCILIATION SUMMARY'))
        self.stdout.write('=' * 60)
        self.stdout.write(f"Registrations processed: {stats['processed']}")
        self.stdout.write(f"Duplicate approvals removed: {stats['duplicates_removed']}")
        self.stdout.write(f"Receipts created: {stats['receipts_created']}")
        self.stdout.write(f"Coupons/tickets created: {stats['coupons_created']}")
        self.stdout.write(f"Registration statuses fixed: {stats['status_fixed']}")
        self.stdout.write(f"Errors: {stats['errors']}")

        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN - No changes were made ==='))

    def reconcile_registration(self, reg, dry_run=False):
        """Reconcile a single registration's approvals."""
        result = {
            'duplicates_removed': 0,
            'receipts_created': 0,
            'coupons_created': 0,
            'status_fixed': 0,
        }

        program_fee = reg.program.registration_fee or Decimal('0')
        
        # Get all paid approvals
        paid_approvals = list(reg.approvals.filter(status='paid').order_by('created_at'))
        
        if not paid_approvals:
            # No paid approvals - check if status needs fixing
            if reg.status == 'paid':
                self.stdout.write(
                    self.style.WARNING(
                        f"  Registration {reg.id} ({reg.participant}): "
                        f"Status is 'paid' but no paid approvals found!"
                    )
                )
                if not dry_run:
                    reg.status = 'pending'
                    reg.save(update_fields=['status'])
                result['status_fixed'] = 1
            return result

        # Calculate total paid from valid (non-zero) approvals
        valid_approvals = [a for a in paid_approvals if a.amount and a.amount > 0]
        zero_approvals = [a for a in paid_approvals if not a.amount or a.amount == 0]
        
        total_paid = sum(a.amount for a in valid_approvals if a.amount)

        self.stdout.write(
            f"\nRegistration {reg.id} ({reg.participant}) - Program: {reg.program.name}"
        )
        self.stdout.write(f"  Program fee: {program_fee}")
        self.stdout.write(f"  Total paid approvals: {len(paid_approvals)}")
        self.stdout.write(f"  Valid approvals (amount > 0): {len(valid_approvals)}")
        self.stdout.write(f"  Zero-amount approvals: {len(zero_approvals)}")
        self.stdout.write(f"  Total amount paid: {total_paid}")
        self.stdout.write(f"  Current status: {reg.status}")

        # Remove zero-amount duplicate approvals
        if zero_approvals and valid_approvals:
            self.stdout.write(
                self.style.WARNING(f"  -> Found {len(zero_approvals)} zero-amount approvals to remove")
            )
            for zero_approval in zero_approvals:
                self.stdout.write(f"     Removing approval {zero_approval.id} (amount=0)")
                if not dry_run:
                    # Clear the receipt/coupon FK on the zero-amount approval before deleting
                    # The valid approval should already have its own receipt/coupon
                    # If not, we'll create them later in the script
                    zero_approval.receipt = None
                    zero_approval.coupon = None
                    zero_approval.save(update_fields=['receipt', 'coupon'])
                    zero_approval.delete()
                result['duplicates_removed'] += 1

        # Determine correct status
        if total_paid >= program_fee:
            correct_status = 'paid'
        elif total_paid > 0:
            correct_status = 'partially_paid'
        else:
            correct_status = 'pending'

        # Fix status if needed
        if reg.status != correct_status:
            self.stdout.write(
                self.style.WARNING(
                    f"  -> Status mismatch: {reg.status} should be {correct_status}"
                )
            )
            if not dry_run:
                reg.status = correct_status
                reg.save(update_fields=['status'])
            result['status_fixed'] = 1

        # Ensure receipt exists for fully paid
        if correct_status == 'paid':
            receipts = reg.receipts.filter(status='paid')
            if not receipts.exists():
                self.stdout.write(self.style.WARNING("  -> Missing receipt, creating one"))
                if not dry_run:
                    # Find the approval with the most payment
                    main_approval = max(valid_approvals, key=lambda a: a.amount or 0)
                    receipt = Receipt.objects.create(
                        registration=reg,
                        issued_by=main_approval.created_by,
                        amount=total_paid,
                        status='paid'
                    )
                    main_approval.receipt = receipt
                    main_approval.save(update_fields=['receipt'])
                result['receipts_created'] = 1

            # Ensure coupon/ticket exists if program requires it
            if reg.program.requires_ticket:
                coupons = Coupon.objects.filter(registration=reg, status='paid')
                if not coupons.exists():
                    self.stdout.write(self.style.WARNING("  -> Missing ticket/coupon, creating one"))
                    if not dry_run:
                        main_approval = max(valid_approvals, key=lambda a: a.amount or 0)
                        coupon = Coupon.objects.create(
                            registration=reg,
                            status='paid'
                        )
                        main_approval.coupon = coupon
                        main_approval.save(update_fields=['coupon'])
                    result['coupons_created'] = 1

        if not any(result.values()):
            self.stdout.write(self.style.SUCCESS("  ✓ No issues found"))

        return result
