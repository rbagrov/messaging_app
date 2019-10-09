from redis import Redis
from urllib.parse import urlparse
from django.conf import settings


class Presence(object):
    @classmethod
    def _connect(cls):
        redis_settings = urlparse(settings.REDIS_URL)
        return Redis(
            host=redis_settings.hostname,
            port=redis_settings.port,
            password=redis_settings.password,
            decode_responses=True,
        )

    @staticmethod
    def decrement_active_connections(user):
        redis = Presence._connect()
        try:
            value = int(redis.get(user))
            assert value > 0
        except Exception:
            redis.set(user, 0, ex=settings.WS_KEY_EXPIRE)
            return int(redis.get(user))

        try:
            return redis.decr(user)
        except Exception:
            redis.delete(user)
            redis.set(user, 0, ex=settings.WS_KEY_EXPIRE)
            return int(redis.get(user))

    @staticmethod
    def increment_active_connections(user):
        redis = Presence._connect()
        try:
            redis.incr(user)
            redis.expire(user, settings.WS_KEY_EXPIRE)
            return int(redis.get(user))
        except Exception:
            redis.delete(user)
            redis.set(user, 0, ex=settings.WS_KEY_EXPIRE)
            return int(redis.get(user))

    @staticmethod
    def is_online(user):
        redis = Presence._connect()
        try:
            return int(redis.get(user)) > 0
        except Exception:
            return False
