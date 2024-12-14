from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MainCategoryViewSet, JudgingCriteriaViewSet, ScoreViewSet, JudgeCommentViewSet, ScoreListAPIView, ScoreReadOnlyViewSet, ContestantDetailViewSet, BulkScoreView, ResultsView, ResultsListView

# Set up the router
router = DefaultRouter()
router.register(r'categories', MainCategoryViewSet, basename='maincategory')
router.register(r'criteria', JudgingCriteriaViewSet, basename='criteria')
router.register(r'scores', ScoreViewSet, basename='score')
router.register(r'score-dets', ScoreReadOnlyViewSet, basename='dets')
router.register(r'participant-dets', ContestantDetailViewSet, basename='participant-dets')
router.register(r'comments', JudgeCommentViewSet, basename='judgecomment')

# Include the router URLs
urlpatterns = [
    path('', include(router.urls)),
    path('upload-scores/', BulkScoreView.as_view(), name='bulk_score_upload'),
    path('results/', ResultsListView.as_view(), name='opt-results'),
    path('result/', ResultsView.as_view(), name='results'),
]
