import os
from django.conf import settings
from io import BytesIO
from django.core.files import File
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator, MinLengthValidator
from datetime import datetime

import qrcode
from PIL import Image

from core.models import BaseModel


class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        mobile_money = "mobile_money", _("Mobile Money")
        cash = 'cash', _("Cash")

    payment_method = models.CharField(max_length=15, choices=PaymentMethod.choices)

    def __str__(self):
        return f'{self.payment_method}'


class Contestant(BaseModel):
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Contestant')
        verbose_name_plural = _('Contestants')


    class ContestantGender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')

    class PaymentStatus(models.TextChoices):
        PAID = 'paid', _('Paid')
        NOT_PAID = 'not_paid', _('Not_Paid')

    identifier = models.CharField(max_length=15, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, blank=True, null=True)
    age = models.IntegerField()
    gender = models.CharField(max_length=1, choices=ContestantGender.choices)
    school = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=15, choices=PaymentStatus.choices, default=PaymentStatus.NOT_PAID)
    payment_method = models.ForeignKey('Payment', on_delete=models.SET_NULL, blank=True, null=True)
    parent = models.ForeignKey('Parent', on_delete=models.SET_NULL,blank=True, null=True, related_name='contestants')

    AGE_CATEGORY_CHOICES = [
        ('junior', _('Junior')),  # Ages 3-7
        ('intermediate', _('Intermediate')),  # Ages 8-12
        ('senior', _('Senior')),  # Ages 13-17
    ]

    age_category = models.CharField(max_length=12, choices=AGE_CATEGORY_CHOICES, editable=False, blank=True, null=True)

    def set_age_category(self):
        """Determine the age category based on the contestant's age."""
        age = int(self.age or 0)
        if 3 <= age <= 7:
            self.age_category = 'junior'
        elif 8 <= age <= 12:
            self.age_category = 'intermediate'
        elif 13 <= age <= 17:
            self.age_category = 'senior'
        else:
            self.age_category = None

    def save(self, *args, **kwargs):
        if self.payment_status == 'paid' and not self.identifier:
            current_year = datetime.now().year % 100
            self.identifier = f'TF{current_year}{self.id:03d}'
            self.set_age_category()
            super().save(*args, **kwargs)
        else:
            self.set_age_category()
            super().save(*args, **kwargs)


    # def save(self, *args, **kwargs):
    #     if not self.pk and not self.identifier:
    #         super().save(*args, **kwargs)  # Save to generate an ID
    #
    #         current_year = datetime.now().year % 100
    #         self.identifier = f'TF{current_year}{self.id:03d}'
    #
    #         if self.identifier is not None:
    #             self.set_age_category()
    #             self.save()  # Save again to store the identifier
    #     else:
    #         self.set_age_category()
    #         super().save(*args, **kwargs)


    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Parent(BaseModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profession = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=100)

    # Email & Number Validator if they are required fields
    email = models.EmailField(
        max_length=254,
        validators=[EmailValidator(message="Invalid email address")],
        null=True, blank=True
    )
    phone_number = models.CharField(
        max_length=13,
        validators=[MinLengthValidator(10, message="Phone number must have at least 10 digits")]
    )

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Ticket(BaseModel):
    participant = models.OneToOneField(
        'register.Contestant',
        on_delete=models.CASCADE,
        related_name='ticket'
    )
    qr_code = models.ImageField(upload_to='tickets/qrcodes/', blank=True, null=True)

    def create_qr_code(self):
        """Generates a QR code for the participant."""
        if not self.participant:
            raise ValueError("Cannot create QR code: Ticket is not linked to a participant.")

        # Generate the QR code data
        qr_data = f"https://app.wokober.com/verify/{self.participant.id}"

        # Create the QR code image
        qr_image = qrcode.make(qr_data)

        # Save the QR code to an in-memory file
        qr_io = BytesIO()
        qr_image.save(qr_io, format='PNG')
        qr_io.seek(0)

        # Save the in-memory file to the qr_code field
        filename = f"participant_{self.participant.id}_qrcode.png"
        self.qr_code.save(filename, File(qr_io), save=False)

    def save(self, *args, **kwargs):
        """Override save to automatically generate QR code if not already created."""
        if not self.qr_code:
            self.create_qr_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket-#{self.participant.id}"



#*************************#
#  NEW APP ARCHITECTURE   #
#*************************#

class School(BaseModel):
    """
    Holds information about schools. One school can have many participants.
    """
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(
        max_length=254,
        validators=[EmailValidator(message="Invalid email address")],
        blank=True, null=True
    )
    phone_number = models.CharField(
        max_length=13,
        validators=[MinLengthValidator(10, message="Phone number must have at least 10 digits")],
        blank=True, null=True
    )

    class Meta:
        verbose_name = _('School')
        verbose_name_plural = _('Schools')
        ordering = ['name']

    def __str__(self):
        return self.name


