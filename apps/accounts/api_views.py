from django.contrib.auth import authenticate, login, logout
from rest_framework import permissions, response, status, views
from .serializers import UserSerializer


class SessionLoginAPI(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)
        if not user:
            return response.Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return response.Response(UserSerializer(user).data)


class SessionLogoutAPI(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return response.Response({"detail": "Logged out"})


class SessionMeAPI(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return response.Response(UserSerializer(request.user).data)
