# PhysicalLovableX — MVP

Idea or prototype → 13 stages → Factory Pack → Launch Dossier. Specs: `../PRD.md`, `../PLAN.md`, `../MONITOR.md`.

## Run
```bash
# API (from mvp/) — Python 3.12 via uv
cp .env.example .env            # add OPENROUTER_API_KEY + the 3 model routes; without a key every stage serves fixtures
uv sync
uv run uvicorn api.main:app --port 8107         # any free port; keep 8000/3000 for the deployed setup
# parallel dev sessions: isolate state, e.g. DB_PATH=api/data/w7.db FILES_DIR=api/data/files_w7 (the factory store follows: api/data/w7_network.db)
curl -X POST localhost:8107/demo/reset          # seeds the 2 cached examples (desk lamp, tracker card) + resets the factory network

# Web
cd web && npm install && NEXT_PUBLIC_API_URL=http://localhost:8107 npm run dev

# Tests (offline, no key, temp DB/network/CAD dirs — covers tests/, api/, factory_mcp/)
uv run pytest

# The 10 PRD test prompts against a running API (live if the key is set) → tests/results/<timestamp>.md
uv run python tests/run_prompts.py --base-url http://localhost:8107 [--only 3,4,5]

# Production MCP server (stdio) — see factory_mcp/README.md for Claude Code / Desktop config
uv run python -m factory_mcp.server
```

Env guards: `LLM_MAX_TOKENS` (per request), `LLM_MAX_REQUESTS` (per API process), `LLM_TIMEOUT_S`,
`LLM_REASONING_EFFORT` (default `low`), `STAGE_TIMEOUT_S` (default 45 — hard cap per stage and on the Factory Pack, then the
cached fixture with reason "timeout"). Key stays server-side; `.env` is gitignored.

Autorun is asynchronous (serverless-friendly): `POST /projects/{id}/autorun` → 202, then poll `GET /projects/{id}` every 2 s
(`autorun.state`, `autorun.current_stage`, per-stage status). `?wait=true` keeps the synchronous behaviour for scripts.

Latest live run: `tests/results/` (10/10 pass, wow screen ≈ 1 min per prompt — see the report for per-stage times).

## Deploy
Web on Vercel (root `web/`), API + CAD on Railway (`Dockerfile` + `railway.toml`, volume at `/data`). Full click-by-click steps,
env vars, rollback and costs: **`docs/DEPLOY.md`**. Agents prepare, the owner clicks deploy.

| Env (API) | Effect |
|---|---|
| `API_SHARED_KEY` | set → every route except `GET /health` (files included) needs header `X-App-Key`; unset → open (local dev). The web password (`APP_PASSWORD`) is a separate, web-only variable |
| `MAX_STORED_PROJECTS` | keep only the N most recent generated-CAD folders in `FILES_DIR` (default 30; Railway trial volume ≈ 0.5 GB) |
| `CORS_ORIGINS` | comma-separated allowed web origins (default `http://localhost:3000`) |
| `RATE_LIMIT_PER_DAY` | live runs per client IP per 24 h on `POST /projects`, `/stages/*/run`, `/autorun` (default 20, 0 = off; only when a key is set) → 429 |
| `DEMO_READONLY=1` | no live AI runs (403); cached demo projects, fixtures, portal and PDF still work — zero-cost public mode |
| `SEED_DEMO_ON_EMPTY=1` | seed the two demo projects at startup when the DB is empty (set in the Docker image) |
| `DB_PATH`, `FILES_DIR`, `FACTORY_MCP_DB` | `/data/app.db`, `/data/files`, `/data/network.db` in the image (Railway volume) |

Local container check: `docker build -t plx-api . && docker run -p 8000:8000 plx-api` (peak ≈ 365 MiB for a CAD build + export; image 2.0 GB, ≈ 470 MB compressed).
Honesty audit of the numbers shown to users: `docs/HONESTY_AUDIT.md`.

## Contracts (read before coding)
- `contracts/artifacts.py` — Pydantic models for the 13 stage artifacts, Factory Pack, network records, `Label`, `LabeledValue`.
- `contracts/api.md` — routes · `contracts/stage_runner.md` — plug-in API · `contracts/fixtures.md` — fixture layout.
- Regenerate schemas + TS types after a (Monitor-approved) contract change:
  `uv run python -m contracts.export_schemas && (cd web && npm run gen:types)`.

