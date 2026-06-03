# users/authentication.py

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """
    Reads the JWT access token from the 'access_token' httpOnly cookie
    instead of the Authorization header.  Falls back to the header so
    that DRF Browsable API / tests using force_authenticate() still work.
    """

    def authenticate(self, request):
        # 1. Try cookie first
        raw_token = request.COOKIES.get('access_token')

        if raw_token is not None:
            try:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token
            except (InvalidToken, TokenError):
                # Cookie present but invalid/expired — don't fall through;
                # let the view return 401 so the client can refresh.
                return None

        # 2. Fall back to Authorization header (supports test clients &
        #    force_authenticate)
        return super().authenticate(request)
