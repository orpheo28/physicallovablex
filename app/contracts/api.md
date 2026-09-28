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
| POST | `/projects/{id}/autorun` | `?wait=bool&through=7\|13` | `AutorunResult` | **202 immediately** (`results: []`, `autorun.state = running`); stage 1 if missing, then 2-7 run in a background thread with defaults (stage 3 gets `direction_id` = chosen or first direction). Poll `GET /projects/{id}` every 2 s: each stage's `StageSummary` turns `draft` as it finishes; `autorun.current_stage` is the stage in progress; `autorun.state` becomes `done`. **`through=13` (autofill)**: after 1-7 it runs stage 8, auto-approves the recommended quote (same path as inputs `{"approve": true, "quote_id": <recommended>}`; the artifact gets assumption `a8_autofill`, label `estimate`: "Auto-approved in autofill mode — review and change the selected factory before any real order"), runs 9-13 and builds the Factory Pack; `current_stage`/`completed_stages` cover 1-13, `autorun.through` = 13 (7 by default). Same 45 s per-stage cap and fallbacks. Other `through` → 422. A second POST while running returns the current status (idempotent). `?wait=true` = synchronous, 200 with all results (scripts/tests) |
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

## Additive fields (W16)
- `AutorunStatus.through` (7 | 13): see `POST /projects/{id}/autorun`. Autofill artifacts carry the stage-8 assumption `a8_autofill` — show it prominently ("review before any real order").

## Studio (W17) — refine the product by prompting
Every prompt updates the real product (CAD, BOM, costs, DFM, certifications, shortlist) as a new **Version**. The stage
artifacts (`GET /projects/{id}/stages/{n}`, n = 1-7) always reflect the **current** version; stages 8-13 and the Factory
Pack are deleted when the current version changes (they described another product) and are rebuilt by "Make it"
(`POST /projects/{id}/autorun?through=13`), which continues from the current version: for a Studio project stages 1-3
return the stored artifacts unchanged when run with default inputs (explicit inputs — stage 1 `answers`, stage 3 another
`direction_id` — still run the normal handler); stages 4-13 re-run on that product.

| Method | Path | Request | Response | Notes |
|---|---|---|---|---|
| POST | `/projects/{id}/studio/start` | – | `StudioAccepted` `{"version": 1}` (**202**) | Background job: stage 1 if missing, stage 2 with only `d1` built now (wearables → family `wearable_band` / `ring`; `d2`/`d3` built lazily, `glb_url: null` until then), concept render of d1 (async, patched in), stage 3, stage 5, stage 7 → **version 1**; then stage 4 (+ stage 5 re-costed with its certifications), stage 6 and stage 7 in the background (`background_pending`). Idempotent: a second call returns the current version (a failed v1 is re-run). 409 while an autorun runs |
| POST | `/projects/{id}/refine` | `RefineRequest` `{"message": str}` (1-1000 chars) | `StudioAccepted` `{"version": n}` (**202**) | Version n is created `running` at once. Jobs of one project run in order (FIFO). 409 before `studio/start` or while an autorun runs; 422 empty message |
| GET | `/projects/{id}/versions` | – | `Version[]` (oldest first) | poll every 1-2 s while a version is `running` / `render_pending` / `background_pending` (cheap read, no lock) |
| GET | `/projects/{id}/versions/{n}` | – | `Version` | 404 unknown |
| POST | `/projects/{id}/versions/{n}/restore` | – | `Version` (200, `is_current: true`) | the stage 1-7 artifacts return to version n (its files are immutable: `v<n>.glb`, `v<n>_enclosure.*`). 404 unknown; 409 if n is not `done`, a refine is running, or an autorun runs |

**Refine job.** (1) ONE LLM call (route `main`, `complete_json`, schema `RefinePatch`) turns message + current product
state into typed ops: `set_color{hex,name}`, `set_material{material ∈ pc_abs|aluminium|stainless_steel|tpu, finish}`,
`set_dimensions{length,width,height mm}`, `set_shape_family{rounded_box|puck|slab|wearable_band|ring}`,
`add_feature{name,description}`, `add_component{part,category,qty,rationale,manufacturer_pn?}`,
`remove_component{bom_item_id}`, `set_target_price{value,currency}`, `set_markets{markets}`, `note_requirement{text}`
(anything not physically modelled → `brief.constraints`). The model never invents a measurement (dimensions only from
numbers the founder gave). (2) Code applies it deterministically: every value re-checked and clamped (per-family ranges —
a clamp becomes a `Note` change; invalid hex refused), brief, chosen direction, CAD rebuilt (build123d, cached by params
hash) into version files, spec (bbox **Measured** from the STEP, weight Estimate, parts), BOM (added electronic parts
matched to the LCSC snapshot → Sourced; a known capability without its part — heart rate/HRV/SpO2, accelerometer, skin
temperature, haptics — gets it added), DFM (measured checks re-run on the new STEP; certifications re-mapped by rule +
wearable rows; component risks; the AI review re-runs in the background), costs (stage 5 code), shortlist (stage 7 code;
stage 6 re-planned in the background when material / shape changed). One commit for stages 1-7. (3) A new concept render
only if colour / material / shape / dimensions changed (`render_pending`, then `preview.render_url = /files/<pid>/v<n>.png`;
`render_url` is `null` meanwhile — the old look is never shown for the new product).

