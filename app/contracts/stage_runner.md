# Stage runner contract

Code: `api/stages/runner.py` (runner), `api/stages/registry.py` (plug-in API), `api/discovery.py` (auto-import).

## Interface
```python
run_stage(project_id: str, n: int, inputs: dict | None = None) -> StageArtifact   # ARTIFACT_MODELS[n]
```
1. Builds a `StageContext(project, stage, inputs, artifacts={k: validated artifact}, factory_pack)`.
2. Calls the handler registered for stage n. Its return value is validated against `ARTIFACT_MODELS[n]`.
3. **Any exception** (LLMError, ValidationError, CAD crash, missing handler...) → loads
   `api/fixtures/<project.example or "desk_lamp">/<NN>_<name>.json`, sets `fallback: true` and `fallback_reason`.
4. Persists it as `draft` (SQLite, one JSON document per project × stage) and returns it.

## Writing a stage handler (Wave 1)
```python
# api/costs/engine.py  (any module under your folder; names starting with _ or test_ are not auto-imported)
from api.stages.registry import stage_handler, StageContext
from contracts.artifacts import CostsArtifact

@stage_handler(5)
def run(ctx: StageContext) -> CostsArtifact:
    spec = ctx.artifact(3)            # SpecArtifact | None
    ...
    return CostsArtifact(project_id=ctx.project.id, generated_by="code", ...)
```
- Set `generated_by` to `"code"` or `"llm:<model slug>"` (`api.llm.model_for(route)`).
- Don't catch-and-hide errors: raise, the runner falls back. Partial live results are fine if valid.
- Use `api.llm.complete_json(route, prompt, Schema)` for LLM calls (validation + 1 retry built in).
- A handler must be fast (< 30 s, PRD §15). Heavy CAD: cache files under `api/data/files/<project_id>/`.
- Providers: `@provider("factory_pack")` (ctx → FactoryPack), `@provider("export_pdf")` (ctx → bytes),
  `@provider("network")` (() → object with `list_factories()`, `get_factory(id)`, `list_rfqs(factory_id)`).
- Extra routes: define `register(router: APIRouter)` in a module of your folder.
- Discovery is automatic at API start (`uvicorn --reload` picks up new files). **Never edit `api/main.py`.**

## Ownership of handlers
| Stage | Handler owner | Folder |
|---|---|---|
| 1 Brief | W4 | api/agents |
| 2 Design, 3 CAD + spec | W2 | api/cad |
| 4 DFM | W2 (measured) + W4 functions (AI-reviewed, risks, certifications) | api/dfm, api/agents |
| 5 Investment, 11 Logistics, 12 Financing | W3 | api/costs |
| 6 Production plan, 9 Tooling, 10 QC, 13 Brand | W4 | api/agents |
| 7 Matching, 8 RFQ + negotiation | W5 | api/agents/negotiation (+ mcp/) |
| Factory Pack assembly, Launch Dossier PDF | W6 | api/export |

If two modules register the same stage, the last import wins and a warning is logged — don't.
