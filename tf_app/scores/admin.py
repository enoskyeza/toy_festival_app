from django.contrib import admin
from .models import MainCategory, JudgingCriteria, Score


# Individual Register normal.

class JudgingCriteriaInline(admin.TabularInline):
    model = JudgingCriteria
    extra = 4  # Number of inline forms to display

class MainCategoryAdmin(admin.ModelAdmin):
    inlines = [JudgingCriteriaInline]


admin.site.register(MainCategory, MainCategoryAdmin)
admin.site.register(JudgingCriteria)
admin.site.register(Score)
