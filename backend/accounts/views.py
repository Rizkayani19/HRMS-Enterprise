from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog
from .permissions import user_role


def _me(user):
    return {"username": user.username, "full_name": user.get_full_name() or user.username, "role": user_role(user)}


class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(request, username=request.data.get("username"), password=request.data.get("password"))
        if not user:
            return Response({"detail": "Invalid username or password."}, status=400)
        login(request, user)
        AuditLog.record(user, "login", user.username)
        return Response(_me(user))


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({"ok": True})


class MeView(APIView):
    def get(self, request):
        return Response(_me(request.user))


class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", default="system")

    class Meta:
        model = AuditLog
        fields = "__all__"


class AuditLogView(APIView):
    def get(self, request):
        return Response(AuditLogSerializer(AuditLog.objects.select_related("user")[:200], many=True).data)
