# API contract (v0 — frozen for Wave 1)

Base URL: `http://localhost:8000` (dev sessions: 8107 for W7) (web: `NEXT_PUBLIC_API_URL`). JSON everywhere except the PDF export.
Models: `contracts/artifacts.py` → `contracts/schemas/*.json` → `web/src/types/contracts.ts`.
Errors: `{"detail": str}` (`ErrorResponse`) with 404 (unknown project/stage/factory) or 422 (invalid body).
A stage never returns 5xx because of an LLM/CAD failure: it returns the fixture with `fallback: true`.
Hard cap: every stage handler and the Factory Pack assembly (incl. CN translation) get `STAGE_TIMEOUT_S` (default 45 s);
past it the fixture is served with `fallback_reason` starting with `"timeout"`.
Provider errors (HTTP 401/402 key or credit cap, 403, 429 rate limit) are never retried in another mode and never surface as
an error: the stage serves its fixture (`fallback: true` → "Cached example" banner) and optional layers (renders, CN
translation, certification nuance) are simply skipped.

| Method | Path | Request | Response | Notes |
|---|---|---|---|---|
| GET | `/health` | – | `HealthResponse` | `llm_configured`, models per route, `registered_stages` (stages with a live handler) |
| GET | `/projects` | – | `Project[]` | oldest first |
| POST | `/projects` | `CreateProjectRequest` | `Project` (201) | `example` guessed from the prompt ("lamp" → `desk_lamp`, "tracker"/"wallet" → `tracker_card`) and used for fallbacks |
| GET | `/projects/{id}` | – | `ProjectDetail` | project + 13 `StageSummary` (status `not_started`/`draft`/`validated`, `fallback`) + `autorun: AutorunStatus \| null` (`state` idle/running/done/failed, `current_stage`, `completed_stages`, `started_at`, `finished_at`, `error`) + `has_fallback` (any of stages 1-7 serves a cached example → show "Cached example — AI was unavailable, figures come from a pre-computed example") and `fallback_stages` (1-13) |
| POST | `/projects/{id}/stages/{n}/run` | `RunStageRequest` (optional body) | `StageResult` | n = 1..13. Runs the registered handler; any error → fixture, `fallback: true`. Stored as `draft`. Stage 7 first (re)assembles the Factory Pack |
| POST | `/projects/{id}/stages/2/render` | `?direction_id=dN` | `StageResult` | on-demand AI concept render of one direction (stage 2 auto-renders only the first `LLM_IMAGE_MAX_RENDERS`, default 1 — images are the largest LLM cost). Same 25 s call timeout / 27 s budget; sets `render_url` in the saved stage 2 (+ assumption `a2_render`). A failed render (no image model, 402, timeout) returns 200 with `render_url` unchanged. 404: unknown project / direction, or stage 2 not run |
| GET | `/projects/{id}/stages/{n}` | – | `StageResult` | 404 if never run |
| PUT | `/projects/{id}/stages/{n}` | `UpdateStageRequest` | `StageResult` | user edits (spec edits, chosen design direction, approvals). `validate_stage: true` → status `validated`. `artifact.stage` must equal n |
| POST | `/projects/{id}/autorun` | `?wait=bool` | `AutorunResult` | **202 immediately** (`results: []`, `autorun.state = running`); stage 1 if missing, then 2-7 run in a background thread with defaults (stage 3 gets `direction_id` = chosen or first direction). Poll `GET /projects/{id}` every 2 s: each stage's `StageSummary` turns `draft` as it finishes; `autorun.current_stage` is the stage in progress; `autorun.state` becomes `done`. A second POST while running returns the current status (idempotent). `?wait=true` = synchronous, 200 with all results (scripts/tests) |
| GET | `/projects/{id}/factory-pack` | `?rebuild=bool` | `FactoryPack` | assembled by the `factory_pack` provider (W6) from stages 1-6, else fixture |
| GET | `/projects/{id}/export` | – | `application/pdf` | Launch Dossier. `export_pdf` provider (W6), else W0 stub PDF |
| POST | `/demo/reset` | – | `ResetResult` | wipes the DB, re-seeds every example in `api/fixtures/*/project.json` with all 13 stages `validated` (ids `demo_desk_lamp`, `demo_tracker_card`) |
| GET | `/factories` | – | `Factory[]` | factory portal. `network` provider (W5, MCP-backed), else `api/fixtures/network/factories.json` |
| POST | `/factories` | `RegisterFactoryRequest` | `Factory` (201) | factory onboarding = MCP `register_capacity` (PRD §10): name, region, processes[], materials[], moq, certifications[], lead_time_days, monthly_capacity, current_load_pct (+ optional archetype, personality). Stored in the MCP store; always `label: fictional`, name ends with "(fictional)"; 422 on invalid body |
| GET | `/factories/{id}` | – | `Factory` | capacity profile, audit notes, past performance — all `fictional` |
| GET | `/factories/{id}/rfqs` | – | `RFQWithQuotes[]` | RFQs received by that factory with quote versions |

