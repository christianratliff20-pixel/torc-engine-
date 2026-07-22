import redis
from fastapi import HTTPException, Request

from app.config import settings

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def rate_limit(key_prefix: str, max_attempts: int, window_seconds: int):
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{key_prefix}:{client_ip}"

        try:
            r = _get_redis()
            current = r.incr(key)
            if current == 1:
                r.expire(key, window_seconds)
            if current > max_attempts:
                ttl = r.ttl(key)
                raise HTTPException(
                    429,
                    f"Too many attempts. Try again in {ttl if ttl > 0 else window_seconds} seconds.",
                )
        except redis.RedisError:
            pass

    return dependency


login_rate_limit = rate_limit("login", max_attempts=10, window_seconds=300)
register_rate_limit = rate_limit("register", max_attempts=5, window_seconds=3600)
forgot_password_rate_limit = rate_limit("forgot_password", max_attempts=3, window_seconds=900)
tt
