from django.contrib import admin
from .models import MainCategory, JudgingCriteria, Score, JudgeComment

@admin.register(MainCategory)
class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(JudgingCriteria)
class JudgingCriteriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category')

@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'judge', 'contestant', 'criteria', 'score')
    list_filter = ('judge', 'contestant', 'criteria')

@admin.register(JudgeComment)
class JudgeCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'judge', 'contestant', 'comment')
    list_filter = ('judge', 'contestant')
