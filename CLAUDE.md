# AGENTS.md — guide for AI assistants analysing this repository

This file is for an AI assistant (Claude, Codex, Cursor, …) asked to read, explain or evaluate this repository. Humans should start with `README.md`.

## Purpose

PhysicalLovableX is a case-study MVP built in three days (26-28 September 2026). A founder describes a physical product in one sentence; the app produces a 3D model from AI-written CAD, unit costs at three volumes, a factory shortlist, and, after **Make it**, a 13-step plan ending in a Launch Dossier (EN + CN). The thesis: hardware ships late because nobody translates the idea into what a factory can build. The primitive is the **Factory Pack**, a spec package a factory can quote from. Product definition: `docs/PRODUIT.md` (one page) and `docs/PRD.md` (full). If they differ, `PRD.md` wins.

The repository also contains the go-to-market work: `gtm-harness/` (agent harness for founder-led outreach) and `gtm/` (landing copy, sequences, content plan, video scripts).

## How to navigate

Read contracts before code. The contracts are the single source of truth for the data shapes and routes.

| Step | Read | Why |
|---|---|---|
| 1 | `app/contracts/api.md` | Every route. Sections are added per worker session (W17 Studio, W20 Engineering, W22 MCP over HTTP, W29 parts and anatomy, C2 assembly, C3 drawings) |
| 2 | `app/contracts/artifacts.py` | Pydantic models for the 13 stage artifacts, the Factory Pack, `Label`, `LabeledValue` |
| 3 | `app/README.md` | Run commands, env guards, folder owners, the stage-by-stage "Real vs simulated" table |
| 4 | `app/api/main.py`, `app/api/discovery.py` | App startup; stage modules and plug-in routes are auto-discovered (`@stage_handler(n)`, `register(router)`) |
| 5 | The module for the question (table below) | |

Generated files: `app/contracts/schemas/*.json` and `app/web/src/types/contracts.ts` come from `artifacts.py` (`uv run python -m contracts.export_schemas && (cd web && npm run gen:types)`). Do not treat them as hand-written.

## Key facts, with files

- **Stage runner.** 13 stages in 4 phases (Design 1-3, Make it manufacturable 4-6, Source 7-8, Launch 9-13). Any handler exception serves the cached fixture with `fallback: true`; each stage has a hard time cap (`STAGE_TIMEOUT_S`, default 45 s). `app/api/stages/runner.py`, `app/api/stages/registry.py`.
- **LLM calls.** All go through `app/api/llm.py` (`complete_json`: JSON-schema validation, one retry) to OpenRouter on routes main, fast, CN and image (`app/.env.example`).
- **Studio.** Each prompt creates a version; a job commits stages 1-7 at once or nothing, so a failed refine leaves the previous version current. A refine is one LLM call that returns typed ops (`set_color`, `add_component`, `set_dimensions`, …), then code applies them deterministically and re-clamps every value. `app/api/studio/engine.py`, `app/api/studio/patch.py`, `app/api/studio/apply.py`; contract in `api.md` "Studio (W17)".
- **Text-to-CAD.** The LLM writes or edits a full build123d program starting from a tested parametric seed; the program runs in a sandbox (AST policy + isolated subprocess); the result is validated (real solids, bounding box within 0.5×-2× of the requested size) and, on failure, the error goes back to the LLM (up to 2 repairs), else the seed is built. `app/api/cad/codegen/engine.py`, `sandbox.py`, `classify.py`.
- **Part edits.** Clicking a part and changing colour, material or a parameter is deterministic, with no LLM call. `app/api/studio/parts.py`, `app/api/studio/edit.py`.
- **Anatomy.** Internal layout generated from the BOM, no LLM, always labelled "Illustrative internal layout — not a routed PCB". `app/api/cad/anatomy/`.
- **DFM.** Draft, undercut, projected area and wall thickness are measured on the STEP (ported from text-to-cad, MIT). The AI review may add alerts but never contradicts a measurement. `app/api/dfm/measure.py`, `app/api/agents/dfm_review.py`.
- **Costs.** Python computes every number; the LLM only proposes BOM lines. Electronic lines are matched to a dated LCSC snapshot. `app/api/costs/engine.py`, `bom.py`, `lcsc.py`; landed cost, HTS and freight in `landed.py`, `hts.py`, `precedent.py`, `freight.py`.
- **Engineering.** Physics checks on the measured CAD, electronics architecture and power budget, firmware skeleton, prototype path, build strategy. `app/api/engineering/service.py` and siblings.
- **Production MCP.** 7 tools (`register_capacity`, `search_capacity`, `get_factory_profile`, `request_quote`, `submit_quote`, `counter_offer`, `accept_quote`) in `app/factory_mcp/server.py`, served over stdio and over HTTP at `/mcp` (`app/api/mcp_http/`). Setup: `app/docs/MCP_DEMO.md`. Agent guide: `app/docs/public/agents.md`.
- **Factory Pack and Dossier.** `app/api/export/factory_pack.py`, `app/api/export/pdf.py`.
- **Web.** Next.js app in `app/web/`; Studio screen `app/web/src/app/projects/[id]/studio/page.tsx`; public docs rendered from `app/docs/public/*.md`.
- **Pro CAD, shipped and on by default.** Standard fasteners, inserts and bosses with ISO 273 clearance holes (`CAD_DETAIL_LEVEL=pro`, `app/api/cad/stdparts/`); assemblies with joints and measured interference / clearance checks (`CAD_ASSEMBLY=1`, `app/api/cad/assembly/`; 0 interferences on all showcases, and it caught and fixed a real propeller collision on the drone); dimensioned technical drawings in the Studio, Factory Pack and Dossier (`CAD_DRAWINGS=1`, `app/api/cad/drawings/`). Contracts: `app/contracts/api.md` "Assembly (C2)" and "2D technical drawings (C3)".

