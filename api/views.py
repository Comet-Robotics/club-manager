from django.contrib.auth.models import User
from .serializers import (
    UserSerializer,
    ProductSerializer,
    EventSerializer,
)
from rest_framework import viewsets, status, serializers
from .permissions import IsOwnerOrStaff, DeleteNotAllowed, ReadOnlyView

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from events.models import Event


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerOrStaff, DeleteNotAllowed]
    serializer_class = UserSerializer
    queryset = User.objects.all()


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()


class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyView]
    serializer_class = EventSerializer
    queryset = Event.objects.all()


def get_csrf(request):
    response = JsonResponse({"detail": "CSRF cookie set"})
    response["X-CSRFToken"] = get_token(request)
    return response


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class LoginResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LoginView(APIView):
    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer, 401: LoginResponseSerializer},
        description="Login with username and password",
    )
    def post(self, request):
        data = request.data
        username = data.get("username")
        password = data.get("password")

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        return Response({"detail": "Successfully logged in."})


class LogoutResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class LogoutView(APIView):
    @extend_schema(
        responses={200: LogoutResponseSerializer, 400: LogoutResponseSerializer}, description="Logout current user"
    )
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "You're not logged in."}, status=status.HTTP_400_BAD_REQUEST)

        logout(request)
        return Response({"detail": "Successfully logged out."})


class SessionResponseSerializer(serializers.Serializer):
    isAuthenticated = serializers.BooleanField()


class SessionView(APIView):
    @extend_schema(responses={200: SessionResponseSerializer}, description="Check if user is authenticated")
    @ensure_csrf_cookie
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"isAuthenticated": False})

        return Response({"isAuthenticated": True})


class WhoAmIView(APIView):
    @extend_schema(
        responses={
            403: {
                "type": "object",
                "properties": {"isAuthenticated": {"type": "boolean", "enum": [False]}},
                "required": ["isAuthenticated"],
            },
            200: {
                "type": "object",
                "properties": {
                    "isAuthenticated": {"type": "boolean", "enum": [True]},
                    "username": {"type": "string"},
                    "id": {"type": "integer"},
                },
                "required": ["isAuthenticated", "username", "id"],
            },
        },
        description="Get current user information",
    )
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"isAuthenticated": False}, status=status.HTTP_403_FORBIDDEN)

        return Response({"username": request.user.username, "id": request.user.id, "isAuthenticated": True})
