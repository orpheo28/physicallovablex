"""Production MCP server — the 7 PRD §10 tools over the fictional network. Owner: W5.

Run (stdio):  uv run python -m factory_mcp.server
Official MCP Python SDK v2 (`MCPServer`, formerly `FastMCP`). All data is Fictional — demo data.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from contracts.artifacts import ProcessType, SearchCapacityQuery
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from factory_mcp import network

server = MCPServer(
    name="physicallovablex-production",
    instructions=(
        "Fictional production network (demo data). Factories register capacity; any agent can search capacity, "
        "read factory profiles, send RFQs referencing a Factory Pack, and run a quote → counter → accept loop. "
        "Every factory, quote and number returned is fictional."
    ),
)


def _run(fn: Callable[[], Any]) -> Any:
    """Surface bad ids / invalid inputs to the calling agent as a readable tool error."""
    try:
        return fn()
    except (network.NotFoundError, ValueError) as e:
        raise ToolError(str(e)) from e


def _dump(obj: Any) -> Any:
    if isinstance(obj, list):
        return [_dump(o) for o in obj]
    return obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj


@server.tool()
def register_capacity(
    name: str,
    region: str,
    processes: list[ProcessType],
    materials: list[str],
    moq: int,
    certifications: list[str],
    lead_time_days: int,
    monthly_capacity: int,
    current_load_pct: float,
    archetype: str = "balanced",
) -> dict[str, str]:
    """Factory onboarding: publish a capacity profile (processes, materials, MOQ, certifications, lead time,
    monthly capacity, current load). Returns the new factory_id. The name is suffixed '(fictional)'."""
    fid = _run(lambda: network.register_capacity(
        name, region, [getattr(p, "value", p) for p in processes], materials, moq, certifications,
        lead_time_days, monthly_capacity, current_load_pct, archetype,
    ))
    return {"factory_id": fid}


@server.tool()
def search_capacity(
    process: ProcessType,
    material: str,
    quantity: int,
    certifications_required: list[str] | None = None,
    deadline: date | None = None,
) -> list[dict[str, Any]]:
    """Rank factories for one process/material/quantity. Deterministic weighted score (process_fit 0.35,
    moq 0.15, certifications 0.15, load 0.15, lead_time 0.20) with a per-criterion breakdown and reasons."""
    q = SearchCapacityQuery(
        process=process, material=material, quantity=quantity,
        certifications_required=certifications_required or [], deadline=deadline,
    )
    return _dump(_run(lambda: network.search_capacity(q)))


@server.tool()
def get_factory_profile(factory_id: str) -> dict[str, Any]:
    """Capacity profile, audit notes and past performance of one factory (fictional)."""
    return _dump(_run(lambda: network.get_factory_profile(factory_id)))


@server.tool()
def request_quote(factory_id: str, factory_pack_id: str, quantities: list[int], product_name: str | None = None) -> dict[str, str]:
    """Send an RFQ referencing a Factory Pack for the given quantity tiers. Returns rfq_id."""
    return {"rfq_id": _run(lambda: network.request_quote(factory_id, factory_pack_id, quantities, product_name=product_name))}


@server.tool()
def submit_quote(
    rfq_id: str,
    unit_price_per_tier: dict[str, float],
    tooling_usd: float,
    moq: int,
    lead_time_days: int,
    payment_terms: str,
    exceptions: list[str] | None = None,
) -> dict[str, str]:
    """Factory agent: quote an RFQ. unit_price_per_tier maps quantity → USD unit price, e.g. {"2000": 13.5}.
    Returns quote_id (each submission is a new version)."""
    prices = {int(k): v for k, v in unit_price_per_tier.items()}
    return {"quote_id": _run(lambda: network.submit_quote(rfq_id, prices, tooling_usd, moq, lead_time_days, payment_terms, exceptions))}


@server.tool()
def counter_offer(quote_id: str, proposed_changes: dict[str, Any], rationale: str) -> dict[str, Any]:
    """Platform agent: counter a quote. proposed_changes keys: unit_price_pct (e.g. -5), tiers, tooling_usd,
    moq, lead_time_days, payment_terms. Returns the new quote version (status 'countered')."""
    return _dump(_run(lambda: network.counter_offer(quote_id, proposed_changes, rationale)))


@server.tool()
def accept_quote(quote_id: str) -> dict[str, Any]:
    """After the founder approves: accept a quote version. Returns an order draft (fictional)."""
    return _dump(_run(lambda: network.accept_quote(quote_id)))


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
