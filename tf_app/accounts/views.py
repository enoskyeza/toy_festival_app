from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from django.contrib.auth import authenticate, login
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .serializers import LoginSerializer, JudgeSerializer, JudgeCreateSerializer
from .models import User, Judge


class JudgeViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for managing judges.
    Soft delete is implemented by setting is_active=False.
    """
    queryset = User.objects.filter(role=User.Role.JUDGE).order_by('-id')
    serializer_class = JudgeSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['id', 'username', 'first_name', 'created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return JudgeCreateSerializer
        return JudgeSerializer
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete - set is_active to False instead of deleting."""
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted judge."""
        instance = self.get_object()
        instance.is_active = True
        instance.save(update_fields=['is_active'])
        return Response(JudgeSerializer(instance).data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active judges."""
        queryset = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

# class LoginView(APIView):
#     authentication_classes = []
#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         serializer = LoginSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data['user']

#         # Login the user
#         login(request, user)

#         # Token creation (if using TokenAuthentication)
#         token, created = Token.objects.get_or_create(user=user)

#         return Response({
#             "token": token.key,
#             "user": {
#                 "id": user.id,
#                 "username": user.username,
#                 "email": user.email,
#                 "role": user.role,
#             }
#         }, status=status.HTTP_200_OK)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            # Log validation errors for debugging
            print("Validation Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']

        try:
            # Login the user
            login(request, user)

            # Token creation
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                "token": token.key,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": getattr(user, 'role', None),
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # Log unexpected errors
            print("Unexpected Error:", str(e))
            return Response({"detail": "An error occurred. Please try again later."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class LogoutView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request, *args, **kwargs):
#         # Delete the user's token to effectively log them out (if using TokenAuthentication)
#         Token.objects.filter(user=request.user).delete()
#
#         # Logout the user
#         logout(request)
#
#         return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)