class Guardian(BaseModel):
    """
    A person responsible for one or more participants.
    """
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    profession   = models.CharField(max_length=100, blank=True, null=True)
    address      = models.CharField(max_length=255, blank=True, null=True)
    email        = models.EmailField(
        max_length=254,
        validators=[EmailValidator(message="Invalid email address")],
        blank=True, null=True
    )
    phone_number = models.CharField(
        max_length=13,
        validators=[MinLengthValidator(10, message="Phone number must have at least 10 digits")],
        blank=True, null=True
    )

    class Meta:
        verbose_name = _('Guardian')
        verbose_name_plural = _('Guardians')
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Participant(BaseModel):
    """
    A person profile; evergreen data. One participant can sign up for many programs.
    """
    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')

    first_name     = models.CharField(max_length=100)
    last_name      = models.CharField(max_length=100)
    email          = models.EmailField(max_length=254, blank=True, null=True)
    date_of_birth  = models.DateField(blank=True, null=True)
    age = models.IntegerField()
    gender         = models.CharField(max_length=1, choices=Gender.choices)
    current_school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        related_name='students',
        blank=True,
        null=True
    )
    guardians = models.ManyToManyField(
        Guardian,
        through='ParticipantGuardian',
        related_name='participants'
    )


    class Meta:
        verbose_name = _('Participant')
        verbose_name_plural = _('Participants')
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def current_age(self):
        """
        Current age computed from date_of_birth.
        """
        from django.utils import timezone
        today = timezone.now().date()
        dob = self.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age


class ParticipantGuardian(models.Model):
    """
    Through model linking Participants and Guardians, with role metadata.
    """
    participant  = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE
    )
    guardian     = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE
    )
    relationship = models.CharField(
        max_length=20,
        choices=[
            ('mother', 'Mother'),
            ('father', 'Father'),
            ('aunt', 'Aunt'),
            ('uncle', 'Uncle'),
            ('other', 'Other'),
        ]
    )
    is_primary   = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Participant-Guardian Link')
        verbose_name_plural = _('Participant-Guardian Links')
        unique_together = (('participant', 'guardian'),)

    def __str__(self):
        return f"{self.guardian} -> {self.participant} ({self.relationship})"


