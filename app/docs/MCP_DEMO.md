# Production MCP — live demo

PhysicalLovableX's **production MCP**: factories publish their capacity, and *any* agent — Claude Desktop, Claude Code, a ChatGPT
connector, a buyer's own script — searches it and requests quotes. Same 7 tools as `factory_mcp/server.py`, now over HTTP at `/mcp`,
in the same process and store as the web portal (a factory registered by an agent shows up in the portal immediately).

> Every factory, quote and number is **fictional demo data**.

| | URL |
|---|---|
| Local | `http://localhost:8000/mcp` |
| Deployed | `https://physicallovablex-production.up.railway.app/mcp` |

**Token** = Railway's `MCP_TOKEN` (falls back to `API_SHARED_KEY` if `MCP_TOKEN` is unset; if neither is set the endpoint is open).
Send it as `Authorization: Bearer <token>` (or `X-App-Key: <token>`). Below, `$MCP_TOKEN` stands for that value.

## Connect

### Claude Code
```bash
# deployed
claude mcp add --transport http physicallovablex-production https://physicallovablex-production.up.railway.app/mcp \
  --header "Authorization: Bearer $MCP_TOKEN"

# local (API running on :8000, no token set locally → header optional)
claude mcp add --transport http physicallovablex-local http://localhost:8000/mcp
```
Check with `claude mcp list`, or `/mcp` inside a session. Team-shared config: add `--scope project` (writes `.mcp.json`).

### Claude Desktop
Settings → Developer → Edit Config (`claude_desktop_config.json`). Desktop speaks stdio, so bridge with `mcp-remote` (needs Node):
```json
{
  "mcpServers": {
    "physicallovablex-production": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://physicallovablex-production.up.railway.app/mcp",
               "--header", "Authorization:${AUTH_HEADER}"],
      "env": { "AUTH_HEADER": "Bearer PASTE_MCP_TOKEN_HERE" }
    }
  }
}
```
(For local: `"http://localhost:8000/mcp"` and drop the `--header` pair. `--allow-http` is needed by `mcp-remote` for non-localhost `http://` URLs only.)
Restart Claude Desktop; the tools appear under the 🔌/hammer icon. On paid plans, Settings → Connectors → *Add custom connector* with
the deployed URL also works for servers that need no header — ours needs the token, so use the config above.

### ChatGPT / any other MCP client
Streamable HTTP, URL as above, header `Authorization: Bearer <token>`. Quick check without any client:
```bash
curl -s https://physicallovablex-production.up.railway.app/mcp \
  -H "Authorization: Bearer $MCP_TOKEN" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | head -c 300
```

### Scripted agents (no Claude needed)
```bash
cd 04_LIVRABLE/mvp
export MCP_URL=https://physicallovablex-production.up.railway.app/mcp MCP_TOKEN=…   # or omit for http://localhost:8000/mcp
uv run python -m factory_mcp.demo.factory_agent   # registers "Tidewater Wearables (fictional)" → in GET /factories, ranks #1
uv run python -m factory_mcp.demo.buyer_agent     # LSR overmolding + PCBA, 2,000 units, ISO 9001, before 2026-12-15 → profile → RFQ
```
Both print a readable transcript. The factory agent also checks `GET /factories` (`--api`, `--api-key` / `API_SHARED_KEY` if the API is gated).
Run the factory agent first: the buyer agent then picks it.

## ≈80-second demo (two prompts in Claude)

Measured live (Claude Code): ≈52 s + ≈28 s ≈ 80 s. **Not three prompts:** Claude typically calls `request_quote` on its own while answering the first prompt, so a separate "request a quote" prompt mostly duplicates it and pushes the total to ≈100 s, over the slot. If Claude stops after the shortlist without requesting a quote, add one short follow-up ("Request it.") rather than the longer scripted second prompt.

Before: `curl -X POST -H "X-App-Key: $API_SHARED_KEY" …/demo/reset` for a clean network (15 fictional partners (11 factories, 1 integrator, 3 installers)), portal open in a tab.

