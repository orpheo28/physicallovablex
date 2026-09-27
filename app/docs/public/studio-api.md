# Studio API

JSON everywhere except the PDF export. Base URL: your API host (`http://localhost:8000` in dev).

## Conventions

- **Auth:** when the API is gated, send `X-App-Key: <key>` on every route except `GET /health`. Missing or wrong key → `401`. Ungated (local dev) → header ignored.
- **Errors:** `{"detail": "<message>"}` with `404` (unknown project, stage or factory), `409` (state conflict), `422` (invalid body), `429` (rate limit), `403` (read-only public demo).
- **No 5xx from AI failures.** A stage that cannot run live returns a cached example with `fallback: true`. A failed Studio version is recorded as `failed`; nothing changes.
- **Per-stage cap:** 45 s (`STAGE_TIMEOUT_S`); past it the cached example is served with a `fallback_reason` starting with `timeout`.
- **Rate limits:** per-IP daily caps apply to live runs when a key is set (`429`). Studio start/refine have their own per-IP daily cap. Under `DEMO_READONLY`, `studio/start`, `refine`, `versions/{n}/restore` and `engineering/recompute` return `403`.
- **Labels:** every value is a `LabeledValue` `{value, unit, label, source_or_assumption}` with `label` one of `measured`, `sourced`, `estimate`, `fictional`.

## Health

### `GET /health`
No auth. Returns `{"status":"ok","version":"...","llm_configured":true,"models":{...},"registered_stages":[1,2,...]}`.

## Showcase gallery

### `GET /examples`
No body. Returns `ExampleSummary[]`: `id` (`demo_<slug>`), `name`, `prompt`, `category`, `strategy`, `hero_image_url`, `glb_url`, `one_line_result`, `versions`, `stages_done`, `tags` (`["Example"]`) and `seeded` (true after `POST /demo/reset`). Opening a showcase costs nothing: all stages, Studio versions, AI CAD programs and engineering are cached. Projects carry `tags` (for example `["Example"]`).

## Projects

### `POST /projects`
Body:
```json
{"mode": "idea", "prompt": "A screenless fitness band, 5-day battery", "name": null, "pasted_bom": null}
```
`mode` is `idea` or `prototype` (prototype: describe it and optionally paste a BOM). Optional `example` (`desk_lamp` | `tracker_card`) forces a cached example.

Response `201`: a `Project` (`id`, name, mode, prompt, timestamps).
Errors: `422` invalid body; `429` rate limit.

### `GET /projects`
Array of `Project`, oldest first.

### `GET /projects/{id}`
`ProjectDetail`: the project, 13 stage summaries (`status`: `not_started`, `draft`, `validated`; `fallback`), `autorun` (`state`: `idle` / `running` / `done` / `failed`, `current_stage`, `completed_stages`, `through`, `error`), `has_fallback` and `fallback_stages`.
Poll this every 2 s during an autorun. `404` unknown project.

### `POST /demo/reset`
Wipes the database, re-seeds the cached examples (`demo_desk_lamp`, `demo_tracker_card` and the showcase gallery) and resets the factory network. Intended for demo environments.

## Studio (prompt → product)

### `POST /projects/{id}/studio/start`
No body. Response `202`: `{"version": 1}`. Builds version 1 in the background (brief, first design direction, concept render, CAD from the product family, cost, shortlist; under 35 s in the contract), then the AI-written CAD model in the background (`cad_pending`, patched into version 1 when done), then completes DFM/certifications and the production plan in the background (`background_pending`). Idempotent: a second call returns the current version; a failed v1 is re-run.
Errors: `409` while an autorun runs; `403` on a read-only demo; `429` cap.

### `POST /projects/{id}/refine`
Body: `{"message": "thinner, 8 mm pod"}` (1-1000 characters). Response `202`: `{"version": n}`; version n exists at once with `status: "running"`. Refines of one project run in order.
Errors: `409` before `studio/start` or while an autorun runs; `422` empty message; `403` / `429` as above.

Supported changes: color, material (`pc_abs`, `aluminium`, `stainless_steel`, `tpu`) and finish, dimensions, shape family, features, components (add/remove), target price, markets, free-text requirements, and `regenerate_geometry{instruction}` — a change of form the parameters cannot express ("wider nose", "bigger bin", "add two storage baskets").

