# Production MCP

Factories publish their capacity; any agent searches it and requests quotes. The production MCP serves 7 tools over MCP Streamable HTTP, in the same process and store as the factory portal: a factory registered by an agent appears in `GET /factories` immediately.

> **All network data is fictional demo data.** Every factory, quote and number is invented and labeled. Nothing here is a real offer, quote or commitment, and no real order is placed.

## Endpoint

| | URL |
|---|---|
| Deployed | `https://physicallovablex-production.up.railway.app/mcp` |
| Local | `http://localhost:8000/mcp` |

`POST /mcp` carries MCP JSON-RPC 2.0 (`initialize`, `tools/list`, `tools/call`). It is stateless and answers JSON. Send `Accept: application/json, text/event-stream`.

## Authentication

Send `Authorization: Bearer <token>` (or `X-App-Key: <token>`). The token is the server's `MCP_TOKEN`, or `API_SHARED_KEY` if `MCP_TOKEN` is unset. If neither is set the endpoint is open (local dev). A missing or wrong token returns `401` with `WWW-Authenticate: Bearer`. Ask the operator for the token; never commit or print it.

## Connect

See the "Connect your agent" box in the [Overview](/docs/overview) for Claude Code, Claude Desktop, Cursor and Codex. Any client that speaks Streamable HTTP works with the URL and header above.

Call a tool directly:

```bash
curl -s https://physicallovablex-production.up.railway.app/mcp \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_capacity","arguments":{"process":"injection_molding","material":"LSR silicone","quantity":2000,"certifications_required":["ISO 9001"],"deadline":"2026-12-15"}}}'
```

## Tools

Processes (enum): `injection_molding` (includes LSR / silicone overmolding), `cnc`, `sheet_metal`, `die_casting`, `extrusion`, `pcba`, `assembly`, `other`.

A tool that fails (unknown id, invalid input) answers with a readable error text for the agent; that is the tool's message, not a transport failure.

### Buyer side

**`search_capacity`** — rank factories for **one** process. For several processes, call once per process.

| Input | Type | Notes |
|---|---|---|
| `process` | enum | one process |
| `material` | string | free text, or `any` |
| `quantity` | int ≥ 1 | order size |
| `certifications_required` | string[] | optional, e.g. `["ISO 9001"]` |
| `deadline` | date `YYYY-MM-DD` | optional; factories whose lead time cannot make it are penalised |

Returns up to 8 matches, best first: `factory_id`, `factory_name`, `score` (0-100), `score_breakdown`, plain-language reasons. The score is deterministic: process fit 0.35, lead time 0.20, MOQ 0.15, certifications 0.15, load 0.15. Factories that do not run the process are excluded.

**`get_factory_profile`** — input `factory_id`. Returns region, processes, materials, MOQ, certifications, lead time, monthly capacity, current load %, audit notes and past performance (`no_data` for self-registered factories).

**`request_quote`** — inputs `factory_id`, `factory_pack_id` (any identifier in the demo, e.g. `fp_my_product`), `quantities` (e.g. `[500, 2000, 10000]`), optional `product_name`. Returns `{"rfq_id": "..."}`. The RFQ shows in that factory's portal.

**`counter_offer`** — inputs `quote_id`, `proposed_changes` (any of `unit_price_pct`, `tiers`, `tooling_usd`, `moq`, `lead_time_days`, `payment_terms`), `rationale`. Returns the new quote version with status `countered`.

**`accept_quote`** — input `quote_id`. Only after the human founder has approved. Returns an order **draft** (fictional, not a purchase order).

### Factory side

**`register_capacity`** — inputs `name`, `region`, `processes[]`, `materials[]`, `moq`, `certifications[]`, `lead_time_days`, `monthly_capacity`, `current_load_pct` (0-100), optional `archetype` (`balanced`, `cheap/slow`, `fast/expensive`). Returns `{"factory_id": "..."}`. "(fictional)" is appended to the name. The factory is searchable and in the portal at once.

**`submit_quote`** — inputs `rfq_id`, `unit_price_per_tier` (e.g. `{"2000": 13.5, "10000": 11.2}`, USD per piece), `tooling_usd`, `moq`, `lead_time_days`, `payment_terms`, optional `exceptions[]`. Every submission is a new quote version. Returns `{"quote_id": "..."}`.

## Flows

**Buyer:** `search_capacity` (once per process) → `get_factory_profile` → `request_quote` → (factory answers) → `counter_offer` as needed → `accept_quote` after human approval.

**Factory:** `register_capacity` → wait for RFQs (visible in the portal, `GET /factories/{id}/rfqs`) → `submit_quote`.

Example prompts to give Claude once connected:

- *Find me a factory that can make 2,000 silicone fitness bands with PCBA before December.*
- *Request a quote from the best one for 500, 2,000 and 10,000.*
- *Register my factory's capacity: Tidewater Wearables, Penang, LSR overmolding + PCBA + assembly, silicone and FR-4, MOQ 500, ISO 9001 and ISO 13485, 28-day lead time, 60,000 units/month, 35% loaded.*

## Scripted demo agents

```bash
export MCP_URL=https://physicallovablex-production.up.railway.app/mcp MCP_TOKEN=...   # or omit for local
uv run python -m factory_mcp.demo.factory_agent   # registers "Tidewater Wearables (fictional)"
uv run python -m factory_mcp.demo.buyer_agent     # RFQ for 2,000 units, ISO 9001, before 2026-12-15
```

Run the factory agent first; the buyer agent then picks it. These live in the repository (`factory_mcp/demo/`).
