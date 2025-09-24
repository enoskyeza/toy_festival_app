from django.contrib import admin
from .models import MainCategory, JudgingCriteria, Score, JudgeComment, Point

@admin.register(MainCategory)
class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(JudgingCriteria)
class JudgingCriteriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category',)
    list_filter = ('category',)
    search_fields = ('name', 'category__name')
    ordering = ('category', 'name')


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'judge', 'contestant', 'criteria', 'score', 'created_at')
    list_filter = ('judge', 'contestant', 'criteria')
    search_fields = ('judge__username', 'contestant__identifier', 'criteria__name')
    autocomplete_fields = ('judge', 'contestant', 'criteria')
    ordering = ('-created_at',)
    list_select_related = ('judge', 'contestant', 'criteria')

@admin.register(Point)
class PointAdmin(admin.ModelAdmin):
    list_display = ('id', 'judge', 'participant', 'criteria', 'score', 'created_at')
    list_filter = ('judge', 'participant', 'criteria')
    search_fields = ('judge__username', 'participant__identifier', 'criteria__name')
    autocomplete_fields = ('judge', 'participant', 'criteria')
    ordering = ('-created_at',)
    list_select_related = ('judge', 'participant', 'criteria')


@admin.register(JudgeComment)
class JudgeCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'judge', 'participant', 'comment', 'created_at')
    list_filter = ('judge', 'participant')
    search_fields = ('judge__username', 'participant__identifier', 'comment')
    autocomplete_fields = ('judge', 'participant')
    ordering = ('-created_at',)
    list_select_related = ('judge', 'participant')




# @admin.register(MainCategory)
# class MainCategoryAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name')
#
# @admin.register(JudgingCriteria)
# class JudgingCriteriaAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'category')
#
# @admin.register(Score)
# class ScoreAdmin(admin.ModelAdmin):
#     list_display = ('id', 'judge', 'contestant', 'criteria', 'score')
#     list_filter = ('judge', 'contestant', 'criteria')
#
# @admin.register(JudgeComment)
# class JudgeCommentAdmin(admin.ModelAdmin):
#     list_display = ('id', 'judge', 'contestant', 'comment')
#     list_filter = ('judge', 'contestant')

