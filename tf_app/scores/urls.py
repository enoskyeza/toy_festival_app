from django.urls import path

from . import views

app_name = 'score'

urlpatterns = [
    path('score/<int:contestant_id>', views.submit_score, name='submit-scores'),
    path('score/<int:contestant_id>', views.contestant_scores, name='contestant-scores'),
]
