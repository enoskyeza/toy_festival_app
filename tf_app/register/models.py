# Current models.py
from io import BytesIO

from django.conf import settings
from django.core.files import File
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from datetime import datetime
from django.utils.text import slugify

import qrcode
from PIL import Image

from core.models import BaseModel





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

        if not self.date_of_birth:
            return None

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
    active = models.BooleanField(
        default=True,
        help_text=_('Whether program participation is still active')
    )
    is_judgable = models.BooleanField(
        default=False,
        help_text=_('Whether this program requires judging/scoring')
    )
    
    # Additional fields from frontend form
    long_description = models.TextField(blank=True, null=True, help_text=_("Detailed program description"))
    level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        blank=True,
        null=True,
        help_text=_("Skill level required")
    )
    thumbnail_url = models.URLField(blank=True, null=True, help_text=_("Thumbnail image URL"))
    logo = models.ImageField(upload_to='programs/logos/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, help_text=_("Preview video URL"))
    instructor = models.CharField(max_length=200, blank=True, null=True, help_text=_("Instructor name"))
    featured = models.BooleanField(default=False, help_text=_("Whether this is a featured program"))

    # Registration categorisation (optional)
    category_label = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text=_("Label shown on forms for participant categorisation (e.g. 'Age Group').")
    )
    category_options = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of allowed category values (e.g. ['6-9 years', '10-13 years']). Leave empty for free text.")
    )
    
    # JSON fields for curriculum data
    modules = models.JSONField(default=list, blank=True, help_text=_("List of curriculum modules"))
    learning_outcomes = models.JSONField(default=list, blank=True, help_text=_("List of learning outcomes"))
    requirements = models.JSONField(default=list, blank=True, help_text=_("List of prerequisites and requirements"))


    class Meta:
        verbose_name = _('Program')
        verbose_name_plural = _('Programs')
        ordering = ['name']

    def __str__(self):
        return self.name


class ProgramForm(models.Model):
    """
    A logical form structure tied to a program, like "Junior Form" or "Adult Form".
    """
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='forms')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    is_default = models.BooleanField(default=False, help_text="Used when auto-selecting forms")
    is_active = models.BooleanField(default=False, help_text="Active form for program registration")
    age_min = models.PositiveIntegerField(blank=True, null=True)
    age_max = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    step_metadata = models.JSONField(default=list, blank=True, help_text=_("Ordered step definitions for dynamic fields"))
    layout_config = models.JSONField(default=dict, blank=True, help_text=_("Global layout configuration for dynamic steps"))

    class Meta:
        unique_together = ('program', 'title')
        ordering = ['program', 'age_min']

    def __str__(self):
        return f"{self.program.name} – {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            counter = 1
            while ProgramForm.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_form_for_program(cls, program):
        """
        Get the active form for a program.
        Returns the active form or None if no active form exists.
        """
        try:
            return cls.objects.get(program=program, is_active=True)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # If somehow multiple active forms exist, return the first one and log warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Multiple active forms found for program {program.id}. Using the first one.")
            return cls.objects.filter(program=program, is_active=True).first()


