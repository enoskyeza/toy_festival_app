from django.urls import path

from . import views
from .views import RegistrationView

app_name = 'register'

urlpatterns = [
    path('', views.home, name='home-page'),
    path('register/', RegistrationView.as_view(), name='register-page'),
    path('success/<int:contestant_id>/', views.success_page, name='success-page' ),
    path('list/', views.contestant_list_view, name='contestant-list' ),
]
