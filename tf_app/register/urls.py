from rest_framework import routers
from .views import PaymentViewSet, ContestantViewSet, ParentViewSet

router = routers.DefaultRouter()
router.register(r'register/payments', PaymentViewSet)
router.register(r'register/contestants', ContestantViewSet)
router.register(r'register/parents', ParentViewSet)

urlpatterns = router.urls




# from django.urls import path
#
# from . import views
# from .views import RegistrationView
#
# app_name = 'register'
#
# urlpatterns = [
#     path('', views.home, name='home-page'),
#     path('reg/', RegistrationView.as_view(), name='register-page'),
#     path('success/<int:contestant_id>/', views.success_page, name='success-page' ),
#     path('list/', views.contestant_list_view, name='contestant-list' ),
# ]
