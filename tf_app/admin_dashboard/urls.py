from django.urls import path

from . import views

app_name = "admin_dashboard"
urlpatterns = [
    path("", views.index, name='dashboard')
]
