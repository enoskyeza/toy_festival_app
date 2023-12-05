from django.urls import path

from . import views

app_name = 'judge'

urlpatterns = [
    path('', views.judge_page, name='judge-page'),
    path('login/', views.judge_login, name='judge-login' ),
]

