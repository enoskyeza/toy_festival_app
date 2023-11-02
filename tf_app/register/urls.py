from django.urls import path

from . import views
from .views import ParentCreateView

app_name = 'register'

urlpatterns = [
    path('', views.home, name='home-page'),
    path('register/', ParentCreateView.as_view(), name='register-page'),
    path('success/', views.success_page, name='success-page' )
]
