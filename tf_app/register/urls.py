from rest_framework import routers
from .views import PaymentViewSet, ContestantViewSet, ParentViewSet, TicketViewSet

router = routers.DefaultRouter()
router.register(r'payments', PaymentViewSet)
router.register(r'contestants', ContestantViewSet)
router.register(r'parents', ParentViewSet)
router.register(r'tickets', TicketViewSet)

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
