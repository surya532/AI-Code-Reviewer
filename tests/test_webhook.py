import json

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.db import Base, get_db
from app.models import Review
from app.rate_limit import RateLimitExceeded, RateLimiterUnavailable
from app.security import compute_signature

# The tests use their own in-memory SQLite database, so they never touch Postgres.
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


main.app.dependency_overrides[get_db] = override_get_db

SECRET = "test-secret"
client = TestClient(main.app)


def pr_payload(sha="a" * 40, action="opened"):
    return {
        "action": action,
        "pull_request": {"number": 7, "head": {"ref": "feature", "sha": sha}},
        "repository": {"full_name": "octo/demo"},
    }


def post(payload, signed=True):
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if signed:
        headers["X-Hub-Signature-256"] = compute_signature(SECRET, body)
    return client.post("/webhook/github", content=body, headers=headers)


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    state = {"llm_calls": 0, "comments": [], "fail_post": False}

    async def fake_files(repo, pr):
        return [{"filename": "app.py", "status": "modified", "patch": "+print('hi')"}]

    async def fake_llm(prompt):
        state["llm_calls"] += 1
        return "looks fine"

    async def fake_post(repo, pr, body):
        if state["fail_post"]:
            raise RuntimeError("github down")
        state["comments"].append(body)

    # No Redis in tests: the rate limiter is replaced by a no-op (a test below makes it raise).
    monkeypatch.setattr(main, "check_rate_limit", lambda repo: None)
    monkeypatch.setattr(main, "get_pr_files", fake_files)
    monkeypatch.setattr(main, "review_code_with_llm", fake_llm)
    monkeypatch.setattr(main, "post_pr_comment", fake_post)
    return state


def test_unsigned_request_is_rejected():
    assert post(pr_payload(), signed=False).status_code == 401


def test_ping_is_ignored_without_side_effects(setup):
    assert post({"action": "ping"}).json() == {"status": "ignored"}
    assert setup["llm_calls"] == 0


def test_review_is_posted_once(setup):
    r = post(pr_payload())
    assert r.json() == {"status": "reviewed", "files_reviewed": 1}
    assert len(setup["comments"]) == 1
    with SessionLocal() as db:
        row = db.query(Review).one()
        assert (row.status, row.head_sha) == ("completed", "a" * 40)


def test_redelivery_for_same_commit_is_a_noop(setup):
    post(pr_payload())
    again = post(pr_payload())
    assert again.json()["status"] == "duplicate"
    assert setup["llm_calls"] == 1
    assert len(setup["comments"]) == 1


def test_new_commit_gets_a_new_review(setup):
    post(pr_payload(sha="a" * 40, action="opened"))
    r = post(pr_payload(sha="b" * 40, action="synchronize"))
    assert r.json()["status"] == "reviewed"
    assert len(setup["comments"]) == 2


def test_failed_comment_can_be_retried_without_a_second_row(setup):
    setup["fail_post"] = True
    assert post(pr_payload()).json()["status"] == "post_failed"
    setup["fail_post"] = False
    assert post(pr_payload()).json()["status"] == "reviewed"
    assert len(setup["comments"]) == 1
    with SessionLocal() as db:
        assert db.query(Review).count() == 1


def test_rate_limited_request_does_no_work(setup, monkeypatch):
    def limited(repo):
        raise RateLimitExceeded("too many requests")

    monkeypatch.setattr(main, "check_rate_limit", limited)
    r = post(pr_payload())
    assert r.status_code == 429
    assert r.json()["status"] == "rate_limited"
    assert setup["llm_calls"] == 0
    assert setup["comments"] == []


def test_redis_outage_fails_closed_without_spending_money(setup, monkeypatch):
    def down(repo):
        raise RateLimiterUnavailable("redis down")

    monkeypatch.setattr(main, "check_rate_limit", down)
    r = post(pr_payload())
    assert r.status_code == 503
    assert r.json() == {"status": "rate_limiter_unavailable"}
    assert setup["llm_calls"] == 0
