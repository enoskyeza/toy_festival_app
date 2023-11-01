from django.contrib import admin
from .models import Payment, Parent, Child


# Individual Register nnormal.

admin.site.register(Parent)
admin.site.register(Payment)
admin.site.register(Child)

# Individual Register Customized.

# @admin.register(Parent)
# class ParentAdmin(admin.ModelAdmin):
#     list_display = ('first_name', 'last_name', 'email', 'phone_number', 'address', 'profession')
#     list_filter = ('profession',)
#     search_fields = ('first_name', 'last_name', 'email', 'phone_number')
#     # Other customizations can be added here

# @admin.register(Child)
# class ChildAdmin(admin.ModelAdmin):
#     list_display = ('first_name', 'last_name', 'email', 'age', 'gender', 'school', 'payment_status')
#     list_filter = ('gender', 'school', 'payment_status')
#     search_fields = ('first_name', 'last_name', 'email', 'school')
#     # Other customizations can be added here

# @admin.register(Payment)
# class PaymentAdmin(admin.ModelAdmin):
#     list_display = ('type', 'status')
#     list_filter = ('type', 'status')
#     search_fields = ('type',)
#     # Other customizations can be added here

# Multiple Register.

# models_to_register = [Payment, Parent, Child]

# for model in models_to_register:
#     admin.site.register(Parent)