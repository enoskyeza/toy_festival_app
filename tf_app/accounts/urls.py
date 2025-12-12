from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginView, JudgeViewSet

router = DefaultRouter()
router.register(r'judges', JudgeViewSet, basename='judge')

urlpatterns = [
    path('', LoginView.as_view(), name='login'),
    path('', include(router.urls)),
    # path('logout/', LogoutView.as_view(), name='logout'),
]
