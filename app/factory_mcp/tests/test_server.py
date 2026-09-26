"""MCP SDK client ↔ production server, in-memory (and one stdio smoke test)."""

import asyncio
import os
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from factory_mcp import network
from factory_mcp.server import server

EXPECTED = {"register_capacity", "search_capacity", "get_factory_profile", "request_quote", "submit_quote", "counter_offer", "accept_quote"}
MVP = Path(__file__).resolve().parents[2]


async def _session(target):
    async with Client(target) as c:
        tools = {t.name for t in (await c.list_tools()).tools}
        r = await c.call_tool("search_capacity", {"process": "pcba", "material": "FR-4", "quantity": 2000, "certifications_required": ["ISO 9001"]})
        return tools, r


def test_in_memory_client_lists_7_tools_and_searches():
    network.reset()
    tools, r = asyncio.run(_session(server))
    assert tools == EXPECTED
    assert not r.is_error
    matches = r.structured_content["result"]
    assert len(matches) >= 3 and matches[0]["rank"] == 1 and matches[0]["reasons"]


def test_in_memory_quote_loop_and_errors():
    network.reset()

    async def go():
        async with Client(server) as c:
            rfq = (await c.call_tool("request_quote", {"factory_id": "f_kestrel", "factory_pack_id": "fp_x", "quantities": [2000]})).structured_content["rfq_id"]
            qid = (await c.call_tool("submit_quote", {"rfq_id": rfq, "unit_price_per_tier": {"2000": 12.0}, "tooling_usd": 8000, "moq": 2000,
                                                      "lead_time_days": 45, "payment_terms": "30% deposit / 70% before shipment"})).structured_content["quote_id"]
            v2 = (await c.call_tool("counter_offer", {"quote_id": qid, "proposed_changes": {"unit_price_pct": -3}, "rationale": "anchor"})).structured_content
            order = (await c.call_tool("accept_quote", {"quote_id": v2["id"]})).structured_content
            bad = await c.call_tool("get_factory_profile", {"factory_id": "nope"})
            reg = (await c.call_tool("register_capacity", {"name": "New Shop", "region": "Foshan", "processes": ["cnc"], "materials": ["Aluminium 6061"],
                                                            "moq": 100, "certifications": [], "lead_time_days": 15, "monthly_capacity": 1000,
                                                            "current_load_pct": 20})).structured_content
            return v2, order, bad, reg

    v2, order, bad, reg = asyncio.run(go())
    assert v2["version"] == 2 and v2["tiers"][0]["unit_price_usd"] == 11.64
    assert order["quote_id"] == v2["id"] and order["label"] == "fictional"
    assert bad.is_error and "not found" in bad.content[0].text
    assert network.get_factory(reg["factory_id"]).name == "New Shop (fictional)"


def test_stdio_server_process():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "factory_mcp.server"], cwd=str(MVP),
        env={**os.environ, "FACTORY_MCP_DB": os.environ["FACTORY_MCP_DB"]},
    )
    tools, r = asyncio.run(_session(params))
    assert tools == EXPECTED and not r.is_error