**Failures.** LLM error / 402 / timeout / CAD failure → the version is `failed` with a plain-language `error`
("The AI service is out of credits (HTTP 402)… Nothing changed — version 3 is still current."); nothing is written, the
previous version stays current. Never a 5xx.

**`Version`** `{n, message, status: running|done|failed, created_at, finished_at, summary, changes: VersionChange[],
preview: VersionPreview|null, error, is_current, render_pending, background_pending}`
- `VersionChange {area: color|material|shape|dimensions|feature|component|price|markets|requirement|certification|cost,
  label, before, after, label_kind: measured|sourced|estimate|fictional}` — e.g. `{"area":"dimensions","label":"Pod
  thickness","before":"10.0 mm","after":"8.0 mm","label_kind":"measured"}`, `{"area":"component","label":"Component
  added","after":"Optical heart-rate sensor (PPG) × 1 — LCSC C6454833, $12.18/unit","label_kind":"sourced"}`.
- `VersionPreview {glb_url, render_url, dimensions: Dimensions (Measured), color_hex, color_name, material, finish,
  shape_family, unit_costs: [{quantity, value, label, source_or_assumption}], top_factories: [{name, score, label:
  "fictional"}], certifications: ["<market> <standard>" of required ones], bom_count}`.

**Shape families** (`cad_parameters.family`): 0 rounded box · 1 puck · 2 slab · **3 wearable_band** (pod length × width ×
thickness incl. a 0.8 mm optical sensor window; `strap_width`, `strap_length`; strap = LSR spec part + BOM line, drawn in
the full-product GLB, excluded from the measured bbox) · **4 ring** (length = width = outer diameter, height = band width,
wall = band thickness; drafted annular halves + inner sensor bump). Wearable certification rows (skin-contact ISO 10993,
EU nickel release, IEC 62471 for optical sensing, FDA general-wellness review) are added to stage 4 for Studio projects.
Public-link guards: `DEMO_READONLY` → 403 on start/refine; per-IP cap `STUDIO_RATE_LIMIT_PER_DAY` (default 100, only with a key).

## Engineering (W20)
Concept-level engineering computed from the current project state (stage 1 brief, stage 2 chosen direction → shape family,
stage 3 measured CAD bbox + STEP solid volume + weight + BOM). Every number is a `LabeledValue`; every check has a formula and a
`verdict` (`pass` / `warn` / `fail` / `info`) against a stated threshold.

| Method | Path | Request | Response | Notes |
|---|---|---|---|---|
| GET | `/projects/{id}/engineering` | `?refresh=bool` | `EngineeringArtifact` | cached by `inputs_digest` (recomputed when stages 1-3 change); 404 unknown project. First call writes `firmware.zip` (template) and, with an LLM key, starts an LLM version in the background (`firmware.pending_llm: true` → re-GET) |
| POST | `/projects/{id}/engineering/recompute` | – | `EngineeringArtifact` | force recompute = `api.engineering.recompute_engineering(project_id)` (call after each Studio refine) |
| GET/HEAD | `/files/{id}/firmware.zip` | – | `application/zip` | generated firmware project, README first line "Generated code — not compiled or tested"; 404 before the first GET of `/engineering` |

`EngineeringArtifact`: `category` (pack key: wearable, furniture_baby, home_robot, vacuum, irrigation, solar_roof, surfboard, lighting,
tracker, generic) + `category_title`; `partner_word` = `factories` | `installers` (+ `site_install`); `standards[]` (`StandardRef`:
`citation_label` sourced = URL checked to load, date in `citation_note`; estimate = "Standard to be confirmed"); `risks[]`; `tests[]`
(drop / ingress / salt_spray / tip_over / thermal …); `checks[]` (`EngineeringCheck`: `value`, `threshold`, `verdict`, `formula`,
`inputs[]`, `notes[]` — e.g. the sealing checklist of the IP check); `electronics` (`power_tree[]`, `connections[]` netlist-level,
`power_budget[]`, `average_current`, `battery_life`, `pcb_note` "PCB layout: next step (human or text-to-PCB)") or null;
`firmware` (`framework` zephyr | arduino, `url`, `files[]`, `generated_by` template | llm:<model>, `note`) or null;
`prototype` (`enclosure_volume` Measured, `cost_lines[]`, `devkit_bom[]` LCSC-matched lines Sourced, `assembly_steps[]`,
`timeline_weeks`, `total_cost`); `solar` (site install: PVGIS yield Sourced "PVGIS (EU JRC), fetched <date>", module count / kWp /
annual kWh / payback Estimates) and `installers[]` (Fictional — demo data). `fallback: true` when stage 3 is missing or cached.

Additive fields: `FactoryPack.engineering: EngineeringArtifact | null` (section 10 "Engineering & prototype path"); the Launch
Dossier has a chapter "Engineering & prototype path" after the 13 stages. Stage 7: a rooftop-solar project (category `solar_roof`)
is matched with the 3 fictional certified installers (`factory_mcp/data/factories.json`, ids `i_*`, process `other`) instead of factories.

## Production MCP (HTTP) (W22)
The 7 PRD §10 tools (`register_capacity`, `search_capacity`, `get_factory_profile`, `request_quote`, `submit_quote`,
`counter_offer`, `accept_quote`) served over MCP Streamable HTTP, in the API process, on the same store as the factory portal
(`factory_mcp/http.py`, mounted by `api/mcp_http/`). Not a REST route: the body is JSON-RPC 2.0.