| # | Type in Claude | What the jury sees |
|---|---|---|
| 1 (0:00, ≈52 s) | *Find me a factory that can make 2,000 silicone fitness bands with PCBA before December, and request a quote from the best one for 500, 2,000 and 10,000.* | Claude calls `search_capacity` twice (injection molding / LSR silicone, then PCBA), `get_factory_profile`, then `request_quote` — a ranked shortlist with score /100 and reasons (process fit, MOQ, ISO 9001, load, lead time vs. the deadline), naming the one factory covering both processes, then an `rfq_id`. Switch to the web portal → that factory's RFQ list shows the new RFQ. |
| 2 (≈0:52, ≈28 s) | *Register my factory's capacity: Tidewater Wearables, Penang, LSR overmolding + PCBA + assembly, silicone and FR-4, MOQ 500, ISO 9001 and ISO 13485, 28-day lead time, 60,000 units/month, 35% loaded.* | `register_capacity` → a `factory_id`. Refresh the portal: **Tidewater Wearables (fictional)** is listed. Re-run prompt 1's search: it now ranks #1 (measured 96/100 for "LSR silicone + PCBA, 2,000 units" in one rehearsal — read the actual score on screen). |

Closing line: *"That factory never had a public API. Now it has one — and Claude, ChatGPT or our own buyer agent can use it the same way."*

Backup if the network is bad: run the two scripted agents locally (above) — same story, printed transcript.

## Why

- **Capacity data does not exist publicly.** Factories don't publish MOQ, free capacity, certifications or lead times; the only sources are
  marketplaces built for humans (1688, Alibaba) and personal relationships. There is nothing for an agent to query.
- **The MCP creates it.** `register_capacity` is onboarding: a factory (or its agent) states what it can make and how loaded it is, once, and
  that record becomes searchable, comparable and quotable — with a deterministic, explainable score (process fit 0.35, lead time 0.20,
  MOQ 0.15, certifications 0.15, load 0.15), not a black box.
- **Any agent can use it.** One open protocol, one endpoint: our Studio's matching stage, a founder's Claude, a procurement team's own
  script, a factory's agent answering RFQs (`submit_quote`). The platform is the network, not the interface — think Waniwani for industrial
  capacity.
- **Honest about the demo:** the 11 factories, 1 integrator and 3 installers are fictional; self-registered ones show "not audited / no past performance data".

## Tools
| Tool | Side | Purpose |
|---|---|---|
| `search_capacity(process, material, quantity, certifications_required?, deadline?)` | buyer | ranked matches for **one** process — call once per process |
| `get_factory_profile(factory_id)` | buyer | capacity, audit notes, past performance |
| `request_quote(factory_id, factory_pack_id, quantities[], product_name?)` | buyer | RFQ → `rfq_id` |
| `counter_offer(quote_id, proposed_changes, rationale)` / `accept_quote(quote_id)` | buyer | negotiation loop → order **draft** |
| `register_capacity(name, region, processes[], materials[], moq, certifications[], lead_time_days, monthly_capacity, current_load_pct)` | factory | publish capacity → `factory_id` |
| `submit_quote(rfq_id, unit_price_per_tier, tooling_usd, moq, lead_time_days, payment_terms, exceptions?)` | factory | answer an RFQ → `quote_id` |

Processes: `injection_molding` (incl. LSR / silicone overmolding), `cnc`, `sheet_metal`, `die_casting`, `extrusion`, `pcba`, `assembly`, `other`.

## Troubleshooting
- **401 Unauthorized** — token missing/wrong. It is `MCP_TOKEN` on Railway (or `API_SHARED_KEY` if `MCP_TOKEN` is unset).
- **Claude Desktop shows no tools** — check the JSON, restart the app, run `npx -y mcp-remote <url> --header "Authorization:Bearer …"` in a terminal to see the error.
- **A tool answers with an error text** (e.g. unknown `factory_id`) — that is the tool's own message to the agent, not a transport failure.
- Standalone without the API: `uv run python -m factory_mcp.http --port 8123` → `http://127.0.0.1:8123/mcp` (same store if the same env).
