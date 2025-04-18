from django.contrib import admin
from .models import (
    Payment, Parent, Contestant, Ticket,
    School, Guardian, Participant, ParticipantGuardian,
    Program, Registration, Receipt, Coupon, Approval, ProgramType
)


# Individual Register normal.

# admin.site.register(Parent)
# admin.site.register(Payment)
# admin.site.register(Contestant)

# Individual Register Customized.

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone_number', 'address', 'profession')
    list_filter = ('profession',)
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    # Other customizations can be added here

@admin.register(Contestant)
class ContestantAdmin(admin.ModelAdmin):
    list_display = ('identifier','first_name', 'last_name', 'email', 'age', 'gender', 'school', 'payment_status','payment_method', 'age_category')
    list_filter = ('gender', 'school', 'payment_status', 'payment_method', 'age_category')
    search_fields = ('first_name', 'last_name', 'email', 'school')
    # Other customizations can be added here

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_method']
    list_filter = ['payment_method']
    search_fields = ['payment_method']
    # Other customizations can be added here

# Multiple Register.

# models_to_register = [Payment, Parent, Contestant]

# for model in models_to_register:
#     admin.site.register(Parent)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('participant', 'created_at', 'qr_code')



@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone_number')
    search_fields = ('name', 'email', 'phone_number')


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'phone_number')
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'gender', 'date_of_birth', 'current_school')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('gender', 'current_school')
    ordering = ('id', )


@admin.register(ParticipantGuardian)
class ParticipantGuardianAdmin(admin.ModelAdmin):
    list_display = ('participant', 'guardian', 'relationship', 'is_primary')
    list_filter = ('relationship', 'is_primary')
    search_fields = ('participant__first_name', 'participant__last_name', 'guardian__first_name', 'guardian__last_name')



@admin.register(ProgramType)
class ProgramTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('id', 'name','type','year', 'start_date', 'end_date', 'registration_fee', 'requires_ticket')
    search_fields = ('name',)
    list_filter = ('requires_ticket','type', 'year')


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant', 'program', 'status', 'age_at_registration')
    search_fields = ('participant__first_name', 'participant__last_name', 'program__name')
    list_filter = ('status', 'program')


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'registration', 'issued_by', 'amount', 'status')
    search_fields = ('registration__participant__first_name', 'registration__participant__last_name')
    list_filter = ('status',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'registration', 'status')
    list_filter = ('status',)


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ('id', 'registration', 'status', 'created_by', 'receipt', 'coupon')
    list_filter = ('status',)
    search_fields = ('registration__participant__first_name', 'registration__participant__last_name')

