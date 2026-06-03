# signing/throttles.py
from rest_framework.throttling import AnonRateThrottle


class SigningTokenRateThrottle(AnonRateThrottle):
    """
    Per signing-token + IP throttle for all public signing endpoints.
    Rate configured via DEFAULT_THROTTLE_RATES['signing_token'] in settings.
    """
    scope = 'signing_token'

    def get_cache_key(self, request, view):
        token = view.kwargs.get('token', '')
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': f"{ident}_{token}",
        }