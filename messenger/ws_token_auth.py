import logging
from django.db import close_old_connections
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.utils import jwt_decode_handler
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class JsonTokenAuthMiddleware(JSONWebTokenAuthentication):
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):

        close_old_connections()

        try:
            payload = jwt_decode_handler(scope.get("subprotocols")[0])
            User = get_user_model()
            scope["user"] = User.objects.get(email=payload.get("email"))
        except Exception as error:
            logger.error(f"WS client connecting with BAD TOKEN: {error}")

        return self.inner(scope)
