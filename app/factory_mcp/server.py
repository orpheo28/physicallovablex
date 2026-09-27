"""Production MCP server — the 7 PRD §10 tools over the fictional network. Owner: W5.

Run (stdio):  uv run python -m factory_mcp.server
Official MCP Python SDK v2 (`MCPServer`, formerly `FastMCP`). All data is Fictional — demo data.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Callable

from contracts.artifacts import ProcessType, SearchCapacityQuery
from mcp.server.mcpserver import MCPServer
from pydantic import Field
from mcp.server.mcpserver.exceptions import ToolError

from factory_mcp import network

server = MCPServer(
    name="physicallovablex-production",
    instructions=(
        "Production network for hardware: factories publish their capacity, buyers' agents search it and request quotes. "
        "Buyer flow: search_capacity (one call per process) -> get_factory_profile -> request_quote. "
        "Factory flow: register_capacity -> submit_quote. Every factory, quote and number here is FICTIONAL demo data."
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
    name: Annotated[str, Field(description="Factory name, e.g. 'Tidewater Wearables'. '(fictional)' is appended if missing.")],
    region: Annotated[str, Field(description="Where the factory is, e.g. 'Guangdong, CN' or 'Porto, PT'.")],
    processes: Annotated[list[ProcessType], Field(description="Processes the factory runs. One or more of: injection_molding "
                                                              "(incl. LSR/silicone overmolding), cnc, sheet_metal, die_casting, "
                                                              "extrusion, pcba, assembly, other.")],
    materials: Annotated[list[str], Field(description="Materials it can process, e.g. ['LSR silicone 50 Shore A', 'PC/ABS', 'FR-4'].")],
    moq: Annotated[int, Field(description="Minimum order quantity, in units.", ge=1)],
    certifications: Annotated[list[str], Field(description="Certifications held, e.g. ['ISO 9001', 'ISO 13485', 'BSCI'].")],
    lead_time_days: Annotated[int, Field(description="Typical order-to-ship lead time, in calendar days.", ge=1)],
    monthly_capacity: Annotated[int, Field(description="Units per month the factory can produce at full load.", ge=1)],
    current_load_pct: Annotated[float, Field(description="How full the factory is right now, 0-100 (%). Lower = more free capacity.",
                                             ge=0, le=100)],
    archetype: Annotated[str, Field(description="Negotiating style of the simulated factory agent: 'balanced' (default), "
                                                "'cheap/slow' or 'fast/expensive'.")] = "balanced",
) -> dict[str, str]:
    """FACTORY SIDE — publish your capacity to the production network. Factory capacity data does not exist publicly;
    this call creates it. The factory becomes immediately searchable via search_capacity and visible in the web portal.
    Returns {"factory_id"}. All data in this network is FICTIONAL demo data: registered names are suffixed '(fictional)'
    and nothing here is a real offer, quote or commitment."""
    fid = _run(lambda: network.register_capacity(
        name, region, [getattr(p, "value", p) for p in processes], materials, moq, certifications,
        lead_time_days, monthly_capacity, current_load_pct, archetype,
    ))
    return {"factory_id": fid}


@server.tool()
def search_capacity(
    process: Annotated[ProcessType, Field(description="The ONE manufacturing process to search. One of: injection_molding "
                                                      "(incl. LSR/silicone overmolding), cnc, sheet_metal, die_casting, "
                                                      "extrusion, pcba, assembly, other. For a product needing several "
                                                      "processes, call once per process.")],
    material: Annotated[str, Field(description="Material to run, free text, e.g. 'PC/ABS', 'LSR silicone', 'Aluminium 6061', "
                                               "'FR-4'. Use 'any' to ignore material.")],
    quantity: Annotated[int, Field(description="Order size in units (pieces).", ge=1)],
    certifications_required: Annotated[list[str] | None, Field(description="Certifications the factory must hold, "
                                                                           "e.g. ['ISO 9001']. Omit for none.")] = None,
    deadline: Annotated[date | None, Field(description="Latest delivery date, ISO format YYYY-MM-DD. Factories whose lead time "
                                                       "cannot make it are penalised. Omit for no deadline.")] = None,
) -> list[dict[str, Any]]:
    """BUYER SIDE — find and rank factories for one process/material/quantity. Returns up to 8 matches, best first; each has
    factory_id, factory_name, score (0-100), a per-criterion score_breakdown and plain-language reasons. Deterministic
    weighted score: process_fit 0.35, lead_time 0.20, moq 0.15, certifications 0.15, load 0.15. Factories that do not run the
    process are excluded. Next step: get_factory_profile, then request_quote. All factories are FICTIONAL demo data."""
    q = SearchCapacityQuery(
        process=process, material=material, quantity=quantity,
        certifications_required=certifications_required or [], deadline=deadline,
    )
    return _dump(_run(lambda: network.search_capacity(q)))


@server.tool()
def get_factory_profile(
    factory_id: Annotated[str, Field(description="A factory_id returned by search_capacity or register_capacity, e.g. 'f_cobaltriver'.")],
) -> dict[str, Any]:
    """BUYER SIDE — full profile of one factory: region, processes, materials, MOQ, certifications, lead time, monthly
    capacity, current load %, audit notes and past performance (on-time / defect rates; 'no_data' for self-registered
    factories). FICTIONAL demo data."""
    return _dump(_run(lambda: network.get_factory_profile(factory_id)))


@server.tool()
def request_quote(
    factory_id: Annotated[str, Field(description="Factory to ask, from search_capacity.")],
    factory_pack_id: Annotated[str, Field(description="Reference of the buyer's Factory Pack (the manufacturing dossier: BOM, "
                                                     "drawings, specs). Any identifier works in the demo, e.g. 'fp_my_product'.")],
    quantities: Annotated[list[int], Field(description="Quantity tiers to price, in units, e.g. [500, 2000, 10000].")],
    product_name: Annotated[str | None, Field(description="Human-readable product name shown to the factory, e.g. "
                                                          "'Silicone fitness band with PCBA'.")] = None,
) -> dict[str, str]:
    """BUYER SIDE — send a request for quotation (RFQ) to one factory for the given quantity tiers. Returns {"rfq_id"}. The
    RFQ appears in that factory's portal; the factory answers with submit_quote. FICTIONAL: no real order is placed."""
    return {"rfq_id": _run(lambda: network.request_quote(factory_id, factory_pack_id, quantities, product_name=product_name))}


