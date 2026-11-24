import json

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.security import compute_signature, require_github_signature, verify_signature

SECRET = "test-secret"

app = FastAPI()


@app.post("/webhook", dependencies=[Depends(require_github_signature)])
async def webhook(payload: dict):
    return {"received": payload.get("action")}


client = TestClient(app)


def post(body: bytes, signature=None):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Hub-Signature-256"] = signature
    return client.post("/webhook", content=body, headers=headers)


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)


def test_valid_signature_is_accepted():
    body = json.dumps({"action": "opened"}).encode()
    r = post(body, compute_signature(SECRET, body))
    assert r.status_code == 200
    assert r.json() == {"received": "opened"}


def test_tampered_body_is_rejected():
    body = json.dumps({"action": "opened"}).encode()
    sig = compute_signature(SECRET, body)
    r = post(json.dumps({"action": "closed"}).encode(), sig)
    assert r.status_code == 401


def test_missing_signature_is_rejected():
    assert post(b'{"action":"opened"}').status_code == 401


def test_wrong_secret_is_rejected():
    body = b'{"action":"opened"}'
    assert post(body, compute_signature("other-secret", body)).status_code == 401


def test_malformed_signature_is_rejected():
    assert post(b'{"action":"opened"}', "sha256=").status_code == 401
    assert post(b'{"action":"opened"}', "not-a-signature").status_code == 401


def test_fails_closed_when_secret_not_configured(monkeypatch):
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    body = b'{"action":"opened"}'
    assert post(body, compute_signature(SECRET, body)).status_code == 500


def test_verify_signature_unit():
    body = b"hello"
    assert verify_signature(SECRET, body, compute_signature(SECRET, body))
    assert not verify_signature(SECRET, body, None)
    assert not verify_signature("", body, compute_signature(SECRET, body))


def test_matches_githubs_documented_example():
    # Test vector from GitHub's "Validating webhook deliveries" documentation.
    secret = "It's a Secret to Everybody"
    body = b"Hello, World!"
    expected = "sha256=757107ea0eb2509fc211221cce984b8a37570b6d7586c22c46f4379c8b043e17"
    assert compute_signature(secret, body) == expected
