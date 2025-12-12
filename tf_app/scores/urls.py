from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MainCategoryViewSet, JudgingCriteriaViewSet,
    PointViewSet, BulkPointView, ParticipantCommentViewSet,
    RubricCategoryViewSet, RubricViewSet, RubricCriteriaViewSet,
    ScoringConfigurationViewSet, JudgeAssignmentViewSet,
    JudgingScoreViewSet, ConflictOfInterestViewSet,
    LeaderboardView, ProgramScoresSummaryView
)

# Set up the router
router = DefaultRouter()
router.register(r'categories', MainCategoryViewSet, basename='maincategory')
router.register(r'criteria', JudgingCriteriaViewSet, basename='criteria')

# New judging system endpoints
router.register(r'points', PointViewSet, basename='points')
router.register(r'participant-comments', ParticipantCommentViewSet, basename='participant-comments')
router.register(r'comments', ParticipantCommentViewSet, basename='comments')  # Alias for frontend

# Phase 2: New judging system models
router.register(r'rubric-categories', RubricCategoryViewSet, basename='rubric-category')
router.register(r'rubrics', RubricViewSet, basename='rubric')
router.register(r'rubric-criteria', RubricCriteriaViewSet, basename='rubric-criteria')
router.register(r'scoring-configs', ScoringConfigurationViewSet, basename='scoring-config')
router.register(r'judge-assignments', JudgeAssignmentViewSet, basename='judge-assignment')
router.register(r'judging-scores', JudgingScoreViewSet, basename='judging-score')
router.register(r'conflicts', ConflictOfInterestViewSet, basename='conflict')

# Include the router URLs
urlpatterns = [
    path('', include(router.urls)),
    path('upload-points/', BulkPointView.as_view(), name='bulk_point_upload'),
    path('leaderboard/<int:program_id>/', LeaderboardView.as_view(), name='leaderboard'),
    path('programs-summary/', ProgramScoresSummaryView.as_view(), name='programs_summary'),
]
