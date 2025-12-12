from django.urls import path, include
from rest_framework import routers
from .views import (
    SchoolViewSet, GuardianViewSet, ParticipantViewSet, ProgramTypeViewSet,
    ProgramViewSet, RegistrationViewSet, SelfRegistrationAPIView, ReceiptViewSet,
    ApprovalViewSet, ProgramFormViewSet
)

router = routers.DefaultRouter()
router.register(r'schools', SchoolViewSet)
router.register(r'guardians', GuardianViewSet)
router.register(r'participants', ParticipantViewSet)
router.register(r'program-types', ProgramTypeViewSet)
router.register(r'programs', ProgramViewSet)
router.register(r'registrations', RegistrationViewSet)
router.register(r'receipts', ReceiptViewSet)
router.register(r'approvals', ApprovalViewSet)
router.register(r'program_forms', ProgramFormViewSet)
router.register(r'forms', ProgramFormViewSet, basename='forms')




urlpatterns = [
    path('self-register/', SelfRegistrationAPIView.as_view(), name='self-register'),
    path('', include(router.urls)),
]
