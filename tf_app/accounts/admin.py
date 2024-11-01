from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Staff, Judge

# @admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['id', "username","email", "first_name", "last_name", "role"]
    list_filter = ["role"]
    fieldsets = [
        (None, {"fields": ["username","email", "password"]}),
        ("Personal info", {"fields": ["first_name", "last_name"]}),
        (_('Permissions'), {
                     'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
                 }),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["username","first_name", "last_name", "email", "password1", "password2"],
            },
        ),
    ]
    search_fields = ["email","username"]
    ordering = ["username"]
    filter_horizontal = []

# class CustomUserAdmin(UserAdmin):
#     list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
#     search_fields = ('username', 'email', 'first_name', 'last_name')
#     list_filter = ('role', 'is_staff', 'is_active')
#     fieldsets = (
#         (None, {'fields': ('username', 'email', 'password')}),
#         (_('Personal info'), {'fields': ('first_name', 'last_name')}),
#         (_('Permissions'), {
#             'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
#         }),
#         (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
#         (_('Custom Fields'), {'fields': ('role',)}),
#     )
#
#     def save_model(self, request, obj, form, change):
#         # Use set_password if password is provided as plain text
#         if form.cleaned_data.get("password"):
#             obj.set_password(form.cleaned_data["password"])
#         super().save_model(request, obj, form, change)


admin.site.register(User, CustomUserAdmin)
admin.site.register(Staff, CustomUserAdmin)
admin.site.register(Judge, CustomUserAdmin)