## Layout and owners
| Folder | Owner |
|---|---|
| `contracts/`, `api/main.py`, `api/llm.py`, `api/db.py`, `api/discovery.py`, `api/stages/` | W0 (W7 for integration fixes) |
| `web/` | W1 |
| `api/cad/`, `api/dfm/` | W2 |
| `api/costs/` | W3 |
| `api/agents/` (except `negotiation/`) | W4 |
| `factory_mcp/`, `api/agents/negotiation/` | W5 |
| `api/fixtures/`, `api/export/`, `tests/` | W6 |

Stage modules register with `@stage_handler(n)` and are auto-discovered at startup; nobody edits `api/main.py`.
Every LLM call goes through `api.llm.complete_json` (JSON schema validation + 1 retry); any stage failure serves the
cached fixture with `fallback: true` and a visible "Cached example" banner — the demo never 5xx's on an AI failure.

## Real vs simulated
Honesty labels everywhere (screen + PDF): **Measured** (computed on the CAD), **Sourced** (real price/official rate +
date + URL), **Estimate** (assumption shown), **Fictional — demo data**. Factory names are invented and end with "(fictional)".

| Stage / artifact | What is real | What is simulated or estimated | Label |
|---|---|---|---|
| 1 Brief | Live LLM (main route), ≤5 clarifying questions with defaults, idea + prototype (pasted BOM) modes | Target price when not stated | Estimate |
| 2 Design | 3 parametric directions (LLM proposes, code clamps), real GLB per direction | AI concept renders are illustrative, not the CAD | — |
| 3 CAD + spec | build123d two-shell enclosure → STEP / STL / GLB; dimensions from the STEP bounding box | Weight = measured volume × assumed density; BOM proposed by the LLM | Measured / Estimate |
| 4 DFM | **Measured** draft, undercut, projected area, wall thickness on the STEP (port of text-to-cad DFM, MIT); AI-reviewed alerts with cited rules (never contradict a measurement); rule-based certification map by market; component risk from the LCSC snapshot | Certification costs/lead times; clamp tonnage formula | Measured / Sourced / Estimate |
| 5 Investment | **Real LCSC/JLCPCB prices + stock** (snapshot 2026-09-26) for matched electronic lines; deterministic cost engine, 3 volumes, tooling, cash, margin, break-even | Mechanical parts, assembly, tooling ranges, unmatched parts | Sourced / Estimate |
| 6 Production plan | Process per part with reason | Lead times | Estimate |
| 7 Matching | Deterministic scoring via the production MCP (`search_capacity`) | **The 8 factories and their capacity** | Fictional — demo data |
| 8 RFQ + negotiation | Real agent loop over the MCP tools (`request_quote` → `submit_quote` → `counter_offer` → `accept_quote`), LLM factory agents with distinct personalities, clamped by policy | **Quotes, replies, final terms** | Fictional — demo data |
| 9 Tooling + samples | Milestones computed from the negotiated lead time; payment split follows the approved quote's terms; date checks | Durations beyond the quote | Estimate / Fictional |
| 10 QC | ISO 2859-1 sample size (General II), defects mapped to spec lines, $268/man-day benchmark | Inspection days | Sourced / Estimate |
| 11 Logistics | HTS from the closest **CBP CROSS ruling precedent** + cached USITC schedule (general rate Sourced; Section 301 Sourced when a ruling cites a 9903.88.xx heading, e.g. lamp 8513.10.40.00 = 3.5 % + 25 %, tracker 8517.62.00.90 = Free + 7.5 %); sea freight derived from the **Drewry WCI** lane rate (Sourced) | Classification itself (precedent, not binding — confirm with a broker), LCL/FCL derivation and air $6/kg by chargeable weight (Estimate), transit days (Fictional) | Sourced / Estimate / Fictional |
| 12 Financing | Cash curve = stage 5 total cash, allocated to stage 9 milestones | Financing options are typical ranges | Estimate |
| 13 Brand | Live LLM name options, packaging spec, landing copy, Shopify + Amazon drafts | — | Estimate |
| Factory Pack / PDF | Assembled from stages 1-6; CN machine translation via the CN route (labeled "to be reviewed by a native speaker") | — | as per source |

Cached examples (`api/fixtures/desk_lamp`, `api/fixtures/tracker_card`, regenerated by their `build_*.py`): measured DFM
values are the real output of `api/dfm/measure.py` on `api/cad/prebuilt/<id>/enclosure.step`; landed cost, duties,
freight and stages 11-12 are computed by the live `api/costs` code (`api/fixtures/_live.py`); LCSC prices are real
(jlcsearch, 2026-09-26); design images: `dN.png` = AI concept render (illustrative), `hero_dN.png` = rendered from the CAD.
