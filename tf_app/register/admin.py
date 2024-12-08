from django.contrib import admin
from .models import Payment, Parent, Contestant, Ticket


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