class FormField(models.Model):
    """
    Field within a ProgramForm, supports conditional display logic.
    """
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('email', 'Email'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('dropdown', 'Dropdown'),
        ('radio', 'Radio Button'),
        ('checkbox', 'Checkbox'),
        ('file', 'File Upload'),
        ('url', 'URL'),
        ('phone', 'Phone'),
    ]

    form = models.ForeignKey(ProgramForm, on_delete=models.CASCADE, related_name='fields')
    field_name = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    is_required = models.BooleanField(default=False)
    help_text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    options = models.JSONField(blank=True, null=True, help_text="Used for dropdown/radio/checkbox")
    max_length = models.PositiveIntegerField(null=True, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    allowed_file_types = models.JSONField(blank=True, null=True)
    max_file_size = models.PositiveIntegerField(blank=True, null=True)
    conditional_logic = models.JSONField(blank=True, null=True, help_text="Rules for showing this field")
    step_key = models.CharField(max_length=120, blank=True, default='', help_text="Identifier of the step this field belongs to")
    column_span = models.PositiveSmallIntegerField(default=4, help_text="Width of the field within a 4-column grid (1-4)")

    class Meta:
        ordering = ['order', 'id']
        unique_together = ['form', 'field_name']

    def __str__(self):
        return f"{self.form.title}: {self.label}"

    def clean(self):
        if self.field_type in ['dropdown', 'radio'] and not self.options:
            raise ValidationError(f"{self.field_type} fields must include options.")
        if self.field_type not in ['dropdown', 'radio', 'checkbox'] and self.options:
            raise ValidationError(f"{self.field_type} should not have options.")
        if self.field_type == 'number' and self.min_value is not None and self.max_value is not None:
            if self.min_value >= self.max_value:
                raise ValidationError("Minimum value must be less than maximum value.")
        if self.column_span < 1 or self.column_span > 4:
            raise ValidationError("Column span must be between 1 and 4.")


class FormResponse(models.Model):
    form = models.ForeignKey(ProgramForm, on_delete=models.CASCADE, related_name='responses')
    registration = models.ForeignKey('register.Registration', on_delete=models.CASCADE, related_name='form_responses', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    def __str__(self):
        target = f"Registration {self.registration_id}" if self.registration_id else 'anonymous'
        return f"Response {self.id} to {self.form.title} ({target})"


class FormResponseEntry(models.Model):
    response = models.ForeignKey(FormResponse, on_delete=models.CASCADE, related_name='entries')
    field = models.ForeignKey(FormField, on_delete=models.CASCADE)
    value = models.TextField(blank=True)
    file_upload = models.FileField(upload_to='form_uploads/', null=True, blank=True)

    def __str__(self):
        return f"{self.response} - {self.field.field_name}"

    def clean(self):
        if self.field.field_type == 'file':
            if not self.file_upload:
                raise ValidationError("File upload required for this field")
        else:
            if not self.value:
                raise ValidationError("Non-file fields require a value")


class Registration(BaseModel):
    """
    Ties a Participant to a Program, capturing all program-specific details
    including payment, age at enrollment, school snapshot, and responsible guardian.
    """
    class Status(models.TextChoices):
        PENDING       = 'pending',       _('Pending')
        PARTIALLY_PAID= 'partially_paid',_('Partially Paid')
        PAID          = 'paid',          _('Paid')
        CANCELLED     = 'cancelled',     _('Cancelled')
        REFUNDED      = 'refunded',      _('Refunded')


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
        max_length=20,  # Increased to accommodate 'partially_paid'
        choices=Status.choices,
        default=Status.PENDING
    )
    category_value = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text=_("Participant-chosen category for this program (matches Program.category_options if provided).")
    )


    class Meta:
        verbose_name = _('Registration')
        verbose_name_plural = _('Registrations')
        unique_together = (('participant', 'program'),)
        ordering = ['-created_at']


    @property
    def amount_due(self) -> Decimal:
        fee = self.program.registration_fee or Decimal('0')
        paid = self.approvals.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        return fee - paid

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
    Handles post-processing to update related models (Registration, Receipt, Coupon).
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
    amount = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True,
        help_text="Portion of the registration fee paid in this approval."
    )
    created_by   = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approvals'
    )
    receipt      = models.OneToOneField(
        'Receipt',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approval'
    )
    coupon       = models.OneToOneField(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approval'
    )

    class Meta:
        verbose_name = _('Approval')
        verbose_name_plural = _('Approvals')
        ordering = ['created_at']

    def __str__(self):
        return f"Approval({self.status}) for {self.registration}"

    def save(self, *args, **kwargs):
        # Default unpaid amount → full balance at save time
        if self.status == self.Status.PAID and self.amount is None:
            full_due = self.registration.amount_due
            self.amount = full_due if full_due > Decimal('0') else Decimal('0')
        super().save(*args, **kwargs)

    def post_process(self):
        reg = self.registration
        old_status = reg.status

        # ——— Valid transitions ———
        if self.status == self.Status.CANCELLED and old_status in [self.Status.PAID, Registration.Status.PAID]:
            raise ValidationError("Cannot cancel a registration that is already paid.")
        if self.status == self.Status.PAID and old_status in [self.Status.CANCELLED, Registration.Status.CANCELLED]:
            raise ValidationError("Cannot mark a cancelled registration as paid.")
        if self.status == self.Status.REFUNDED and old_status not in [self.Status.PAID, Registration.Status.PAID]:
            raise ValidationError("Only paid registrations can be refunded.")
        # ——— End validations ———

        # Side-effects for payment
        if self.status == self.Status.PAID:
            paid_amount = self.amount
            # Calculate amount_due EXCLUDING this approval (since it's already saved)
            # Only count PAID approvals
            fee = reg.program.registration_fee or Decimal('0')
            paid_before_this = reg.approvals.filter(status='paid').exclude(pk=self.pk).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
            amount_due_before = fee - paid_before_this
            
            if paid_amount > amount_due_before:
                raise ValidationError("Cannot pay more than the amount due.")

            # Create receipt for this payment
            receipt = Receipt.objects.create(
                registration=reg,
                issued_by=self.created_by,
                amount=paid_amount,
                status=Receipt.Status.PAID
            )
            self.receipt = receipt

            # Calculate new amount due after this payment
            # Re-fetch to get updated amount_due property
            reg.refresh_from_db()
            remaining_balance = reg.amount_due

            # Determine new registration status
            if remaining_balance <= Decimal('0'):
                # Fully paid
                reg.status = Registration.Status.PAID
                
                # Issue coupon/ticket only if fully paid and program requires it
                if reg.program.requires_ticket:
                    # Check if coupon doesn't already exist
                    if not Coupon.objects.filter(registration=reg).exists():
                        coupon = Coupon.objects.create(
                            registration=reg,
                            status=Coupon.Status.PAID
                        )
                        self.coupon = coupon
            else:
                # Partial payment - balance remains
                reg.status = Registration.Status.PARTIALLY_PAID
            
            reg.save(update_fields=['status'])

        elif self.status == self.Status.CANCELLED:
            # Cancel registration
            reg.status = Registration.Status.CANCELLED
            reg.save(update_fields=['status'])

        elif self.status == self.Status.REFUNDED:
            # Refund any linked receipt & coupon
            if self.receipt:
                self.receipt.status = Receipt.Status.REFUNDED
                self.receipt.save(update_fields=['status'])
            if self.coupon:
                self.coupon.status = Coupon.Status.REFUNDED
                self.coupon.save(update_fields=['status'])
            
            reg.status = Registration.Status.REFUNDED
            reg.save(update_fields=['status'])

        # Persist updated foreign-keys on this Approval
        update_fields = []
        if self.receipt_id:
            update_fields.append('receipt')
        if self.coupon_id:
            update_fields.append('coupon')
        if update_fields:
            self.save(update_fields=update_fields)

        return self
