from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login

from .serializers import LoginSerializer

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Login the user
        login(request, user)

        # Token creation (if using TokenAuthentication)
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            }
        }, status=status.HTTP_200_OK)


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