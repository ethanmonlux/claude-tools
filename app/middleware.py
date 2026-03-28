"""Request body size limit middleware.
Fail-closed: unknown routes get the smallest limit.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import settings

SKILL_MAX_BYTES = 64 * 1024  # 64 KB
ADMIN_MAX_BYTES = 256 * 1024  # 256 KB
DEFAULT_MAX_BYTES = SKILL_MAX_BYTES


def _limit_for_path(path: str) -> int:
    if path.startswith("/admin"):
        return ADMIN_MAX_BYTES
    if path.startswith("/skill"):
        return SKILL_MAX_BYTES
    return DEFAULT_MAX_BYTES


# ---------------------------------------------------------------------------
# Token bucket rate limiter (per API key, in-memory)
# ---------------------------------------------------------------------------

# {hashed_key: [tokens_remaining, last_refill_timestamp]}
_buckets: dict[str, list] = defaultdict(
    lambda: [settings.rate_limit_requests, time.monotonic()]
)


def _check_rate_limit(api_key: str) -> bool:
    """Return True if request is allowed, False if rate limit exceeded."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    bucket = _buckets[key_hash]
    now = time.monotonic()
    elapsed = now - bucket[1]

    # Refill tokens based on elapsed time
    refill = (
        elapsed / settings.rate_limit_window_seconds
    ) * settings.rate_limit_requests
    bucket[0] = min(settings.rate_limit_requests, bucket[0] + refill)
    bucket[1] = now

    if bucket[0] < 1:
        return False

    bucket[0] -= 1
    return True


async def _send_429(send: Send) -> None:
    body = json.dumps(
        {
            "error": "rate_limit_exceeded",
            "detail": "Rate limit exceeded — try again shortly",
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 429,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        max_bytes = _limit_for_path(path)

        headers = dict(scope.get("headers", []))

        # Rate limit skill endpoints by API key
        if path.startswith("/skill"):
            api_key = headers.get(b"x-api-key", b"").decode()
            if api_key and not _check_rate_limit(api_key):
                await _send_429(send)
                return

        content_length_raw = headers.get(b"content-length")
        if content_length_raw is not None:
            try:
                if int(content_length_raw) > max_bytes:
                    await _send_413(send, max_bytes)
                    return
            except (ValueError, TypeError):
                pass

        bytes_received = 0

        async def limited_receive() -> dict:
            nonlocal bytes_received
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > max_bytes:
                    raise _BodyTooLarge(max_bytes)
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLarge:
            await _send_413(send, max_bytes)


class _BodyTooLarge(Exception):
    def __init__(self, limit: int) -> None:
        self.limit = limit


async def _send_413(send: Send, limit: int) -> None:
    body = json.dumps(
        {
            "error": "payload_too_large",
            "detail": f"Request body exceeds {limit} byte limit",
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
