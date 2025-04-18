
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from register.models import Registration, Receipt
from accounts.models import User


class Command(BaseCommand):
    help = "Generate receipts for all paid registrations (one per Registration)."

    def handle(self, *args, **options):
        # 1) find an admin user
        admin = User.objects.filter(role=User.Role.ADMIN).first()
        if not admin:
            self.stderr.write(self.style.ERROR("➥ No admin user found (role='admin'). Aborting."))
            return

        # 2) find paid registrations without receipts
        regs = (
            Registration.objects
            .filter(status=Registration.Status.PAID)
            .filter(receipts__isnull=True)
        )

        total = regs.count()
        success = 0
        failures = []

        for reg in regs:
            try:
                with transaction.atomic():
                    # 3) create the receipt
                    receipt = Receipt.objects.create(
                        registration=reg,
                        issued_by=admin,
                        amount=reg.program.registration_fee,
                        status=Receipt.Status.PAID
                    )
                    # 4) override created_at to match registration
                    receipt.created_at = reg.created_at
                    receipt.save(update_fields=["created_at"])

                success += 1
                self.stdout.write(self.style.SUCCESS(
                    f"✔ Receipt #{receipt.id} for Registration #{reg.id}"
                ))

            except Exception as e:
                failures.append((reg.id, str(e)))
                self.stderr.write(self.style.ERROR(
                    f"✘ Failed for Registration #{reg.id}: {e}"
                ))

        # 5) summary
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Done: {success}/{total} receipts created."
        ))
        if failures:
            self.stdout.write(self.style.WARNING("Failures:"))
            for reg_id, err in failures:
                self.stdout.write(f" - Registration {reg_id}: {err}")