@server.tool()
def submit_quote(
    rfq_id: Annotated[str, Field(description="RFQ to answer, from request_quote.")],
    unit_price_per_tier: Annotated[dict[str, float], Field(description="Quantity → unit price in USD per piece, "
                                                                      "e.g. {\"2000\": 13.5, \"10000\": 11.2}.")],
    tooling_usd: Annotated[float, Field(description="One-off tooling / mould cost, USD.", ge=0)],
    moq: Annotated[int, Field(description="Minimum order quantity for this quote, units.", ge=1)],
    lead_time_days: Annotated[int, Field(description="Lead time from PO to shipment, calendar days.", ge=1)],
    payment_terms: Annotated[str, Field(description="e.g. '30% deposit, 70% before shipment'.")],
    exceptions: Annotated[list[str] | None, Field(description="Deviations from the Factory Pack the factory cannot meet.")] = None,
) -> dict[str, str]:
    """FACTORY SIDE — quote an RFQ. Every submission is a new quote version. Returns {"quote_id"}. FICTIONAL demo data."""
    prices = {int(k): v for k, v in unit_price_per_tier.items()}
    return {"quote_id": _run(lambda: network.submit_quote(rfq_id, prices, tooling_usd, moq, lead_time_days, payment_terms, exceptions))}


@server.tool()
def counter_offer(
    quote_id: Annotated[str, Field(description="Quote version to counter, from submit_quote.")],
    proposed_changes: Annotated[dict[str, Any], Field(description="Any of: unit_price_pct (number, e.g. -5 = 5% cheaper), tiers "
                                                                  "({qty: usd}), tooling_usd, moq, lead_time_days, payment_terms.")],
    rationale: Annotated[str, Field(description="One or two sentences justifying the counter.")],
) -> dict[str, Any]:
    """BUYER SIDE — counter a quote. Returns the new quote version (status 'countered'). FICTIONAL demo data."""
    return _dump(_run(lambda: network.counter_offer(quote_id, proposed_changes, rationale)))


@server.tool()
def accept_quote(
    quote_id: Annotated[str, Field(description="Quote version to accept.")],
) -> dict[str, Any]:
    """BUYER SIDE — accept a quote version (only after the human founder has approved it). Returns an order DRAFT
    (fictional, not a real purchase order)."""
    return _dump(_run(lambda: network.accept_quote(quote_id)))


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
