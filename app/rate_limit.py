import os
import time
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

RATE_LIMIT = 5  # max requests per minute per repo

def check_rate_limit(repo: str):
    key = f"rate:{repo}"
    current = r.get(key)
    if current and int(current) >= RATE_LIMIT:
        raise Exception(f"Rate limit exceeded for repo {repo}")
    pipe = r.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, 60)  # 60 seconds window
    pipe.execute()
