"""W22: production MCP over Streamable HTTP at /mcp — real HTTP (uvicorn on a free port) + the SDK client."""

import asyncio
import socket
import threading
import time
import uuid

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from api.main import app
from factory_mcp.demo._client import connect, result_data

TOOLS = {"register_capacity", "search_capacity", "get_factory_profile", "request_quote", "submit_quote", "counter_offer",
         "accept_quote"}
JSON_RPC = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
ACCEPT = {"Accept": "application/json, text/event-stream"}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("MCP_TOKEN", "API_SHARED_KEY", "DEMO_READONLY"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture(scope="module")
def base_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    assert server.started
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    th.join(timeout=10)


def run(coro):
    return asyncio.run(coro)


def test_lists_exactly_the_7_tools(base_url):
    async def go():
        async with connect(f"{base_url}/mcp", "") as c:
            return (await c.list_tools()).tools

    tools = run(go())
    assert {t.name for t in tools} == TOOLS and len(tools) == 7
    assert all("FICTIONAL" in (t.description or "").upper() for t in tools if t.name != "counter_offer")  # written for external agents


def test_search_returns_ranked_results(base_url):
    async def go():
        async with connect(f"{base_url}/mcp", "") as c:
            res = await c.call_tool("search_capacity", {"process": "injection_molding", "material": "PC/ABS", "quantity": 2000,
                                                        "certifications_required": ["ISO 9001"], "deadline": "2026-12-15"})
            return result_data(res)

    matches = run(go())
    assert len(matches) >= 3
    assert [m["rank"] for m in matches] == list(range(1, len(matches) + 1))
    scores = [m["score"]["value"] for m in matches]
    assert scores == sorted(scores, reverse=True)
    assert all(m["reasons"] and len(m["score_breakdown"]) == 5 for m in matches)


def test_register_capacity_appears_in_portal_and_ranks(base_url):
    name = f"Tidewater Test {uuid.uuid4().hex[:6]}"

    async def go():
        async with connect(f"{base_url}/mcp", "") as c:
            fid = result_data(await c.call_tool("register_capacity", dict(
                name=name, region="Penang, MY", processes=["injection_molding", "pcba"], materials=["LSR silicone"], moq=100,
                certifications=["ISO 9001"], lead_time_days=20, monthly_capacity=90000, current_load_pct=10)))["factory_id"]
            found = result_data(await c.call_tool("search_capacity", {"process": "injection_molding", "material": "LSR silicone",
                                                                      "quantity": 2000}))
            rfq = result_data(await c.call_tool("request_quote", {"factory_id": fid, "factory_pack_id": "fp_test",
                                                                  "quantities": [500, 2000]}))
            return fid, found, rfq["rfq_id"]

    fid, found, rfq_id = run(go())
    portal = httpx.get(f"{base_url}/factories").json()  # same process, same store as the portal
    assert any(f["id"] == fid and f["name"] == f"{name} (fictional)" for f in portal)
    assert found[0]["factory_id"] == fid  # nearly empty + exact material → tops the ranking
    assert any(r["rfq"]["id"] == rfq_id for r in httpx.get(f"{base_url}/factories/{fid}/rfqs").json())


def test_auth_rejects_without_token_when_mcp_token_set(base_url, monkeypatch):
    monkeypatch.setenv("MCP_TOKEN", "t0ken")
    r = httpx.post(f"{base_url}/mcp", json=JSON_RPC, headers=ACCEPT)
    assert r.status_code == 401 and "bearer" in r.headers["www-authenticate"].lower()
    assert httpx.post(f"{base_url}/mcp", json=JSON_RPC, headers={**ACCEPT, "Authorization": "Bearer nope"}).status_code == 401
    assert httpx.post(f"{base_url}/mcp", json=JSON_RPC, headers={**ACCEPT, "X-App-Key": "nope"}).status_code == 401
    for h in ({"Authorization": "Bearer t0ken"}, {"X-App-Key": "t0ken"}):
        assert httpx.post(f"{base_url}/mcp", json=JSON_RPC, headers={**ACCEPT, **h}).status_code == 200

    async def go(token):
        async with connect(f"{base_url}/mcp", token) as c:
            return len((await c.list_tools()).tools)

    assert run(go("t0ken")) == 7


def test_token_falls_back_to_api_shared_key_and_bypasses_portal_gate(base_url, monkeypatch):
    monkeypatch.setenv("API_SHARED_KEY", "shared")
    assert httpx.get(f"{base_url}/factories").status_code == 401  # portal still gated by X-App-Key
    assert httpx.post(f"{base_url}/mcp", json=JSON_RPC, headers=ACCEPT).status_code == 401
    assert httpx.post(f"{base_url}/mcp", json=JSON_RPC, headers={**ACCEPT, "Authorization": "Bearer shared"}).status_code == 200
    monkeypatch.setenv("MCP_TOKEN", "own")  # MCP_TOKEN wins; API_SHARED_KEY no longer opens /mcp
    assert httpx.post(f"{base_url}/mcp", json=JSON_RPC, headers={**ACCEPT, "Authorization": "Bearer shared"}).status_code == 401
    assert httpx.post(f"{base_url}/mcp", json=JSON_RPC, headers={**ACCEPT, "Authorization": "Bearer own"}).status_code == 200


def test_tool_errors_are_readable(base_url):
    async def go():
        async with connect(f"{base_url}/mcp", "") as c:
            return await c.call_tool("get_factory_profile", {"factory_id": "nope"})

    res = run(go())
    assert res.is_error and "nope" in res.content[0].text


def test_app_restarts_cleanly():
    """The SDK session manager starts once per app start — TestClient contexts must be repeatable."""
    for _ in range(2):
        with TestClient(app) as c:
            assert c.post("/mcp", json=JSON_RPC, headers=ACCEPT).status_code == 200
            assert c.post("/mcp/", json=JSON_RPC, headers=ACCEPT).status_code == 200
