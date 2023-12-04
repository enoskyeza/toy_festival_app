from django.contrib import admin
from .models import Payment, Parent, Contestant


# Individual Register nnormal.

# admin.site.register(Parent)
# admin.site.register(Payment)
# admin.site.register(Contestant)

# Individual Register Customized.

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone_number', 'address', 'proffession')
    list_filter = ('proffession',)
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    # Other customizations can be added here

@admin.register(Contestant)
class ContestantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'age', 'gender', 'school', 'payment_status')
    list_filter = ('gender', 'school', 'payment_status')
    search_fields = ('first_name', 'last_name', 'email', 'school')
    # Other customizations can be added here

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('pay_type', 'pay_status')
    list_filter = ('pay_type', 'pay_status')
    search_fields = ('pay_type',)
    # Other customizations can be added here

# Multiple Register.

# models_to_register = [Payment, Parent, Contestant]

# for model in models_to_register:
#     admin.site.register(Parent)