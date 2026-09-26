# factory_mcp/ — Production MCP (PRD §10)

**Owner: W5.** The "Alibaba layer": a fictional production network exposed as an MCP server, so **any agent**
(ours, Claude, ChatGPT, a buyer's own agent) can query capacity the same way. Research (E_usines.md) found no
public capacity API: the network *creates* the data through factory onboarding (`register_capacity`).

> Everything here is **Fictional — demo data**: the 8 factories, their capacity, quotes, replies and past performance.
> Every name ends with "(fictional)".

| File | What |
|---|---|
| `network.py` | Plain Python (no MCP import): SQLite store + the 7 tools + `list_factories / get_factory / list_rfqs` (factory portal) |
| `server.py` | MCP server (official SDK v2 `MCPServer`, ex-`FastMCP`) exposing the 7 tools over `network.py` |
| `data/factories.json` | 8 seed factories (W0's 4 ids kept + mould maker, box-build EMS, die-caster, 1688-style workshop) |
| `data/seed_rfqs.json` | Demo RFQs for the desk lamp (portal history) |
| `data/network.db` | Runtime state (gitignored). Path: `$FACTORY_MCP_DB`, else next to `$DB_PATH` (`app.db` → `factory_network.db`, `<name>.db` → `<name>_network.db`, so isolated DBs never share a store), else here. SQLite WAL |

## Tools
| Tool | Caller | Returns |
|---|---|---|
| `register_capacity(name, region, processes[], materials[], moq, certifications[], lead_time_days, monthly_capacity, current_load_pct)` | factory | `factory_id` |
| `search_capacity(process, material, quantity, certifications_required[], deadline?)` | platform | ranked `FactoryMatch[]` with `score_breakdown` + `reasons` |
| `get_factory_profile(factory_id)` | platform | `Factory` (capacity, audit notes, past performance) |
| `request_quote(factory_id, factory_pack_id, quantities[])` | platform | `rfq_id` |
| `submit_quote(rfq_id, unit_price_per_tier{qty: usd}, tooling_usd, moq, lead_time_days, payment_terms, exceptions[])` | factory agent | `quote_id` (new version) |
| `counter_offer(quote_id, proposed_changes{unit_price_pct, tiers, tooling_usd, moq, lead_time_days, payment_terms}, rationale)` | platform agent | new `Quote` version (`countered`) |
| `accept_quote(quote_id)` | platform, after founder approval | order draft |

`search_capacity` is deterministic: score = 100 × (0.35 process fit + 0.15 MOQ + 0.15 certifications + 0.15 load
+ 0.20 lead time); factories that do not run the process are excluded; ties break on id.

## Run
```bash
cd 04_LIVRABLE/mvp
uv run python -m factory_mcp.server          # stdio
```

**Claude Code**
```bash
claude mcp add physicallovablex-production -- uv --directory /ABS/PATH/04_LIVRABLE/mvp run python -m factory_mcp.server
```

**Claude Desktop** (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "physicallovablex-production": {
      "command": "uv",
      "args": ["--directory", "/ABS/PATH/04_LIVRABLE/mvp", "run", "python", "-m", "factory_mcp.server"]
    }
  }
}
```
Then ask e.g. "Which factories can injection-mould PC/ABS at 2,000 units with ISO 9001?".
The API (stages 7-8, factory portal) and the MCP server share the same store when run with the same env.

## Tests
```bash
uv run pytest factory_mcp api/agents/negotiation     # offline, temp store, no key
```
