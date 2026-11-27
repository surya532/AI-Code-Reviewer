import fakeredis
import pytest
import redis

from app import rate_limit
from app.rate_limit import RateLimitExceeded, RateLimiterUnavailable, check_rate_limit


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(rate_limit, "r", client)
    monkeypatch.setattr(rate_limit, "RATE_LIMIT", 3)
    return client


def test_allows_requests_up_to_the_limit():
    for _ in range(3):
        check_rate_limit("octo/demo")


def test_blocks_the_request_over_the_limit():
    for _ in range(3):
        check_rate_limit("octo/demo")
    with pytest.raises(RateLimitExceeded):
        check_rate_limit("octo/demo")


def test_limits_are_per_repo():
    for _ in range(3):
        check_rate_limit("octo/one")
    check_rate_limit("octo/two")  # a different repo is unaffected


def test_window_starts_at_first_request_and_is_not_extended(fake_redis):
    check_rate_limit("octo/demo")
    assert 0 < fake_redis.ttl("rate:octo/demo") <= rate_limit.WINDOW_SECONDS
    fake_redis.expire("rate:octo/demo", 10)
    check_rate_limit("octo/demo")
    assert fake_redis.ttl("rate:octo/demo") <= 10  # later requests must not push the expiry out


def test_allows_again_after_the_window_expires(fake_redis):
    for _ in range(3):
        check_rate_limit("octo/demo")
    fake_redis.delete("rate:octo/demo")  # what Redis does when the TTL runs out
    check_rate_limit("octo/demo")


def test_redis_failure_raises_unavailable(monkeypatch):
    class Broken:
        def pipeline(self, transaction=True):
            raise redis.ConnectionError("connection refused")

    monkeypatch.setattr(rate_limit, "r", Broken())
    with pytest.raises(RateLimiterUnavailable):
        check_rate_limit("octo/demo")
