"""GitHub webhook signature verification.

GitHub signs every webhook delivery with HMAC-SHA256 over the RAW request body, using the secret you
configure on the webhook, and sends the result in the `X-Hub-Signature-256` header as `sha256=<hex>`.
Without this check, anyone who finds the endpoint can POST fake events and make the service call
OpenAI (cost) and post comments on pull requests.
"""
import hashlib
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, Request


def compute_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: bytes, signature_header: Optional[str]) -> bool:
    """Constant-time comparison; returns False for a missing secret or header."""
    if not secret or not signature_header:
        return False
    return hmac.compare_digest(compute_signature(secret, body), signature_header)


async def require_github_signature(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(default=None),
) -> None:
    """FastAPI dependency. Fails closed: if no secret is configured, every request is rejected."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret is not configured")
    body = await request.body()  # raw bytes; Starlette caches them so the endpoint can still parse JSON
    if not verify_signature(secret, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
