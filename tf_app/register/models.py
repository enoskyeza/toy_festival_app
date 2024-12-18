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
        'register.Contestant',  # Replace with your actual Participant model's app name
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