Plug-in routes (via `register(router)` in owned folders), reserved paths:
- `GET|HEAD /files/{project_id}/{filename}` — W2 (STEP/STL/GLB/PNG referenced by `CadFile.url` and `DesignDirection.glb_url`).
- Anything else must be prefixed by the owner's area (`/cad/...`, `/costs/...`, `/agents/...`, `/mcp/...`, `/export/...`) to avoid collisions.

## `RunStageRequest.inputs` per stage (conventions)
| Stage | inputs |
|---|---|
| 1 | `{"answers": {"<question id>": "<answer>" }}` — re-run with answers; skipped questions stay `skipped: true` |
| 2 | `{}` — answers after ≤ ~12 s; AI renders still running are patched into the saved artifact (`render_url`) within 27 s of the start: re-GET stage 2 to pick them up |
| 3 | `{"direction_id": "d1"}` (default: `DesignArtifact.chosen_direction_id`, else first) |
| 5 | `{"volumes": [500, 2000, 10000], "volume_factor": 0.92, "reference_quantity": 2000}` (all optional) |
| 8 | `{"approve": true, "quote_id": "..."}` → `user_approved`, `final_terms` set |
| 11 | `{"section_122": true}` toggle |
| others | `{}` |

## Labels (UI + PDF)
`measured` → "Measured" · `sourced` → "Sourced" · `estimate` → "Estimate" · `fictional` → "Fictional — demo data".
Every `LabeledValue` renders value + unit + badge, with `source_or_assumption` as tooltip. Network records
(`Factory`, `CapacityProfile`, `RFQ`, `Quote`, `NegotiationTurn`) carry a record-level `label: "fictional"`: badge the whole card.
An artifact with `fallback: true` shows a "Cached example" banner (it may be the desk lamp for another product).

## Additive fields (W7g)
- `ProjectDetail.has_fallback`, `ProjectDetail.fallback_stages` — see `GET /projects/{id}`.
- `FactoryPack.cached_note` (= `contracts.artifacts.CACHED_NOTE` when any of stages 1-7 fell back) + `FactoryPack.fallback_stages`; the Launch
  Dossier cover and footer carry the same note.
- `FinancingArtifact.stage5_total` (budget reference) + `reconciliation_note`: once a stage-8 quote is approved, stage 12 uses its unit
  price, tooling and payment terms; `matches_stage5_total` is then false and the note says "Differs from stage 5 by $X because the
  negotiated quote … replaced the estimate". Show the note instead of "Matches stage 5 total".
- `PastPerformance.no_data` (+ `on_time_rate_pct` / `defect_rate_pct` nullable): self-registered factories → "no data yet".
- `contracts.artifacts.process_label()` / `PROCESS_LABELS`: human wording of process enums (injection_molding → "Injection molding").
