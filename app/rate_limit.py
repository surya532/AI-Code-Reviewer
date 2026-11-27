import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))  # max requests per repo per window
WINDOW_SECONDS = 60

# Short timeouts so a Redis outage fails fast instead of hanging the webhook.
r = redis.Redis.from_url(
    REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
)


class RateLimitExceeded(Exception):
    """The repo has used up its requests for the current window."""


class RateLimiterUnavailable(Exception):
    """Redis could not be reached, so the limit could not be checked."""


def check_rate_limit(repo: str) -> None:
    """Fixed-window limiter. Requires Redis 7.0+ (EXPIRE ... NX).

    INCR and EXPIRE NX run in one transaction, so concurrent requests cannot both slip under the
    limit, and the window starts at the first request and is not extended by later ones.
    """
    key = f"rate:{repo}"
    try:
        pipe = r.pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS, nx=True)
        count, _ = pipe.execute()
    except redis.RedisError as exc:
        raise RateLimiterUnavailable("Rate limiter backend is unavailable") from exc
    if count > RATE_LIMIT:
        raise RateLimitExceeded(f"Rate limit exceeded for repo {repo}")
