from django.urls import path
from . import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'authors', views.AuthorViewSet)
router.register(r'posts', views.PostViewSet)
router.register(r'comments', views.CommentViewSet)

urlpatterns = [
                  path('post/<int:pk>/like/', views.PostViewSet.as_view({'post': 'like'}), name='like-post'),
              ] + router.urls
