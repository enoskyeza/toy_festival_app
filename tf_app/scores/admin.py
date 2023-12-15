from django.contrib import admin
from .models import MainCategory, JudgingCriteria, Score, JudgeComment


# Individual Register normal.

class JudgingCriteriaInline(admin.TabularInline):
    model = JudgingCriteria
    extra = 4  # Number of inline forms to display

class MainCategoryAdmin(admin.ModelAdmin):
    inlines = [JudgingCriteriaInline]


admin.site.register(MainCategory, MainCategoryAdmin)
admin.site.register(JudgingCriteria)

@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('judge', 'contestant', 'criteria', 'score' )
    list_filter = ('judge', 'contestant', 'criteria')
    search_fields = ('judge', 'contestant', 'criteria')
    # Other customizations can be added here

@admin.register(JudgeComment)
class JudgeCommentAdmin(admin.ModelAdmin):
    list_display = ('judge', 'contestant', 'comment' )
    list_filter = ('judge', 'contestant')
    search_fields = ('judge', 'contestant')
    # Other customizations can be added here