from rest_framework_simplejwt.tokens import AccessToken
from datetime import timedelta, datetime
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CookieRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        access_token_cookie = request.COOKIES.get('access_token')

        if (
            hasattr(request, 'user')
            and request.user.is_authenticated
            and access_token_cookie
            and request.path != '/api/logout/'
        ):
            try:
                token = AccessToken(access_token_cookie)
                exp_timestamp = token['exp']
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                remaining_time = exp_datetime - datetime.utcnow()

                if remaining_time < timedelta(minutes=2):  # Renovamos si falta poco
                    new_token = AccessToken.for_user(request.user)
                    new_token.set_exp(lifetime=timedelta(minutes=10))  # Le damos 10 minutos más
                    response.set_cookie(
                        'access_token',
                        str(new_token),
                        max_age=10 * 60,
                        httponly=True,
                        secure=settings.SESSION_COOKIE_SECURE,
                        samesite='None',
                        path='/',
                    )
                    logger.debug(f"Token renovado automáticamente para {request.user.username}")
            except Exception as e:
                logger.error(f"Error al renovar token: {str(e)}")

        return response