`regenerate_geometry`, `set_shape_family` and `set_dimensions` edit the version's AI CAD program (self-repair, then measured); the diff shows `{"area":"shape","label":"AI CAD program","after":"v<k> — <instruction>"}`. Other refines stay fast (no code generation). Without an AI model, a form change is recorded as a requirement and a note says it was not modelled. Product families keep their family on `set_shape_family`; `set_dimensions` scales a family CAD 0.5-2× per axis.

### `GET /projects/{id}/versions`
Array of `Version`, oldest first. Poll every 1-2 s while any version is `running`, `render_pending` or `background_pending` (cheap read).

### `GET /projects/{id}/versions/{n}`
One `Version`. `404` unknown.

### `POST /projects/{id}/versions/{n}/restore`
Response `200`: the `Version` with `is_current: true`. Stage 1-7 artifacts return to version n; steps 8-13 and the Factory Pack are discarded until Make it runs again.
Errors: `404` unknown; `409` if n is not `done`, a refine is running, or an autorun is running.

**`Version` shape:**
```json
{
  "n": 2,
  "message": "Add heart-rate and HRV sensing",
  "status": "done",
  "created_at": "...", "finished_at": "...",
  "summary": "...",
  "changes": [
    {"area": "component", "label": "Component added",
     "before": null,
     "after": "Optical heart-rate sensor (PPG) × 1 — LCSC C6454833, $12.18/unit",
     "label_kind": "sourced"}
  ],
  "preview": {
    "glb_url": "/files/<pid>/v2.glb", "render_url": null,
    "dimensions": {"...": "Measured"},
    "color_hex": "#...", "color_name": "...", "material": "...", "finish": "...",
    "shape_family": "wearable_band",
    "unit_costs": [{"quantity": 2000, "value": 26.55, "label": "estimate", "source_or_assumption": "..."}],
    "top_factories": [{"name": "... (fictional)", "score": 91, "label": "fictional"}],
    "certifications": ["EU ..."], "bom_count": 12,
    "code_url": "/projects/<pid>/cad/code/1", "step_url": "/files/<pid>/model_v1.step",
    "cad_label": "AI-generated CAD (concept level) — geometry measured on the result",
    "cad_source": "llm:<model>"
  },
  "error": null,
  "is_current": true, "render_pending": true, "background_pending": true,
  "cad_pending": false, "cad_note": null
}
```
Values in this example are illustrative. A `failed` version has a plain-language `error` (for example "The AI service is out of credits … Nothing changed — version 1 is still current.") and the previous version stays current.

`cad_pending` is true while the AI CAD model (text-to-CAD) of the version is generated in the background (Studio start) or edited (geometric refine); `cad_note` is a plain-language note (for example the version fell back to the parametric family). `preview.cad_source` is `llm:<model>`, `seed:<family>` or `previous_version`. When an AI model exists, `preview.glb_url` is that model; `shape_family` may be a product family name (board, drone, ...).

`render_url` is `null` while a new concept render is pending; the old look is never shown for the new product.

## Stages

### `POST /projects/{id}/stages/{n}/run`
Runs stage n (1-13). Optional body `{"inputs": {...}}`. Response: `StageResult` (`artifact`, `status`, `fallback`, ...). Stored as `draft`.

| Stage | `inputs` |
|---|---|
| 1 | `{"answers": {"<question id>": "<answer>"}}` |
| 3 | `{"direction_id": "d1"}` |
| 5 | `{"volumes": [500, 2000, 10000], "volume_factor": 0.92, "reference_quantity": 2000}` (all optional) |
| 8 | `{"approve": true, "quote_id": "..."}` |
| 11 | `{"section_122": true}` |
| others | `{}` |

For a Studio project, stages 1-3 with default inputs return the stored artifacts unchanged.

### `GET /projects/{id}/stages/{n}`
`StageResult`. `404` if never run.

### `PUT /projects/{id}/stages/{n}`
Body: `UpdateStageRequest` — user edits (spec edits, chosen direction, approvals); `validate_stage: true` marks it `validated`. `artifact.stage` must equal n.

### `POST /projects/{id}/stages/2/render?direction_id=dN`
On-demand concept render of one design direction. A failed render still returns `200` with `render_url` unchanged. `404` if the project, direction or stage 2 is missing.

