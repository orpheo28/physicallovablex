"""Production MCP at /mcp (Streamable HTTP), same process and store as the factory portal. Owner: W22.

Auto-discovered (api/discovery.py): register() adds the /mcp route and hooks the SDK session manager into the app lifespan.
Auth is the endpoint's own (MCP_TOKEN, falling back to API_SHARED_KEY — see factory_mcp/http.py), so the global X-App-Key
gate (api/auth.py Guards, MCP_PATHS — native exemption since W21b) lets /mcp through: MCP clients (ChatGPT connectors, Claude) send `Authorization: Bearer`.
"""

from __future__ import annotations

from fastapi import APIRouter

from factory_mcp.http import MCP_PATH, McpEndpoint

endpoint = McpEndpoint()
_PATHS = (MCP_PATH, MCP_PATH + "/")


def register(router: APIRouter) -> None:
    for path in _PATHS:
        router.add_route(path, endpoint)
    router.lifespan_context = endpoint.lifespan