class ProgramType(BaseModel):
    """
    A reusable, recurring program definition like 'Toy Festival', 'Mentorship Program', etc.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    form_key    = models.CharField(
        max_length=50,
        help_text="Front‑end key for the React form component (e.g. 'tf', 'mp')"
    )

    def __str__(self):
        return self.name


class Program(BaseModel):
    """
    Defines an event or offering for which participants can register.
    e.g. Toy Festival 2025, Mentorship Program 2024, etc.
    """
    type = models.ForeignKey(
        ProgramType,
        on_delete=models.SET_NULL,
        related_name='programs',
        blank=True,
        null=True,
        help_text=_("Leave blank if this is a one-time program")
    )
    year = models.PositiveIntegerField(blank=True, null=True)

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    registration_fee = models.DecimalField(max_digits=8, decimal_places=2, help_text=_("Fee in your local currency"), blank=True, null=True)
    age_min = models.PositiveIntegerField(help_text=_("Minimum age to participate"), blank=True, null=True)
    age_max = models.PositiveIntegerField(help_text=_("Maximum age to participate"), blank=True, null=True)
    capacity = models.PositiveIntegerField(blank=True, null=True, help_text=_("Maximum number of participants. Leave blank for unlimited."))
    requires_ticket = models.BooleanField(
        default=False,
        help_text=_('Whether program participation requires a ticket')
    )

    class Meta:
        verbose_name = _('Program')
        verbose_name_plural = _('Programs')
        ordering = ['name']

    def __str__(self):
        return self.name


class Registration(BaseModel):
    """
    Ties a Participant to a Program, capturing all program-specific details
    including payment, age at enrollment, school snapshot, and responsible guardian.
    """
    class Status(models.TextChoices):
        PENDING   = 'pending',   _('Pending')
        PAID      = 'paid',      _('Paid')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED  = 'refunded',  _('Refunded')


    participant = models.ForeignKey(
        'Participant',
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    age_at_registration = models.PositiveIntegerField()
    school_at_registration = models.ForeignKey(
        'School',
        on_delete=models.SET_NULL,
        related_name='registrations',
        blank=True,
        null=True
    )
    guardian_at_registration = models.ForeignKey(
        'Guardian',
        on_delete=models.SET_NULL,
        related_name='registrations_as_guardian',
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    class Meta:
        verbose_name = _('Registration')
        verbose_name_plural = _('Registrations')
        unique_together = (('participant', 'program'),)
        ordering = ['-created_at']

    # def save(self, *args, **kwargs):
    #     # On initial save, compute age_at_enrollment
    #     if not self.pk:
    #         dob = self.participant.date_of_birth
    #         enrolled_date = self.registered_at.date() if self.registered_at else timezone.now().date()
    #         self.age_at_enrollment = (
    #             enrolled_date.year - dob.year
    #             - ((enrolled_date.month, enrolled_date.day) < (dob.month, dob.day))
    #         )
    #     super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.participant} @ {self.program}"


class Receipt(BaseModel):
    """
    A receipt for a completed PaymentApproval / Registration.
    """
    class Status(models.TextChoices):
        PAID    = 'paid',    _('Paid')
        REFUNDED= 'refunded',_('Refunded')

    registration = models.ForeignKey(
        'Registration',
        on_delete=models.CASCADE,
        related_name='receipts'
    )
    issued_by    = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='issuer'
    )
    amount       = models.DecimalField(max_digits=8, decimal_places=2)
    status       = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PAID
    )


    def __str__(self):
        return f'Receipt-{self.registration}'


class Coupon(BaseModel):
    """
    Ticket for a registration…
    """
    class Status(models.TextChoices):
        PAID     = 'paid',     _('Paid')
        REFUNDED = 'refunded', _('Refunded')

    registration = models.OneToOneField(
        'Registration', on_delete=models.CASCADE, related_name='coupon'
    )
    qr_code      = models.ImageField(
        upload_to='tickets/qrcodes/', blank=True, null=True
    )
    status       = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PAID
    )

    def create_qr_code(self):
        url = f"https://app.wokober.com/verify/{self.registration.id}"
        img = qrcode.make(url)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        self.qr_code.save(f"ticket_{self.registration.id}.png", File(buffer), save=False)

    def save(self, *args, **kwargs):
        if not self.qr_code and self.registration.program.requires_ticket:
            self.create_qr_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket #{self.registration.id}"


class Approval(BaseModel):
    """
    Records a staff action on a Registration: marking it Paid, Cancelled, or Refunded.
    Handles post-processing to update related models (Registration, Receipt, Ticket, Coupon).
    """
    class Status(models.TextChoices):
        PAID      = 'paid',      _('Paid')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED  = 'refunded',  _('Refunded')

    registration = models.ForeignKey(
        'Registration',
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    status       = models.CharField(
        max_length=10,
        choices=Status.choices
    )
    created_by     = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approvals'
    )
    receipt      = models.OneToOneField(
        'Receipt',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval'
    )
    coupon       = models.OneToOneField(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval'
    )

    class Meta:
        verbose_name = _('Approval')
        verbose_name_plural = _('Approvals')
        ordering = ['created_at']

    def __str__(self):
        return f"Approval({self.status}) for {self.registration}"

    def post_process(self):
        reg = self.registration
        old = reg.status

        # ——— Validation: only sensible transitions ———
        if self.status == self.Status.CANCELLED and old == self.Status.PAID:
            raise ValidationError("Cannot cancel a registration that is already paid.")
        if self.status == self.Status.PAID and old == self.Status.CANCELLED:
            raise ValidationError("Cannot mark cancelled registration as paid.")
        if self.status == self.Status.REFUNDED and old != self.Status.PAID:
            raise ValidationError("Only paid registrations can be refunded.")
        # ——— end validations ———

        # Idempotent guard
        if old == self.status:
            return

        # Apply to Registration
        reg.status = self.status
        reg.save(update_fields=['status'])

        # Handle side‑effects
        if self.status == self.Status.PAID:
            # 1) create receipt
            receipt = Receipt.objects.create(
                registration=reg,
                issued_by=self.created_by,
                amount=reg.program.registration_fee,
                status=Receipt.Status.PAID
            )
            self.receipt = receipt

            # 2) ticket if needed
            if reg.program.requires_ticket:
                ticket = Coupon.objects.create(registration=reg, status=Coupon.Status.PAID)
                self.coupon = ticket

        elif self.status == self.Status.REFUNDED:
            # mark receipt & ticket refunded
            if self.receipt:
                self.receipt.status = Receipt.Status.REFUNDED
                self.receipt.save(update_fields=['status'])
            if self.coupon:
                self.coupon.status = Coupon.Status.REFUNDED
                self.coupon.save(update_fields=['status'])

        # save Approval links
        self.save(update_fields=['receipt', 'coupon'])
        return self