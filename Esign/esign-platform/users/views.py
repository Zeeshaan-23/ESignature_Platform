# users/views.py

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from notifications.tasks import send_password_reset_email

_token_generator = PasswordResetTokenGenerator()

# ─── Cookie helpers ───────────────────────────────────────────────────────────

_SECURE = not settings.DEBUG  # True in production (HTTPS); False in dev


def _set_auth_cookies(response, refresh):
    """Attach access + refresh JWT as httpOnly cookies to *response*."""
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    access_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
    refresh_lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

    response.set_cookie(
        key='access_token',
        value=access_token,
        max_age=int(access_lifetime.total_seconds()),
        httponly=True,
        secure=_SECURE,
        samesite='Lax',
        path='/',
    )
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        max_age=int(refresh_lifetime.total_seconds()),
        httponly=True,
        secure=_SECURE,
        samesite='Lax',
        path='/api/users/',   # Scope to refresh endpoint path
    )
    return response


def _clear_auth_cookies(response):
    """Delete both JWT cookies."""
    response.delete_cookie('access_token', path='/')
    response.delete_cookie('refresh_token', path='/api/users/')
    return response


# ─── Auth views ───────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user and set httpOnly JWT cookies."""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    refresh = RefreshToken.for_user(user)

    response = Response(
        {'user': UserSerializer(user).data},
        status=status.HTTP_201_CREATED,
    )
    return _set_auth_cookies(response, refresh)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Authenticate with email + password; set httpOnly JWT cookies.
    Returns the user profile so the frontend has it immediately.
    """
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.check_password(password):
        return Response(
            {'error': 'Invalid credentials.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return Response(
            {'error': 'Account is disabled.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(user)
    response = Response({'user': UserSerializer(user).data}, status=status.HTTP_200_OK)
    return _set_auth_cookies(response, refresh)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Read the refresh token from the httpOnly cookie, rotate it, and
    set fresh access + refresh cookies.
    """
    raw_refresh = request.COOKIES.get('refresh_token')
    if not raw_refresh:
        return Response(
            {'error': 'No refresh token cookie present.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        refresh = RefreshToken(raw_refresh)
        # Rotating refresh token (invalidates old one)
        refresh.blacklist() if hasattr(refresh, 'blacklist') else None
        new_refresh = refresh
    except TokenError:
        return Response(
            {'error': 'Refresh token is invalid or expired.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    response = Response({'detail': 'Token refreshed.'}, status=status.HTTP_200_OK)
    return _set_auth_cookies(response, new_refresh)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """Clear both JWT cookies — effectively logs the user out."""
    response = Response({'detail': 'Logged out.'}, status=status.HTTP_200_OK)
    return _clear_auth_cookies(response)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Returns the currently authenticated user's profile."""
    return Response(UserSerializer(request.user).data)


# ─── Password reset ───────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    Accepts an email and sends a reset link if the account exists.
    Always returns 200 to prevent user enumeration.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    try:
        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = _token_generator.make_token(user)
        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        )
        send_password_reset_email.delay(email, reset_url)
    except User.DoesNotExist:
        pass  # silent — don't reveal whether email exists

    return Response(
        {'message': 'If that email is registered, a reset link has been sent.'},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """Validates uid + token, then sets the new password."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    uid = serializer.validated_data['uid']
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']

    try:
        user_pk = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_pk)
    except (User.DoesNotExist, ValueError, TypeError):
        return Response(
            {'error': 'Invalid reset link.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not _token_generator.check_token(user, token):
        return Response(
            {'error': 'Invalid or expired reset link.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save()

    return Response(
        {'message': 'Password has been reset successfully.'},
        status=status.HTTP_200_OK,
    )