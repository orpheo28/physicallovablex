"""Production MCP over Streamable HTTP. Owner: W22.

Same 7 tools as the stdio server (factory_mcp/server.py), same SQLite store as the portal. Two ways to run it:
- inside the API (api/mcp_http mounts it at /mcp — same process, so a factory registered over MCP shows up in GET /factories);
- standalone:  uv run python -m factory_mcp.http --port 8123      (endpoint http://127.0.0.1:8123/mcp)

Auth: `Authorization: Bearer <MCP_TOKEN>` or `X-App-Key: <MCP_TOKEN>`. MCP_TOKEN falls back to API_SHARED_KEY; both unset →
open (local dev). Read on every request, so it can be flipped without a restart. Stateless + JSON responses: no session to
lose on a redeploy, and plain HTTP clients (ChatGPT connectors, curl) work.
"""

from __future__ import annotations

import hmac
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Receive, Scope, Send

from factory_mcp.server import server

MCP_PATH = "/mcp"


def expected_token() -> str:
    return os.getenv("MCP_TOKEN") or os.getenv("API_SHARED_KEY") or ""


def token_ok(headers: list[tuple[bytes, bytes]]) -> bool:
    expected = expected_token()
    if not expected:
        return True
    h = {k.lower(): v.decode("latin-1") for k, v in headers}
    auth = h.get(b"authorization", "")
    provided = auth[7:].strip() if auth[:7].lower() == "bearer " else h.get(b"x-app-key", "")
    return hmac.compare_digest(provided.encode(), expected.encode())


class McpEndpoint:
    """ASGI app for the /mcp path: token gate → the SDK's Streamable HTTP app of the *current* server run.

    The SDK session manager can only be started once, so `lifespan()` builds a fresh one per app start (tests start the app
    many times); until it has run, requests get a 503."""

    def __init__(self) -> None:
        self._app: ASGIApp | None = None

    @asynccontextmanager
    async def lifespan(self, _app: object = None) -> AsyncIterator[None]:
        self._app = server.streamable_http_app(
            streamable_http_path=MCP_PATH,
            json_response=True,
            stateless_http=True,
            # token auth replaces the localhost-only DNS-rebinding allow-list (which would reject the public Host header)
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        try:
            async with server.session_manager.run():
                yield
        finally:
            self._app = None

    async def _reply(self, send: Send, status: int, detail: str, headers: list[tuple[bytes, bytes]] | None = None) -> None:
        body = json.dumps({"detail": detail}).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                                *(headers or [])]})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        if scope["method"] != "OPTIONS" and not token_ok(scope["headers"]):
            return await self._reply(send, 401, "Unauthorized: send 'Authorization: Bearer <MCP_TOKEN>' (or X-App-Key).",
                                     [(b"www-authenticate", b'Bearer realm="physicallovablex-production-mcp"')])
        if self._app is None:
            return await self._reply(send, 503, "MCP endpoint is not started.")
        scope = {**scope, "path": MCP_PATH, "raw_path": MCP_PATH.encode()}  # accept /mcp and /mcp/
        await self._app(scope, receive, send)


def main() -> None:
    import argparse

    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route

    ap = argparse.ArgumentParser(description="Production MCP over Streamable HTTP (standalone)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8123)
    args = ap.parse_args()
    endpoint = McpEndpoint()
    app = Starlette(routes=[Route(MCP_PATH, endpoint), Route(MCP_PATH + "/", endpoint)], lifespan=endpoint.lifespan)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
