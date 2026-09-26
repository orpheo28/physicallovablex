"""Public-link guards: shared-password gate, per-IP live-run limit, read-only demo mode. Owner: W9.

All settings are read from the environment on every request, so they can be flipped without a restart in tests.

- API_SHARED_KEY set → every route except GET /health (and CORS preflight) needs `X-App-Key: <API_SHARED_KEY>`, else 401.
                      Unset → open (local dev). The Next.js proxy adds the header server-side from its own API_SHARED_KEY; the browser never sees it.
                      (APP_PASSWORD is a different thing: the web app's password screen.)
- RATE_LIMIT_PER_DAY (default 20) → per client IP, rolling 24 h, on the routes that can spend LLM credits
                      (POST /projects, POST .../stages/{n}/run, POST .../autorun). Only counted when an OpenRouter
                      key is configured (without one every stage serves free fixtures). 0 disables. In-memory: resets on restart.
- DEMO_READONLY=1   → no live runs at all: the routes above, PUT stage edits and POST /factories return 403.
                      Cached demo projects, fixtures, factory portal reads and the PDF export keep working.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import threading
import time
from collections import defaultdict, deque

from starlette.types import ASGIApp, Receive, Scope, Send

LIVE_RUN = re.compile(r"^/projects(?:/[^/]+/(?:stages/\d+/run|autorun))?/?$")
READONLY_BLOCKED = re.compile(r"^/projects(?:/[^/]+/(?:stages/\d+(?:/run)?|autorun))?/?$|^/factories/?$")
WINDOW_S = 24 * 3600

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def key_ok(provided: str | None) -> bool:
    expected = os.getenv("API_SHARED_KEY", "")
    if not expected:
        return True
    return hmac.compare_digest((provided or "").encode(), expected.encode())


def client_ip(scope: Scope) -> str:
    """First X-Forwarded-For hop (Railway / the Vercel proxy set it), else the socket peer."""
    for k, v in scope["headers"]:
        if k == b"x-forwarded-for" and v.strip():
            return v.decode("latin-1").split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


def rate_limit_left(ip: str, limit: int, now: float | None = None, consume: bool = True) -> int | None:
    """Consume one run for `ip`; return None when allowed, else the seconds until a slot frees up."""
    now = time.time() if now is None else now
    with _lock:
        q = _hits[ip]
        while q and q[0] <= now - WINDOW_S:
            q.popleft()
        if len(q) >= limit:
            return int(q[0] + WINDOW_S - now) + 1
        if consume:
            q.append(now)
        return None


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


def _live_llm() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY"))


def _prune() -> None:
    try:
        from api.housekeeping import prune_files

        prune_files()
    except Exception:  # noqa: BLE001 — housekeeping must never break a request
        pass


class Guards:
    """Pure ASGI middleware (no body buffering)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def _reply(self, send: Send, status: int, detail: str, headers: list[tuple[bytes, bytes]] | None = None) -> None:
        body = json.dumps({"detail": detail}).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                                *(headers or [])]})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        method, path = scope["method"], scope["path"]
        if method == "OPTIONS" or (method in ("GET", "HEAD") and path == "/health"):
            return await self.app(scope, receive, send)

        if os.getenv("API_SHARED_KEY"):
            provided = next((v.decode("latin-1") for k, v in scope["headers"] if k == b"x-app-key"), None)
            if not key_ok(provided):
                return await self._reply(send, 401, "Unauthorized: missing or wrong X-App-Key.")

        if method in ("POST", "PUT") and _truthy("DEMO_READONLY") and READONLY_BLOCKED.match(path):
            return await self._reply(send, 403, "Read-only demo: live AI runs are disabled here. "
                                                "Open one of the cached example projects, or run the app locally.")

        if method == "POST" and LIVE_RUN.match(path):
            _prune()
        if method == "POST" and LIVE_RUN.match(path) and _live_llm():
            limit = int(os.getenv("RATE_LIMIT_PER_DAY", "20") or 0)
            if limit > 0:
                wait = rate_limit_left(client_ip(scope), limit)
                if wait is not None:
                    return await self._reply(
                        send, 429, f"Daily limit reached: {limit} live runs per visitor per 24 h. "
                                   f"Try again in about {max(1, wait // 3600)} h, or explore the cached examples.",
                        [(b"retry-after", str(wait).encode())])
        await self.app(scope, receive, send)
