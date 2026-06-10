from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.services import log_event

from .models import User
from .permissions import ADMIN_ONLY, ELEVATED, RolePermission
from .serializers import (
    ChangePasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=settings.REFRESH_COOKIE_PATH,
        secure=settings.REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH
    )


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class LoginView(APIView):
    """POST {username, password} -> {access, user}; refresh token only in
    an httpOnly cookie so XSS can never exfiltrate it."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        try:
            valid = serializer.is_valid()
        except AuthenticationFailed:
            # SimpleJWT raises (rather than returning False) for bad
            # credentials and inactive accounts alike.
            valid = False
        if not valid:
            log_event(
                request,
                action="login_fail",
                model="accounts.User",
                object_repr=str(request.data.get("username", ""))[:64],
            )
            return Response(
                {"detail": "نام کاربری یا کلمه عبور اشتباه است."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        user = serializer.user
        data = serializer.validated_data
        response = Response(
            {"access": data["access"], "user": UserSerializer(user).data}
        )
        _set_refresh_cookie(response, data["refresh"])
        log_event(request, action="login_ok", actor=user, model="accounts.User",
                  object_id=str(user.pk), object_repr=user.username)
        return response


class RefreshView(APIView):
    """Rotate the refresh token from the httpOnly cookie; return new access."""

    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "refresh"

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            return Response(
                {"detail": "نشست معتبر نیست."}, status=status.HTTP_401_UNAUTHORIZED
            )
        serializer = TokenRefreshSerializer(data={"refresh": raw})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            response = Response(
                {"detail": "نشست منقضی شده است."}, status=status.HTTP_401_UNAUTHORIZED
            )
            _clear_refresh_cookie(response)
            return response
        data = serializer.validated_data
        response = Response({"access": data["access"]})
        # ROTATE_REFRESH_TOKENS=True -> serializer returns a new refresh token.
        if data.get("refresh"):
            _set_refresh_cookie(response, data["refresh"])
        return response


class LogoutView(APIView):
    """Blacklist the refresh token and clear its cookie."""

    permission_classes = []  # allow logout even with an expired access token

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_event(request, action="update", model="accounts.User",
                  object_id=str(request.user.pk), object_repr=request.user.username,
                  changes={"password": "changed"})
        return Response({"detail": "کلمه عبور با موفقیت تغییر کرد."})


class UserViewSet(viewsets.ModelViewSet):
    """User management: Admin full CRUD, QA Lead read-only."""

    queryset = User.objects.all()
    permission_classes = [RolePermission]
    allowed_roles = {
        "list": ELEVATED,
        "retrieve": ELEVATED,
        "create": ADMIN_ONLY,
        "update": ADMIN_ONLY,
        "partial_update": ADMIN_ONLY,
        "destroy": ADMIN_ONLY,
    }

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        # Never hard-delete users: history/audit must stay attributable.
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        log_event(self.request, action="update", model="accounts.User",
                  object_id=str(instance.pk), object_repr=instance.username,
                  changes={"is_active": False})
