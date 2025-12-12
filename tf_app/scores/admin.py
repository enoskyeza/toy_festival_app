from django.contrib import admin
from .models import (
    MainCategory, JudgingCriteria, JudgeComment, Point,
    RubricCategory, Rubric, RubricCriteria, ScoringConfiguration,
    JudgeAssignment, JudgingScore, ConflictOfInterest
)

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


# ============================================================================
# PHASE 2: NEW JUDGING SYSTEM ADMIN
# ============================================================================


@admin.register(RubricCategory)
class RubricCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'icon')
    search_fields = ('name', 'description')
    ordering = ('order', 'name')
    list_editable = ('order',)


class RubricCriteriaInline(admin.TabularInline):
    model = RubricCriteria
    extra = 1
    fields = ('category', 'name', 'description', 'guidelines', 'max_score', 'weight', 'order')
    autocomplete_fields = ('category',)


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ('name', 'program', 'is_active', 'criteria_count', 'total_possible_points', 'created_at')
    search_fields = ('name', 'program__name', 'description')
    list_filter = ('is_active', 'program', 'created_at')
    autocomplete_fields = ('program', 'created_by')
    readonly_fields = ('criteria_count', 'created_at', 'updated_at')
    inlines = [RubricCriteriaInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('program', 'name', 'description', 'is_active')
        }),
        ('Scoring', {
            'fields': ('total_possible_points', 'criteria_count')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RubricCriteria)
class RubricCriteriaAdmin(admin.ModelAdmin):
    list_display = ('name', 'rubric', 'category', 'max_score', 'weight_percentage', 'order')
    search_fields = ('name', 'description', 'rubric__name')
    list_filter = ('category', 'rubric')
    autocomplete_fields = ('rubric', 'category')
    ordering = ('category__order', 'order', 'name')
    list_editable = ('order',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('rubric', 'category', 'name', 'description')
        }),
        ('Scoring Details', {
            'fields': ('max_score', 'weight', 'guidelines')
        }),
        ('Display', {
            'fields': ('order',)
        }),
    )


@admin.register(ScoringConfiguration)
class ScoringConfigurationAdmin(admin.ModelAdmin):
    list_display = ('program', 'scoring_start', 'scoring_end', 'calculation_method', 'is_scoring_active')
    search_fields = ('program__name',)
    list_filter = ('calculation_method', 'allow_revisions', 'show_scores_to_participants')
    autocomplete_fields = ('program',)
    readonly_fields = ('is_scoring_active', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Program', {
            'fields': ('program',)
        }),
        ('Timing', {
            'fields': ('scoring_start', 'scoring_end', 'is_scoring_active')
        }),
        ('Judge Requirements', {
            'fields': ('min_judges_required', 'max_judges_per_participant')
        }),
        ('Calculation Method', {
            'fields': ('calculation_method', 'top_n_count')
        }),
        ('Revisions', {
            'fields': ('allow_revisions', 'revision_deadline', 'max_revisions_per_score')
        }),
        ('Visibility', {
            'fields': ('show_scores_to_participants', 'scores_visible_after')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(JudgeAssignment)
class JudgeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('judge', 'program', 'category_value', 'status', 'participants_scored', 'completion_percentage', 'assigned_at')
    search_fields = ('judge__username', 'program__name', 'category_value', 'notes')
    list_filter = ('status', 'program', 'assigned_at')
    autocomplete_fields = ('program', 'judge', 'assigned_by')
    readonly_fields = ('participants_scored', 'completion_percentage', 'assigned_at')
    list_editable = ('status',)
    
    fieldsets = (
        ('Assignment', {
            'fields': ('program', 'judge', 'category_value', 'status')
        }),
        ('Workload', {
            'fields': ('max_participants', 'participants_scored', 'completion_percentage')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['pause_assignments', 'resume_assignments', 'mark_completed']
    
    def pause_assignments(self, request, queryset):
        queryset.update(status='PAUSED')
        self.message_user(request, f"{queryset.count()} assignments paused")
    pause_assignments.short_description = "Pause selected assignments"
    
    def resume_assignments(self, request, queryset):
        queryset.update(status='ACTIVE')
        self.message_user(request, f"{queryset.count()} assignments resumed")
    resume_assignments.short_description = "Resume selected assignments"
    
    def mark_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
        self.message_user(request, f"{queryset.count()} assignments marked as completed")
    mark_completed.short_description = "Mark as completed"


@admin.register(JudgingScore)
class JudgingScoreAdmin(admin.ModelAdmin):
    list_display = ('judge', 'registration_participant', 'criteria', 'raw_score', 'max_score', 'score_percentage', 'submitted_at')
    search_fields = ('judge__username', 'registration__participant__first_name', 'registration__participant__last_name', 'notes')
    list_filter = ('program', 'judge', 'submitted_at', 'revision_number')
    autocomplete_fields = ('program', 'registration', 'judge', 'criteria')
    readonly_fields = ('score_percentage', 'weighted_score', 'submitted_at', 'updated_at')
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Score Details', {
            'fields': ('program', 'registration', 'judge', 'criteria')
        }),
        ('Score Values', {
            'fields': ('raw_score', 'max_score', 'score_percentage', 'weighted_score')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Revision Tracking', {
            'fields': ('revision_number', 'previous_score', 'revision_reason'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('submitted_at', 'updated_at', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def registration_participant(self, obj):
        return obj.registration.participant
    registration_participant.short_description = 'Participant'
    registration_participant.admin_order_field = 'registration__participant'


@admin.register(ConflictOfInterest)
class ConflictOfInterestAdmin(admin.ModelAdmin):
    list_display = ('judge', 'participant', 'relationship_type', 'status', 'flagged_at', 'reviewed_by')
    search_fields = ('judge__username', 'participant__first_name', 'participant__last_name', 'description')
    list_filter = ('status', 'relationship_type', 'flagged_at', 'reviewed_at')
    autocomplete_fields = ('judge', 'participant', 'flagged_by', 'reviewed_by')
    readonly_fields = ('flagged_at', 'reviewed_at')
    list_editable = ('status',)
    date_hierarchy = 'flagged_at'
    
    fieldsets = (
        ('Conflict Details', {
            'fields': ('judge', 'participant', 'relationship_type', 'description')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Flagged By', {
            'fields': ('flagged_by', 'flagged_at')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_conflicts', 'reject_conflicts']
    
    def approve_conflicts(self, request, queryset):
        queryset.update(status='APPROVED', reviewed_by=request.user)
        self.message_user(request, f"{queryset.count()} conflicts approved")
    approve_conflicts.short_description = "Approve selected conflicts"
    
    def reject_conflicts(self, request, queryset):
        queryset.update(status='REJECTED', reviewed_by=request.user)
        self.message_user(request, f"{queryset.count()} conflicts rejected")
    reject_conflicts.short_description = "Reject selected conflicts"
