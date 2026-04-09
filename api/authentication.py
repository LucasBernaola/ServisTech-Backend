import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        access_token = request.COOKIES.get('access_token')
        logger.debug("Access token present: %s", bool(access_token))

        if not access_token:
            logger.debug("No access token in cookies, checking Authorization header")
            header = self.get_header(request)
            if header is None:
                logger.debug("No Authorization header found")
                return None
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                logger.debug("No token in Authorization header")
                return None
            try:
                validated_token = self.get_validated_token(raw_token)
                user = self.get_user(validated_token)
                logger.debug(f"Authenticated user from header: {user.username}")
                return user, validated_token
            except Exception as e:
                logger.error(f"Header authentication failed: {str(e)}")
                raise AuthenticationFailed(f'Invalid token in header: {str(e)}')

        try:
            validated_token = self.get_validated_token(access_token)
            user = self.get_user(validated_token)
            logger.debug(f"Authenticated user from cookie: {user.username}")
            return user, validated_token
        except Exception as e:
            logger.error(f"Cookie authentication failed: {str(e)}")
            raise AuthenticationFailed(f'Invalid or expired token: {str(e)}')
