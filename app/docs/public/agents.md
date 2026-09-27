---
name: physicallovablex
description: Turn a plain-language physical product idea into a 3D concept with costs, factory shortlist, engineering checks and a Launch Dossier, using the PhysicalLovableX Studio API and production MCP.
when_to_use: The user wants to design, refine or prepare a physical product for manufacturing (wearable, drone, lamp, furniture, appliance, ...), find or quote factories, or get a landed-cost and launch plan. Not for software products, and not for placing real orders.
docs: https://physicallovablex.vercel.app/docs/overview
---

# PhysicalLovableX for agents

Set up and use PhysicalLovableX with minimal friction. Two surfaces: the **production MCP** (factory search, RFQs; 7 tools) and the **Studio REST API** (create, refine, Make it, export). Everything about factories is fictional demo data.

## 1. Connect

Prefer MCP for factory work. If your client supports remote MCP, add the server:

```bash
claude mcp add --transport http physicallovablex-production \
  https://physicallovablex-production.up.railway.app/mcp \
  --header "Authorization: Bearer $MCP_TOKEN"
```

Other clients: Streamable HTTP, URL `https://physicallovablex-production.up.railway.app/mcp`, header `Authorization: Bearer <token>`. Stdio-only clients (Claude Desktop): bridge with `npx -y mcp-remote <url> --header "Authorization:${AUTH_HEADER}"`. See [Overview](https://physicallovablex.vercel.app/docs/overview).

The MCP has no tools for creating or refining products. For that, use the REST API (fallback and primary for Studio): base URL is the API host the user gives you (`http://localhost:8000` locally).

Verify the connection:

```bash
curl -s $API/health
```
```json
{"status":"ok","version":"...","llm_configured":true,"models":{},"registered_stages":[1,2,3,4,5,6,7]}
```

## 2. Authenticate

Ask the user for the token or key. **Never print, log, echo or store it in files or memory.** Read it from an environment variable.

- MCP: `Authorization: Bearer $MCP_TOKEN` (or `X-App-Key`). `401` means missing or wrong.
- REST: `X-App-Key: $APP_KEY` on every route except `GET /health`. `401` means missing or wrong. If the user says the API is local and ungated, no header is needed.

## 3. Create a product from the user's intent

Use the user's words. Do not invent dimensions, prices or specs they did not give.

```bash
curl -s -X POST $API/projects -H "X-App-Key: $APP_KEY" -H "Content-Type: application/json" \
  -d '{"mode":"idea","prompt":"A screenless wrist-worn fitness band, 5-day battery, tracks sleep and strain."}'
```
```json
{"id":"p_...","name":"...","mode":"idea"}
```

Then start the Studio (returns `202`, `{"version":1}`), and poll until version 1 is done:

```bash
curl -s -X POST $API/projects/$PID/studio/start -H "X-App-Key: $APP_KEY"
curl -s $API/projects/$PID/versions -H "X-App-Key: $APP_KEY"    # poll every 1-2 s
```

Wait for `status: "done"`. `render_pending`, `background_pending` and `cad_pending` may stay true a little longer (render, DFM review, the AI-written CAD model); the product is usable before they clear. The CAD program is at `preview.code_url` (`GET /projects/{id}/cad/code/{k}`).

To start from a recorded example instead, `GET /examples` and open one (no AI cost).

Use `mode: "prototype"` with `pasted_bom` when the user has a working prototype and a BOM.

## 4. Refine iteratively and read the diff

One change per prompt keeps diffs readable.

```bash
curl -s -X POST $API/projects/$PID/refine -H "X-App-Key: $APP_KEY" -H "Content-Type: application/json" \
  -d '{"message":"Add heart-rate and HRV sensing"}'
# → {"version":2}
curl -s $API/projects/$PID/versions/2 -H "X-App-Key: $APP_KEY"
```
```json
{"n":2,"status":"done","changes":[{"area":"component","label":"Component added","after":"Optical heart-rate sensor (PPG) × 1 — LCSC C6454833, $12.18/unit","label_kind":"sourced"}],"is_current":true}
```

For a change of form the parameters cannot express ("wider nose", "add two storage baskets"), just say it in the message; the server uses `regenerate_geometry` and edits the CAD program (`cad_pending`). Read `changes[]` and report each with its `label_kind`. Clamped values appear as notes: tell the user when a request was clamped. If `status` is `failed`, relay `error` (nothing changed; the previous version is still current). `409` means a refine or autorun is running or the Studio has not started: wait and retry. To go back: `POST /projects/$PID/versions/{n}/restore`.

## 5. Check engineering and build strategy

```bash
curl -s $API/projects/$PID/engineering -H "X-App-Key: $APP_KEY"
```

Report: `category_title` (categories include drone, hair dryer, camera and smartphone), each entry of `checks[]` (`verdict`, `value`, `threshold`), `risks[]`, `tests[]`, `build_strategy` (`full_design`, `module_assembly` or `odm_customization`, with `customisable[]`, `not_customisable[]`, `path[]` and Estimate figures for `moq`, `entry_cost`, `lead_time`; say plainly when the honest path is an ODM), and `prototype` (`total_cost`, `timeline_weeks`). If `firmware.pending_llm` is true, GET again later. Call `POST /projects/$PID/engineering/recompute` after a refine if the data looks stale. Surface every `warn` and `fail`.

For factories, use MCP: `search_capacity` (one call per process: `injection_molding`, `cnc`, `sheet_metal`, `die_casting`, `extrusion`, `pcba`, `assembly`, `other`), then `get_factory_profile`, then `request_quote`. Example call:

```json
{"name":"search_capacity","arguments":{"process":"injection_molding","material":"LSR silicone","quantity":2000,"certifications_required":["ISO 9001"],"deadline":"2026-12-15"}}
```

## 6. Make it and fetch the Launch Dossier

```bash
curl -s -X POST "$API/projects/$PID/autorun?through=13" -H "X-App-Key: $APP_KEY"    # 202
curl -s $API/projects/$PID -H "X-App-Key: $APP_KEY"                                  # poll every 2 s
```
```json
{"autorun":{"state":"running","current_stage":8,"completed_stages":[1,2,3,4,5,6,7],"through":13}}
```

Wait for `autorun.state` to be `done` (about a minute in the recorded run; do not assume that duration). If `failed`, relay `autorun.error`. Then:

```bash
curl -s $API/projects/$PID/export -H "X-App-Key: $APP_KEY" -o launch-dossier.pdf
curl -s $API/projects/$PID/factory-pack -H "X-App-Key: $APP_KEY"
```

Tell the user the file path. In Make it, the recommended quote is auto-approved and carries assumption `a8_autofill`: say so, and tell the user to review the selected factory.

## 7. Rules

1. **Never present Fictional or Estimate values as facts.** Quote the label with every figure: "unit cost $26.55 at 2,000 units (Estimate)". Factories, quotes, freight and transit days are always **Fictional — demo data**.
2. **Never place real orders.** `accept_quote` returns a fictional order draft and only after the human has approved. Do not tell the user a factory has agreed to anything real.
3. **Surface risks.** Report `warn`/`fail` checks, certification rows, component risks (for example low-stock or single-source LCSC parts), and clamped requests. Do not hide a `fallback: true` result: say "Cached example — this may not be the user's product".
4. **Be honest about scope.** Concept-level CAD; the firmware skeleton is "not compiled or tested"; humans sign off design freeze, certification and any order. See [Limits](https://physicallovablex.vercel.app/docs/limits).
5. **Respect limits.** Poll versions every 1-2 s and project status every 2 s, not faster. On `429`, back off and tell the user; on `403`, the deployment is read-only (`studio/start`, `refine`, restore and `engineering/recompute` are blocked). Do not loop refines automatically; each live run costs the operator money.
6. **Protect secrets.** Never print tokens or keys, and never put them in URLs or committed files.
7. **Don't invent.** If a field, route or tool is not in the [docs](https://physicallovablex.vercel.app/docs/studio-api), say you do not know instead of guessing.

## Example prompts

- "Design a screenless fitness band with a 5-day battery, add heart-rate sensing, make it pink, then show me what changed." → steps 3-4.
- "Is it safe for kids?" (for a changing table) → step 5: read `standards[]`, `tests[]`, `checks[]`; state that the references guide the work and do not certify it.
- "Find a factory for 2,000 units of this, before December." → MCP `search_capacity` per process, `get_factory_profile`, then ask the user before `request_quote`.
- "Give me the launch package." → step 6.

## Reference

[Overview](https://physicallovablex.vercel.app/docs/overview) · [Quickstart](https://physicallovablex.vercel.app/docs/quickstart) · [Concepts](https://physicallovablex.vercel.app/docs/concepts) · [Studio API](https://physicallovablex.vercel.app/docs/studio-api) · [Production MCP](https://physicallovablex.vercel.app/docs/production-mcp) · [Engineering](https://physicallovablex.vercel.app/docs/engineering) · [Limits](https://physicallovablex.vercel.app/docs/limits)