## Make it (autorun)

### `POST /projects/{id}/autorun?through=13`
Response `202` immediately (`autorun.state = "running"`). Runs the missing stages, then, with `through=13`: stage 8 (the recommended quote is auto-approved and flagged with assumption `a8_autofill`, label `estimate`: "Auto-approved in autofill mode — review and change the selected factory before any real order"), stages 9-13, and the Factory Pack. `through` accepts `7` (default) or `13`; anything else → `422`.

Poll `GET /projects/{id}` every 2 s. A second POST while running returns the current status. `?wait=true` runs synchronously and returns `200` with all results (for scripts and tests). `409` on a Studio project while a refine is running.

## Factory Pack and export

### `GET /projects/{id}/factory-pack?rebuild=false`
`FactoryPack`, assembled from stages 1-6 (plus engineering when available). Adds `cached_note` and `fallback_stages` when any of stages 1-7 fell back.

### `GET /projects/{id}/export`
`application/pdf` — the Launch Dossier. It carries the same cached-example note when applicable and includes a chapter "Engineering & prototype path".

## CAD files and CAD code

### `GET|HEAD /files/{project_id}/{filename}`
STEP, STL, GLB, PNG referenced by `CadFile.url` and design directions. Version files are immutable: `v<n>.glb`, `v<n>_enclosure.*`. Gated like other routes.

### `GET|HEAD /projects/{id}/cad/code/{k}`
Response `text/x-python`: the build123d program `model_v<k>.py` of the AI-written (or parametric family) model. This is what the app's "CAD code" tab shows. Take the URL from `Version.preview.code_url` or from the `format: "py"` entry of stage 3 `cad_files[]`. Gated by the API key like every other route.

Stage 3 `cad_files[]` lists the AI model first (`glb` and `step` whose description starts "AI-generated CAD (concept level) — geometry measured", and the `py` program), then the product and DFM files (`enclosure.*`). With `CODEGEN_ENABLED=0` or no LLM key there is no AI model: the family's parametric program is recorded as the version's code (`cad_label` says parametric, `cad_source` is `seed:<family>`).

For shell products (vacuum, robot, irrigation controller, drone, hair dryer, camera, phone) stage 3 `overall_dimensions` is the full product, `enclosure.*` stays the moulded housing used for DFM and weight, and a "Full product — all parts, STEP AP214" file is added. Solid products (board, furniture, PV array) export the product itself as `enclosure.*`; stage 4 then uses measured process-fit, stock-size and thinnest-section checks instead of draft/undercut/wall checks.

## Engineering

### `GET /projects/{id}/engineering?refresh=false`
`EngineeringArtifact` (including `build_strategy`), cached by an input digest and recomputed when stages 1-3 change. The first call writes `firmware.zip` (template) and, with an LLM key, starts an LLM firmware version in the background (`firmware.pending_llm: true` → GET again). `404` unknown project.

### `POST /projects/{id}/engineering/recompute`
Force recompute. The server also recomputes after Studio start, each refine, each restore and when an AI model lands. Same response.

### `GET|HEAD /files/{id}/firmware.zip`
The generated firmware project. `404` before the first `GET /engineering`.

See [Engineering](/docs/engineering) for the artifact.

## Factory portal

### `GET /factories`
`Factory[]` — always `label: "fictional"`.

### `POST /factories`
Register a factory (same as MCP `register_capacity`). Body:
```json
{"name": "Tidewater Wearables", "region": "Penang, MY",
 "processes": ["injection_molding", "pcba", "assembly"],
 "materials": ["LSR silicone 50 Shore A", "FR-4"],
 "moq": 500, "certifications": ["ISO 9001", "ISO 13485"],
 "lead_time_days": 28, "monthly_capacity": 60000, "current_load_pct": 35}
```
Response `201`: `Factory`; the name is suffixed "(fictional)". `422` invalid body. Optional `archetype` (`balanced`, `cheap/slow`, `fast/expensive`) and `personality`.

### `GET /factories/{id}`
Capacity profile, audit notes and past performance (`no_data` for self-registered factories). `404` unknown.

### `GET /factories/{id}/rfqs`
`RFQWithQuotes[]` received by that factory, with quote versions.

For agent access to the same network, see [Production MCP](/docs/production-mcp).
