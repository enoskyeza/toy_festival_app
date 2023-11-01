from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import EmailValidator, MinLengthValidator



class Payment(models.Model):
    class PaymentType(models.TextChoices):
        mobile_money = "mm", ("MOBILE_MONEY")
        cash = 'cash', ("CASH")

    class PaymentStatus(models.TextChoices):
        PAID = 'PAID', ('PAID')
        NOT_PAID = 'NOT_PAID', ('NOT_PAID')

    pay_type = models.CharField(max_length=15, choices=PaymentType.choices)
    pay_status = models.CharField(max_length=15, choices=PaymentStatus.choices)


class Child(models.Model):

    class ChildGender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')


    first_name = models.CharField(max_length=100)
    second_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, blank='True')
    age = models.IntegerField()
    gender = models.CharField(max_length=1, choices=ChildGender.choices)
    school = models.CharField(max_length=100)
    payment_status = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    parent = models.ForeignKey('Parent', on_delete=models.SET_NULL, blank=False, null=True)

    def __str__(self):
        return f'{self.first_name} {self.second_name}'


class Parent(models.Model):
    first_name = models.CharField(max_length=100)
    second_name = models.CharField(max_length=100)
    proffession = models.CharField(max_length=100)
    address = models.CharField(max_length=100)

    # Email & Number Validator if they are required fields
    email = models.EmailField(
        max_length=254,
        validators=[EmailValidator(message="Invalid email address")]
    )
    phone_number = models.CharField(
        max_length=13,
        validators=[MinLengthValidator(10, message="Phone number must have at least 10 digits")]
    )

    def __str__(self):
        return f'{self.first_name} {self.second_name}'

class Judge:
    pass