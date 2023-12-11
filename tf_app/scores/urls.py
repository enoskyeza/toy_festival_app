from django.urls import path

from . import views

app_name = 'score'

urlpatterns = [
    path('<int:contestant_id>', views.submit_score, name='submit-scores'),
    path('update/<int:contestant_id>', views.update_score, name='update-scores'),
    path('details/<int:contestant_id>', views.contestant_scores, name='contestant-scores'),
    # path('success', views.contestant_scores, name='success'),
]
