# api/agents/

**Owner: W4 — Agents.** Only this session edits this folder.

Stage 1 (brief + ≤5 clarifying questions, both modes), 6 (production plan), 9 (tooling + samples), 10 (QC), 13 (brand) via `@stage_handler(n)`; plus reusable functions for stage 4 (AI-reviewed DFM text, component risks, certification map) that W2 calls. Every LLM call goes through `api.llm.complete_json`. The `negotiation/` sub-folder belongs to W5.

Contracts: `contracts/artifacts.py`, `contracts/api.md`, `contracts/stage_runner.md`, `contracts/fixtures.md`. Never edit `contracts/`, `api/main.py`, `pyproject.toml`, `web/package.json` — send a CONTRACT CHANGE REQUEST to the Monitor.

## What lives here (W4)

| Module | Stage / function | LLM route | Without a key |
|---|---|---|---|
| `brief.py` | stage 1 (idea + prototype mode, ≤5 questions with defaults, answers from `inputs["answers"]`) | main | raises → fixture |
| `dfm_review.py` | `ai_review(spec, bom, measured) -> list[DFMIssue]` (stage 4, called by W2) | main | deterministic checklist |
| `certification.py` | `certification_map(brief, spec) -> list[Certification]` (stage 4, called by W2) | fast (optional nuance) | rule-based core |
| `production_plan.py` | stage 6 | fast (reasons + notes only) | code-written reasons, `generated_by="code"` |
| `tooling.py` | stage 9 (dates + 30/70 payments, Python date check → assumptions) | none | always code |
| `qc.py` | stage 10 (ISO 2859-1 General II, AQL 0/2.5/4.0, spec_refs validated) | fast | code-derived defects |
| `brand.py` | stage 13 | fast | raises → fixture |

`_common.py`, `_planning.py` are private helpers (lead-time table, sample-size table, formulas). Prompts: `prompts/*.md` (`{{placeholders}}`).

### `BriefArtifact.category` vocabulary (fixed — W2/W3 may rely on it for defaults)
`lighting`, `ble_accessory`, `iot_sensor`, `wearable`, `audio`, `input_device`, `kitchen_appliance`, `mechanical`, `other`.

### Stage 1 answers
`POST .../stages/1/run {"inputs": {"answers": {"q1": "US + EU", "q3": "€39"}}}` — keys are question ids (`q1`..`q5`) or topics (`markets`, `volume`, `target_price`, `battery`, `wireless`). An unanswered question keeps its default in `answer` and gets `skipped: true`.

### Stage 9 inputs
Optional `{"start_date": "YYYY-MM-DD"}` (default: next Monday). Lead time: stage 8 `final_terms` → recommended quote → stage 6 plan → defaults.

### Tests
`uv run pytest api/agents --ignore=api/agents/negotiation` — offline (key cleared by `api/agents/conftest.py`); `test_live_smoke.py` runs one tiny call per configured route only if `OPENROUTER_API_KEY` is set.

**Sourced citations (W13).** `certification.py` quotes 47 CFR Part 15 (15.19, 15.101, 15.103, 15.107, 15.109, 15.247, 15.407) from
`data/certs/fcc_part15.json` (written once by `_fetch_ecfr.py`, eCFR text as of 2026-09-22, retrieved 2026-09-26) in the FCC rows'
`applies_because`. CE / UKCA / UN38.3 rows carry hand-written EUR-Lex, gov.uk and IATA references (Sourced for the citation only);
costs and lead times stay Estimates.
