from django.urls import path

from . import views

app_name = 'judge'

urlpatterns = [
    path('login/', views.judge_login, name='judge-login' ),
]