## Do not assume

- **Factories, quotes and freight are fictional demo data.** All 15 partners (11 factories, 1 integrator, 3 installers), their capacity, quotes, negotiation replies, past performance, carrier freight quotes and transit days are invented. Names end with "(fictional)". The negotiation is a real agent loop over the MCP tools, but the replies are simulated. In Make it, the quote is auto-approved and flagged as such.
- **Internal layouts are illustrative.** Anatomy is not a routed PCB. No PCB layout is produced; electronics stop at a power tree and netlist-level connections.
- **Firmware is generated, not compiled or tested.**
- **CAD is concept-level**, not tooling-ready.
- **HTS classification is a precedent from CBP rulings**, not a binding ruling.
- **The CN text is machine-translated** and labelled for native review.
- **Numbers carry labels: quote them with their label.** Measured (computed on the CAD), Sourced (real price or rate, with source and date), Estimate (assumption shown), Fictional — demo data. Write "$27.64 per unit at 2,000 (Estimate)", not "$27.64 per unit".
- **Timings are live measurements that vary between runs.** Quote the ranges and name the file (`docs/PRODUIT.md`, `app/docs/DEMO_SCRIPT.md`, `app/docs/QA_REPORT.md`).
- **No customers, no revenue.** The business model in `docs/PRD.md` §17 is a hypothesis.
- **Documents reference files that are not in this repository**: planning and discovery material kept private. If a path cited in a document does not exist here, say so; do not infer its content.
- **Some GTM files were excluded from the export** because they contained contact data. `gtm-harness/outputs/` keeps public names and URLs only.

## Tests and QA evidence

- Backend tests: `app/tests/`, plus `test_*.py` files inside `app/api/` and `app/factory_mcp/` (`testpaths` in `app/pyproject.toml`). They run offline with temporary databases and no API key.
- QA history: `app/docs/QA_REPORT.md`, one section per wave, with verdict, test counts, timings, live spend and an open-bug table with severity. Final whole-suite run: 719 passed, 31 skipped (section "C5 — pro CAD integration (28 Sep)" in `app/docs/QA_REPORT.md`; verdict "ready for pass-7"), including the pro CAD tests (`app/tests/test_c1_stdparts.py`, `test_c2_assembly.py`, `test_codegen_rag.py`, `test_drawings.py`).
- CAD benchmark: `app/docs/CAD_BENCH.md` (harness `app/tests/cad_bench.py`, renders in `app/docs/screens/cad_bench/`).
- Honesty audit of labels: `app/docs/HONESTY_AUDIT.md` (script `app/docs/audit_honesty.py`).
- Raw test outputs (`tests/results/`) are not in the export; the QA report summarises them.

## How to run

```bash
cd app
uv sync && (cd web && npm install)
scripts/demo_start.sh                  # API :8000, web :3000, seeds demos and showcases, prints READY
uv run pytest                          # offline
cd web && npx tsc --noEmit && npm run lint && npm run build
```

Without `OPENROUTER_API_KEY`, every AI stage serves its cached example; the 11 recorded showcases still open fully, with no model calls. Deploy: `app/docs/DEPLOY.md`.

## Questions this repo can answer, and where

| Question | Files |
|---|---|
| How does a refine work end to end? | `app/contracts/api.md` "Studio (W17)" → `app/api/studio/routes.py` → `engine.py` (job queue, commit) → `patch.py` (LLM → typed ops) → `apply.py` (deterministic apply) → `app/api/cad/codegen/engine.py` `refine_cad` (geometry edits) → web `app/web/src/app/projects/[id]/studio/page.tsx` |
| How does the AI write and repair CAD? | `app/api/cad/codegen/engine.py`, `sandbox.py`, `retrieval.py`; evaluation `app/docs/CAD_BENCH.md` |
| How is unit cost computed, and what is sourced? | `app/api/costs/engine.py`, `lcsc.py`, `landed.py`; `app/README.md` "Real vs simulated" |
| How are duties and freight derived? | `app/api/costs/hts.py`, `precedent.py`, `freight.py`, `landed.py` |
| What happens when the AI fails? | `app/api/stages/runner.py`, `app/api/llm.py`, `app/contracts/api.md` (header), `app/docs/public/limits.md` "Availability behaviour" |
| How does an external agent get a quote? | `app/factory_mcp/server.py`, `app/factory_mcp/network.py`, `app/api/mcp_http/`, `app/docs/MCP_DEMO.md`, `app/docs/public/production-mcp.md` |
| How does Make it autofill stages 8-13? | `app/contracts/api.md` `/autorun?through=13`, `app/api/agents/negotiation/`, `app/api/agents/` (tooling, QC, planning, brand) |
| What is in a Factory Pack? | `app/contracts/artifacts.py` (`FactoryPack`), `app/api/export/factory_pack.py`, `docs/PRD.md` §8.1 |
| What does the Anatomy view show and how is it built? | `app/api/cad/anatomy/` (`layout.py`, `packages.py`, `mesh.py`), `app/contracts/api.md` "3D parts & anatomy" |
| How reliable is it? Known bugs? | `app/docs/QA_REPORT.md` |
| Who is the customer and how is it sold? | `gtm-harness/CLAUDE.md`, `gtm-harness/context/icp.md`, `signals.md`, `positioning.md`, `docs/PRD.md` §4, §17 |
| How was it built? | `app/README.md` "Layout and owners", `app/contracts/`, `app/docs/QA_REPORT.md`, `README.md` "How it was built" |

## Tone for answers about this repo

Be precise and cite paths. Separate what is built from what is planned, and what is measured from what is estimated or fictional. When a claim has no file behind it, say you could not verify it rather than filling the gap.