| Method | Path | Notes |
|---|---|---|
| POST | `/mcp` (also `/mcp/`) | MCP JSON-RPC (`initialize`, `tools/list`, `tools/call`). Stateless, JSON responses (`Accept: application/json, text/event-stream`) |

- **Auth**: `Authorization: Bearer <token>` or `X-App-Key: <token>`, where token = `MCP_TOKEN`, else `API_SHARED_KEY`; both unset → open
  (local dev). Read per request. Missing/wrong → 401 + `WWW-Authenticate: Bearer`. `/mcp` is exempt from the global `X-App-Key`
  guard (`api/auth.py`), which would otherwise demand the API key; `DEMO_READONLY` does not apply to it.
- A factory registered over MCP is immediately in `GET /factories` and in `search_capacity`; an RFQ from `request_quote` is in
  `GET /factories/{id}/rfqs`. All data is Fictional — demo data.
- Standalone (no API): `uv run python -m factory_mcp.http --port 8123`. Demo agents: `python -m factory_mcp.demo.buyer_agent | factory_agent`
  (`--url`, `--token`). Guide: `docs/MCP_DEMO.md`.

## W21 — product families, AI CAD in the Studio, build strategy, showcase gallery (additive)

**Product families in stages 2-4.** When the brief maps to a parametric family (`api.cad.codegen.classify` → `seed_for`:
board, furniture, stick_vacuum, home_robot, irrigation, solar_array, drone, hair_dryer, camera, smartphone), stage 2's three
directions are that family (three parameter sets, < 1 s each, `generated_by: "code"`, dimensions **Measured** on the family CAD;
sizes stated in the prompt are applied, e.g. a 7'6" board = 2286 mm, a 35 m² roof → module count). `DesignDirection.cad_parameters`
then also carries `product_family` (code 10-19), the family parameters prefixed `fp_` and, after a Studio dimension edit,
`fp_scale_x|y|z`. Stage 3: `overall_dimensions` = the full product; shell products (vacuum, robot, irrigation controller, drone,
hair dryer, camera, phone) keep the two-shell `enclosure.*` as their main moulded housing (DFM, weight) plus a "Full product — all
parts, STEP AP214" file; solid products (board, furniture, PV array) export the product itself as `enclosure.*`, weight = measured
solid volume × per-part densities, parts grouped by role, and stage 4 replaces draft / undercut / wall / tonnage with measured
process-fit, stock-size and thinnest-section checks (a surfboard never gets wall-thickness DFM). Wearables keep W17's families.

**Studio (additive).**
- `Version.cad_pending` — the AI CAD model (text-to-CAD, `api/cad/codegen`) of this version is being generated in the
  background (Studio start) or edited (geometric refine). `Version.cad_note` — plain-language note (e.g. fell back to the family).
- `VersionPreview.code_url` (`/projects/{id}/cad/code/{k}` — the build123d program), `step_url`, `cad_label`
  ("AI-generated CAD (concept level) — geometry measured on the result" or "Parametric family CAD (concept level) — …"),
  `cad_source` (`llm:<model>` | `seed:<family>` | `previous_version`). When an AI model exists, `preview.glb_url` is it
  (`model_v<k>.glb`, or a recoloured copy `v<n>_ai.glb` after a colour / material change); `shape_family` may now be a product
  family name (board, drone …).
- Stage 3 `cad_files`: the AI model first (`glb` + `step` with description starting "AI-generated CAD (concept level) —
  geometry measured", and `format: "py"` = its program), then the product / DFM files (`enclosure.*` stays for DFM).
- Studio start: v1 from the family (< 35 s), then the AI model in the background, patched into v1 (and later versions that
  did not change geometry) when done. `CODEGEN_ENABLED=0` (or no key) → no AI CAD: the family's parametric program is recorded
  as the version's code (`cad_label` = parametric, `cad_source` = `seed:<family>`).
- New refine op `regenerate_geometry{instruction}` (a change of form the parameters cannot express: "wider nose", "bigger bin",
  "add two storage baskets"). `regenerate_geometry`, `set_shape_family` and `set_dimensions` edit the version's AI program
  (`refine_cad`, Cursor-style, self-repair, measured) — change `{"area": "shape", "label": "AI CAD program", "after": "v<k> — <instruction>"}`.
  Other refines stay fast (no codegen). Without an AI model the form change is recorded as a requirement and a note says it
  was not modelled. Product families keep their family on `set_shape_family`; `set_dimensions` scales the family CAD (0.5-2× per axis).
- `recompute_engineering` runs after Studio start, each refine commit, each restore and when an AI model lands.

**Engineering (additive).** `EngineeringArtifact.build_strategy: BuildStrategy | null` — `strategy` `full_design` (furniture,
board, lamp, tracker, generic) | `module_assembly` (drone, irrigation, wearable, hair dryer, vacuum, rooftop solar) |
`odm_customization` (smartphone, camera, home robot); `title`, `explanation`, `customisable[]`, `not_customisable[]`, `moq`,
`entry_cost`, `lead_time` (LabeledValue, **Estimate** with the assumption), `path[]` (ODM: find an ODM with a close reference
platform → customise enclosure / colours / display / sensors / software → certifications carried over or redone),
`certifications_note`, `assumptions[]`. Shown in the Factory Pack (section 10 summary) and the Launch Dossier ("Build strategy").
New categories: `drone` (checks `thrust_to_weight`, `hover_time` — momentum theory from battery Wh and hover power —,
`drone_class`: EU C0 < 250 g / C1 < 900 g / C2 < 4 kg, **Sourced** from Regulation (EU) 2019/945), `hair_dryer` (IEC 60335-2-23;
`dryer_power`, `dryer_airflow`, `outlet_temperature` = P / (ρ Q c_p)), `camera` and `smartphone` (ODM; radio certifications
47 CFR Parts 2/15/22/24/27, RED, PTCRB/GCF). `EngineeringCheck.domain` adds `flight`, `regulatory`.

**Factories (additive).** `CapacityProfile.categories` (specialities; empty = generalist) and `SearchCapacityQuery.category`
(stage 7 passes the engineering category): a specialist of another category scores 50% on process fit ("specialises in
lighting, not wearable"). Three new fictional factories: Tidewater Wearables EMS, Lumen Peak Micro-Electronics (wearables /
small electronics) and Skyforge Robotics Integrators (drones / robots). LCSC matching: a line that names a sensing kind (PPG,
IMU, gas, image sensor…) only matches a part of that kind; unmatched stays **Estimate**.

| Method | Path | Request | Response | Notes |
|---|---|---|---|---|
| GET | `/examples` | – | `ExampleSummary[]` | showcase gallery: `id` (demo_<slug>), `name`, `prompt`, `category`, `strategy`, `hero_image_url`, `glb_url`, `one_line_result`, `versions`, `stages_done`, `tags` (["Example"]), `seeded` (true after `POST /demo/reset`). Opening a showcase costs nothing: all stages, Studio versions, AI CAD programs and engineering are cached |
| GET/HEAD | `/projects/{id}/cad/code/{k}` | – | `text/x-python` | AI-written (or family) build123d program `model_v<k>.py` |

`Project.tags` (e.g. `["Example"]`). `/demo/reset` also seeds `api/fixtures/showcase_<slug>/` (Studio versions + engineering cache);
their files resolve from `api/cad/prebuilt/showcase_<slug>/`. Guards (api/auth.py): `studio/start`, `refine`, `versions/{n}/restore`
and `engineering/recompute` → 403 under `DEMO_READONLY`, per-IP `STUDIO_RATE_LIMIT_PER_DAY` (a start on an already-started project
is not counted); `cad/code` is behind `API_SHARED_KEY` like every route.

## W21b (additive)
- Refine op `upgrade_battery{capacity_mah?, factor?}` (default 1.5×; also the backstop for a noted "longer flight time /
  battery life / runtime"): the BOM battery line gets the new capacity (or a pack line is added), price scales (Estimate),
  added mass is stated. Changes: `{"area": "component", "label": "Battery capacity", "after": "3680 mAh at 14.8 V (54.5 Wh), +101 g"}`
  and `{"area": "performance", "label": "Flight time" | "Battery life", "before", "after"}` recomputed by the engineering layer.
  `VersionChange.area` adds `performance`.
- `VersionChange.risk: ComponentRiskSummary | null` on "Component added" and `ComponentRiskItem.alternative: PartAlternative | null`:
  `{level, reasons[], alternative: {part, lcsc_pn, price (Sourced), stock, label}}` — a cheaper in-stock same-kind LCSC part when
  the line is expensive (≥ $3 at 2k) or low-stock; `null` + a reason when the snapshot has none (e.g. MAX30102).
- `Factory.kind`: `factory | installer | integrator` (all seeds set; older stored records inferred). New seed: Coralline Silicone
  Works (fictional), LSR / silicone overmolding + PCBA (the MCP buyer demo lands on it). W21's "Tidewater Wearables EMS" is
  renamed Harborlight Wearables EMS (the MCP demo registers "Tidewater Wearables" itself). 15 partners after `/demo/reset`.
- `Project.name` becomes the brief's `product_name` after stage 1 / Studio start when the project was auto-named (prompt).
- `EngineeringArtifact.unit_basis` (`per_unit` | `per_installation`) + `installation_cost`; `ExampleSummary.unit_basis` +
  `unit_cost` (per installation for rooftop solar, e.g. 10,621 EUR turnkey).
- `/mcp` is natively exempt in `api/auth.py` (`MCP_PATHS`): the endpoint checks its own `MCP_TOKEN`.

## W21c (additive; one relaxation)
- Refine components are capability-aware: a part is never added for a capability the BOM already provides (PPG covers heart
  rate / HRV / SpO2 — a PPG without red + IR is upgraded in place to MAX30102, change "Component upgraded"); a feature adds
  every part it implies ("SpO2 and skin temperature" → the missing temperature sensor only, HDC3020 Sourced). SpO2 /
  body-temperature on a worn product adds the required row "US FDA general-wellness vs medical-device boundary (SpO2 /
  body-temperature claims)" → a visible `certification` change.
- LCSC matching never maps complex modules (mainboard, display, camera / compute module, gimbal, flight controller, ESC,
  BLDC / gear motors, LiDAR, pump, valve, heater, flex / "assembly" lines, grouped passives, PV kit) to a catalogue chip,
  rejects implausible class matches (a $0.01 tactile switch as a trigger / TRIAC switch) and one generic chip standing in
  for different lines. Those lines are priced by the module price model (`api/costs/modules.py`, Estimate with the assumption).
- An assumed (not founder-given) retail below 1.6 × landed cost is replaced by ex-works × category multiplier (3.0; 2.4 for
  furniture / boards), assumption stated.
- `CostsArtifact.unit_basis` (`per_unit` | `per_installation`); `CostsArtifact.tiers` min length relaxed 3 → 1. Site installs
  (rooftop solar): one tier = a pilot of 10 installations with per-installation figures, `target_retail_price` = turnkey installed
  price, margin vs installed price, cash for the pilot; stage 11 = DDP local delivery, no import. One currency per project: USD
  (engineering solar figures converted at 1.08 USD/EUR, stated).
- `Version.cad_attempts`, `Version.cad_repairs` ("self-repaired N×").

## W27 — product photos (reference-based AI photography + listing kit, additive)

Photos are AI images **styled from a reference image of OUR CAD**: the prompt directs only light, surface, lens and
framing and ends with "Preserve the exact geometry, proportions, colours, materials and details of the referenced
product. No added text, logos, watermarks or extra objects unless stated." Reference, in order: (a) a PNG/JPEG the
client captured from the 3D viewer (sent with the request, saved as `/files/<pid>/ref_v<n>.png` and reused by later
shots of that version); (b) the Blender render of the CAD (`hero_v<n>.png`, or `hero_<dN>.png` of the chosen direction
for version 1); (c) none → text-only prompt (product described from the design direction). Doc: docs/PHOTOGRAPHY.md.

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| POST | `/projects/{id}/versions/{n}/photo?shot=hero_studio` | optional image (below) | `PhotoAccepted {version, shots}` (**202**) | one shot, background job; `shot` ∈ `hero_studio` (4:5) · `packshot_white` (1:1) · `lifestyle` (4:5) · `in_hand_scale` (4:5) · `detail_macro` (1:1) |
| POST | `/projects/{id}/photos/kit?version=n&detail=true` | optional image | `PhotoAccepted` (**202**) | listing kit: `packshot_white`, `lifestyle`, `in_hand_scale` (+ `detail_macro` unless `detail=false`) of `version` (default current); when done the kit is attached to stage 13 `BrandArtifact.listing_photos` and printed on a "Listing photos" page of the Launch Dossier |
| GET | `/projects/{id}/photos` | – | `ProjectPhotos {project_id, version, photos: ProductPhoto[], job: PhotoJob, configured}` | poll every ~2 s while `job.state == "running"`; `photos` = current version, newest per shot (source of truth) |

Image body (optional; ≤ 2 MB; PNG or JPEG checked by magic bytes and decoding; 64-4096 px a side), any of:
`multipart/form-data` field `image` · `application/json {"image_base64": "<base64 or data: URL>"}` · raw `image/png` |
`image/jpeg`. Errors: 413 (> 2 MB), 415 (not PNG/JPEG / undecodable / other content type), 422 (unknown shot, too
small / large, bad base64), 404 (project / version), 409 (a photo job of this project is running), 403
(`DEMO_READONLY`), 429 (per-IP `PHOTO_RATE_LIMIT_PER_DAY`, default 30 jobs, 0 disables), 503 (no image model).

- `ProductPhoto {shot, url (/files/<pid>/photo_v<n>_<shot>.png), label, reference: viewer|cad_render|none, aspect_ratio,
  staged, model, version, created_at}`. `label` (show it under the image, always):
  "Photo-styled from the CAD (AI image, geometry from our CAD)" with a reference, "AI concept image (no CAD reference)"
  without; lifestyle / in-hand add " · Staged scene — illustrative" (`staged: true`).
- `PhotoJob {state: idle|running|done|failed, version, shots, done, failed, error, started_at, finished_at}`. A failed
  shot (timeout, 402 credits, no image) keeps the previous file and entry; `error` is a calm plain-language sentence.
- `VersionPreview.photos: ProductPhoto[]` (additive). A `hero_studio` photo also becomes `VersionPreview.render_url`
  (and the chosen direction's `render_url` in the version snapshot) — `a2_render` semantics unchanged otherwise.
- `BrandArtifact.listing_photos: ProductPhoto[]` (additive, default []).
- `ExampleSummary.hero_image_label` + `ExampleSummary.photos` (hero_studio + lifestyle; additive). Showcase cards'
  `hero_image_url` is the hero_studio photo styled from the Blender render of the current version's CAD.
- Model: env `LLM_IMAGE_MODEL` (live); the showcase recorder uses `LLM_IMAGE_MODEL_SHOWCASE` when set.

## W21d
- Studio preview refreshes (background DFM / plan / render results) keep `preview.photos` (W27 photos are not in the snapshot).
- Photo routes (`POST /projects/{id}/versions/{n}/photo`, `POST /projects/{id}/photos/kit`) are guarded in `api/auth.py`
  (`PHOTO_RUN`): 403 under `DEMO_READONLY`, per-IP `PHOTO_RATE_LIMIT_PER_DAY` (default 30, own bucket, only with a key); the
  route keeps only the 503 "no image model" check.
- The live Studio concept render of version n sends the stored viewer capture `ref_v<n>.png` as the image reference when present.
- Site installs: `breakeven_units` is counted in `installations` (unit) against the pilot's fixed-cost base (installer
  qualification + insurance, tools / van share, sales), which the pilot cash plan now includes.

## W21e
- `VersionPreview.unit_basis`, `installed_price`, `installer_cost` (per_installation only): one source of truth per version —
  `installed_price` = stage 5 `target_retail_price` = engineering `installation_cost` = gallery card `unit_cost` (PV turnkey +
  battery system when the BOM has one); `installer_cost` = stage 5 tier `unit_cost` ("not the customer price").
- "Component added" changes carry the price stage 5 uses (`$3,400.00/installation` for the solar battery), not a stale BOM placeholder.
- `Version.look_changed`: false when colour / material / finish / shape / dimensions did not change → the previous version's photos
  are copied to the new version (same labels / references, no image call); `POST /versions/{n}/photo` then returns 202 with the
  carried photo (add `?force=true` to re-shoot anyway).
- `whoop_kitesurf` showcase: the 4-shot listing kit (packshot_white, lifestyle, in_hand_scale, detail_macro, Blender CAD reference)
  in stage 13 and the Dossier.

## 3D parts & anatomy (W29, additive)

**GLB conventions** (every version GLB `/files/<pid>/v<n>.glb` / `model_v<k>.glb` / `v<n>_ai.glb`, and the anatomy GLB):
metres, **+Y up** (glTF default), one node per part named `"<part_id>"`; node `extras` = `PartMeta`. Smooth vertex normals
with a ~30° crease angle (hard edges stay sharp). PBR materials per role; `KHR_materials_clearcoat` (gloss plastics, painted
metal), `KHR_materials_sheen` (LSR silicone, fabric straps), `KHR_materials_transmission` + `KHR_materials_ior` (diffusers,
lenses, windows), `KHR_materials_specular` where useful; metals metallic 1, roughness by finish (anodised 0.35, brushed 0.25,
polished 0.1); soft-touch plastics roughness 0.75. Colours from the version's look. Each GLB < 3 MB.

**`PartMeta`** `{part_id, name, role (shell_top|shell_bottom|strap|button|window|lens|diffuser|frame|arm|prop|motor|pcb|component|
battery|antenna|connector|cable|fastener|other), layer_id, material, finish, colour_hex, measured_bbox_mm [x,y,z], centroid_mm
[x,y,z], label ("measured"|"estimate"), bom_item_id?, lcsc_pn?, package?, unit_price? (LabeledValue), editable: [{param, label,
min, max, step, unit, value}], colour_editable: bool, material_options: [str]}` (mm and GLB axes: x, y = up, z).

| Method | Path | Request | Response | Notes |
|---|---|---|---|---|
| GET | `/projects/{id}/parts` | `?version=n` (default current) | `ProjectParts {version, glb_url, parts: PartMeta[]}` | `glb_url` = the version's `preview.glb_url`; exterior parts only (measured on our CAD) |
| POST | `/projects/{id}/parts/{part_id}/edit` | `PartEditRequest {colour_hex?, material?, finish?, param?, value?}` | `StudioAccepted {version}` (**202**) | deterministic refine, **no LLM**; the new version appears in `GET /projects/{id}/versions` like any refine |
| GET | `/projects/{id}/anatomy` | `?version=n` | `ProjectAnatomy` | built on first request, cached per version |

**Edit semantics.** Applies to the current version (new version n+1, FIFO with Studio jobs). colour / material / finish → a look
change only (recoloured GLB; photos follow `look_changed`; costs unchanged unless the material price differs — Estimate from the
cost price tables). `param` (one of `PartMeta.editable[].param`, `value` within `[min, max]`) → CAD rebuilt (family parameter,
or the AI CAD program's named parameter literal re-run in the sandbox), measured, BOM / costs / DFM / engineering recomputed like
a normal refine. `Version.summary` / `changes`: "Strap colour → Sage (#9DB09A)", "Pod thickness 10.0 → 9.0 mm (Measured)", "Shell
material PC/ABS → Anodised aluminium (+$3.20/unit, Estimate)". Version `message` = the same summary.

**`ProjectAnatomy`** `{version, glb_url, label: "Illustrative internal layout — not a routed PCB", kind: electronics|construction,
bbox_mm, layers: [{id, name, order, parts: [part_id], explode_vector: [x,y,z] (unit), explode_distance_mm, caption}], steps:
[{id, title, kicker, caption, camera: {position_mm, target_mm, fov_deg}, layers_exploded: [layer_id], focus_parts: [part_id]}],
parts: PartMeta[]}`.
- **Companion GLB**: `glb_url` = `/files/<pid>/anatomy_v<n>.glb` — the exterior parts (same `part_id`s as `/parts`) plus the
  internal bodies (PCB, components with their package dimensions, battery, motors, cables…), each a named node with `PartMeta`
  extras (`label: "estimate"` for internals). The version GLB is never modified by anatomy.
- Layer offsets: the viewer moves every node of a layer by `explode_vector × explode_distance_mm` (mm → m) when exploded;
  `steps[k].layers_exploded` = the layers exploded at that step. Camera `position_mm` / `target_mm` are in mm in the GLB's own frame
  (the frame of `centroid_mm`: the CAD origin, product standing on y = 0 — not re-centred), placed from the product bbox.
- `kind: construction` for solid products (board, furniture): layers are construction layers (foam core, stringer, glass…).

**As implemented (W29 notes).**
- Node tree: scene root `product` (identity; extras `{pipeline: "w29-glb-1", units: "m", up: "+Y", overrides, part_params}`) →
  part nodes (name = `part_id`, `translation` = part bbox centre in metres, extras = PartMeta) → one or more **mesh children**
  named `<material role>.<n>` (the build123d label: body, accent, glass, fabric…). Move / hide the part node, never the mesh.
  Geometry is baked in world space (no rotation on any node), so exploding = adding `explode_vector × explode_distance_mm / 1000`
  to the part node's translation.
- Parts that one program loop draws (10 cyclone cones, feet) are one part with several mesh children; props / motors / arms stay
  one part each. Part names come from the program (variable / comment at the label call site), else the material role.
- `version`: omitted = current Studio version. A project without Studio versions (e.g. `demo_desk_lamp`, `demo_tracker_card`)
  answers `version: 0` = the chosen direction's model (edits need a Studio version → 409).
- `editable[]`: at most 4 per part, the program `P[...]` keys the part depends on (data flow), ranges = the family clamp ∩
  [0.5×, 2×] of the current value; an AI-program key that is also a family / enclosure parameter (e.g. `pod_thickness` →
  pod height, `bin_diameter`) drives both (DFM, weight, costs follow); otherwise only the AI model changes (a note says so).
- `material_options`: shells `pc_abs | aluminium | stainless_steel | tpu`; straps `lsr_silicone | fabric | tpu`; windows
  `glass | clear_pc`; others none. Body-colour parts edit the product colour / material (same path as a prompt); other parts get a
  per-part override stored in the version GLB (`v<n>_ai.glb` or `v<n>.glb`), kept by later recolours.
- `ProjectAnatomy.kind` (`electronics` | `construction`) and `ProjectAnatomy.parts` (PartMeta of every node of the anatomy GLB;
  internal bodies `label: "estimate"`, `package` = the LCSC package string or the sizing rule's package) are additive fields.
  A construction anatomy may show a hull as its laminates (the board's hull part id keeps the deck laminate).
- Showcases ship precomputed `anatomy_v<n>.{glb,json}` for every version; other projects build on first GET (< 1.5 s).

**Errors** (all routes): 404 unknown project / version / part · 409 a Studio job (refine / edit) or autorun is running
(edit only) or the project has no Studio version · 422 invalid value (out of range, unknown param / material, bad hex, empty body)
· 403 `DEMO_READONLY` (edit) · 429 rate limit (edit; shares the `STUDIO_RATE_LIMIT_PER_DAY` bucket).

## W29b (additive)
- `VersionPreview.photo_stale` — a look-changing part edit starts its version with no photos and `render_url: null`;
  `photo_stale: true` until a `hero_studio` photo of that version is attached (the UI says "photo shows an older look /
  not generated yet"). The auto `hero_studio` job starts server-side when a reference of that version is stored
  (`ref_v<n>.png` / `hero_v<n>.png`) and an image model is configured; otherwise the Studio's viewer-capture POST applies.
- Colour / material / finish part edits keep stage 6 and the stage-7 shortlist unchanged.
- Engineering: electronic BOM lines are classified by their part name first (a battery pack whose description mentions
  the motor is a battery); category "typical" lines never duplicate a kind the BOM has; an `nS … 4.2·n V` pack runs at
  3.6·n V nominal; the vacuum motor class (180 W) is electrical input power. Runtime = pack mAh × 85 % / I at pack voltage.
- Anatomy closing step states the whole-product mass (all parts: exterior surface × wall × density + internals, Estimate).


## Assembly (C2, additive — on by default since pass-7; set `CAD_ASSEMBLY=0` to disable)
A version's parts connected by **build123d Joints** (RigidJoint / RevoluteJoint / LinearJoint), with **measured** assembly
checks. On by default since pass-7 (set `CAD_ASSEMBLY=0` to disable: the route answers 404 and nothing else changes,
engineering digests included). When on,
`GET /projects/{id}/parts` then also carries `parent_part_id` / `joint` / `explode_vector` / `explode_distance_mm`, stage-5 costs
add the measured fastener lines (`fx…`) for joints the modelled hardware (`hw…`, C1 standard parts — on by default since
pass-7; set `CAD_DETAIL_LEVEL=basic` to disable) does not hold, and a lump
'fastener set / screws' BOM line is replaced by the counted lines (never both).

| Method | Path | Request | Response | Notes |
|---|---|---|---|---|
| GET | `/projects/{id}/assembly` | `?version=n` (default current), `?refresh=true` | `ProjectAssembly` | built on first request (≈ 0.5-2 s), cached per version in `FILES_DIR/<pid>/assembly_v<n>.json` |

**`ProjectAssembly`** `{project_id, version, label, source (/files/<pid>/<model>.step), root (part_id), nodes: AssemblyNode[],
joints: AssemblyJoint[], interferences: AssemblyInterference[], clearances: AssemblyClearance[], fasteners: BOMItem[],
checks: EngineeringCheck[] (domain "assembly"), summary, engine}`. All coordinates in **mm, GLB axes (+Y up)** like `PartMeta`.
- `AssemblyNode {part_id (= PartMeta.part_id), name, role, parent, joint_id, rigid_body, volume (Measured mm³), explode_vector
  (unit), explode_distance_mm}` — one node per part of `/parts`; exactly one root; `explode_*` derived from the joint axis
  (revolute / linear: along the axis, away from the parent; rigid: the principal axis the child sits on), cumulative down the tree.
- `AssemblyJoint {id, parent, child, kind: rigid|revolute|linear, method: screwed|snap_fit|inlay|press_fit|bonded|clip|hinge|
  bearing|slide|latch, dof, origin_mm, axis, range (deg / mm), fasteners: FastenerUse[], rule}` — `rule` says which family /
  role rule inferred the mate (prop → motor revolute; motor → arm 4 screws; folding arm → hinge (DOF locked in use, `dof: 0`);
  two shells meeting at a parting line → screws into heat-set inserts (≥ 60 mm) or snap-fit; windows / lenses / lights → inlay;
  strap → 2 spring bars; wheels / rollers → revolute about their symmetry axis; buttons / triggers → linear 0.5 mm travel;
  lids → hinge on the rear edge).
- `FastenerUse {kind: screw|insert|spring_bar|pin|nut|washer, standard, designation, size, length_mm, qty, source}` — `source`
  = `api.cad.stdparts` (C1 catalogue) when importable, else `built-in table`.
- `AssemblyInterference {a, b, volume (Measured mm³, OCCT boolean common, tolerance 0.01 mm³), kind, note}`:
  `interference` (parts in different rigid bodies, over each moving joint's motion study, or the two shells of a parting line
  overlapping → **fail**), `joint_seat` (overlap between the two parts of one joint, or a button / wheel pocket through its
  host's rigid body), `static_overlap` (parts of one rigid body interpenetrate — concept geometry, pocket at detail design).
- `AssemblyClearance {part_id, against, min_clearance (Measured, BRepExtrema), motion, verdict, rule}` — props ≥ 2 mm over 12
  poses / 360°, rolling parts ≥ 1 mm, buttons pressed 0.5 mm keep ≥ 0.2 mm, parting-line gap ≤ 0.3 mm.
- `fasteners` — BOM lines `fx1…` aggregated by designation (mechanical; `unit_cost_est` Estimate from the C1 / built-in
  catalogue at ~2,000 pcs; an LCSC snapshot match would make them Sourced).
- `checks` (also appended to `EngineeringArtifact.checks` when the flag is on): `asm_interference`, `asm_static_overlap`,
  `asm_clearance`, `asm_parting_gap`, `asm_fastener_engagement` (material under each screw measured by line ∩ solid; insert
  needs boss ≥ insert + 0.5 mm, engagement ≥ 80 % of the insert; tapped metal ≥ 1.5·d; thread-forming ≥ 2·d),
  `asm_fastener_count`, `asm_joint_closure` (every child re-placed by `connect_to`, residual < 0.01 mm), `asm_support`.

**Additive fields.** `EngineeringCheck.domain` += `"assembly"`; `EngineeringArtifact.assembly: ProjectAssembly | null` (travels
into `FactoryPack.engineering`); `PartMeta.parent_part_id`, `PartMeta.joint`, `PartMeta.explode_vector`,
`PartMeta.explode_distance_mm` (null until the parts route calls `api.cad.assembly.service.part_extras`).

**Errors.** 404: flag off · unknown project / version · the version's GLB has no labelled STEP next to it (legacy W2 directions;
since C5 the two cached demos ship a labelled STEP for their chosen direction).

## 2D technical drawings (C3, additive — on by default since pass-7; set `CAD_DRAWINGS=0` to disable)
| Method | Path | Query | Response | Notes |
|---|---|---|---|---|
| GET | `/projects/{id}/drawings` | `?version=n` | `DrawingSheet[]` | built from the version's STEP on first request (0.6–9 s on the showcases), cached per version; 404 unknown project / version, no STEP, or `CAD_DRAWINGS=0` |
| GET/HEAD | `/files/{id}/drawings/{name}` | – | `image/svg+xml` / `application/pdf` | `v<n>_<sheet>.svg`, `v<n>_<sheet>.pdf` (one page), `v<n>_set.pdf` (every sheet); built on demand when a Factory Pack link arrives first (C5); 404 when off |

- On by default since pass-7. Disabled (`CAD_DRAWINGS=0`): the routes answer 404 and `/projects/{project_id}/drawings` is absent from the OpenAPI
  schema, so the web hides the Studio "Drawings" tab and the stage 3 link.
- Sheets: `A1` general assembly (A3: front, left, isometric; balloons = parts-list ITEM tied to the stage-3 BOM line;
  hidden lines omitted), `P01…` one sheet per distinct part (identical instances grouped, `qty`; largest first, ≤ 12),
  `M01…` moulded shells when the DFM enclosure STEP is the product's housing (two largest dimensions within 5 % of a part).
- Every sheet: first-angle projection (ISO E), front / top / left (or section A-A for hollow parts) + isometric (reference,
  not to scale), A4 or A3 landscape, scale from ISO 5455 standard scales; overall L × W × H measured on the STEP with the
  ISO 2768-m tolerance; holes / bosses (Ø, count, depth, pattern pitch) and wall thickness measured on the B-rep; fillets
  as a note; title block (product, part, material, finish, scale, units mm, ISO 2768-m, projection symbol, revision = `v<n>`,
  date, drawing no., sheet i/N) and the note "Generated from CAD — verify before release"; legend label **Measured**.
- `FactoryPack.drawings` (additive): the current version's sheets when enabled; the Launch Dossier prints each sheet as a
  vector page in a "Drawings" chapter (rotated onto A4) and lists them in Factory Pack section 3.
