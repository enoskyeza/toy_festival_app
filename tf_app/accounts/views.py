from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login

from .serializers import LoginSerializer

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