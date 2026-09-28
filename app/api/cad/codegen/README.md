# api/cad/codegen/ — text-to-CAD engine (W19)

In hardware, CAD is code. The LLM (route `main`) writes a build123d program, we run it in a sandbox, measure the
result, and feed errors back for self-repair, the way Cursor fixes a compile error. Deterministic parametric
families (`api/cad/families/`) are both the seed the LLM starts from and the fallback when it fails.

```python
from api.cad.codegen import generate_cad, refine_cad, classify, seed_for, LABEL

r = generate_cad(brief, requirements=None, category=None, seed_family=None,       # new model
                 project_id=pid, dims=(L, W, H) | Dimensions | None, colour="#RRGGBB")
r = refine_cad(pid, "make the bin 20% larger")                                     # edit latest model_vN.py
r = generate_cad(brief, previous_code=code, instruction="…", project_id=pid)        # same, explicit
```

`r` = `{status: ok|repaired|fallback|failed, version, code, source, label, category, seed_family, files{step,stl,glb},
urls{…: /files/<pid>/model_vN.*}, code_url (/projects/<pid>/cad/code/N), bbox_mm, volume_mm3, parts[{label, role,
bbox_mm, volume_mm3}], attempts[{n, kind, llm_seconds, run_seconds, error, error_kind}], notes, parent_version, seconds}`.
Files: `model_vN.{py,glb,step,stl,json}` in the project files dir. Versions are never overwritten.

- `classify.py`: brief → `wearable | furniture_child | vacuum | home_robot | irrigation | solar_roof | board |
  lighting | ble_accessory | generic` → (family, variant).
- `sandbox.py`: AST whitelist (imports only build123d/math, no open/exec/eval/getattr/dunders/"_" attributes/file
  I/O), then `python -I -B _runner.py` in a fresh temp dir, clean env (no secrets), rlimits (CPU, AS
  `CODEGEN_MEM_MB`=1280, DATA `CODEGEN_DATA_MB`=640, FSIZE; single-threaded OpenBLAS — tuned for a 1 GB container, see docs/DEPLOY.md), 25 s wall clock kills the process group, macOS Seatbelt (no network, no writes
  outside the temp dir).
- `_runner.py`: child process. Restricted builtins + import guard, calls `build()`, checks solids, exports.
- `routes.py`: `GET /projects/{id}/cad/code/{n}` (files.py does not serve `.py`). Mount with `register(router)`.

Honesty: `LABEL` = "AI-generated CAD (concept level) — geometry measured on the result"; fallbacks carry
`FALLBACK_LABEL` and a note. Tests: `uv run pytest tests/test_codegen.py tests/test_cad_families.py` (LLM mocked).

## Retrieval-augmented prompts (C4, `CODEGEN_RAG=1`, default off)

- `library.py` + `examples/`: 84 sandbox-verified build123d programs (17 family seeds, the generic example, 66 idioms:
  `encl_` enclosures, `form_` revolve/loft/sweep/threads, `mech_` patterns/mirrors/joints), docstring = title,
  description, `tags:`; measured facts in `examples/index.json` (`python -m api.cad.codegen.library --reindex`).
- `retrieval.py`: pure-Python BM25 → up to 4 examples (2 in edit mode) within a 9,000-char budget (5,000 in edit
  mode), seed family excluded, weak matches dropped.
- `engine.py`: when the flag is on — `SYSTEM + RAG_RULES` (verified build123d do/don't list), the examples block
  appended to the generate/edit prompt, `repair_hints(error)` in repair prompts, and `result["rag"]["examples"]`.
  Flag off = prompts byte-identical to before (tested).
- Measured in docs/CAD_BENCH.md (`tests/cad_bench.py`): no gain over the current prompt with `gpt-6-sol`
  (100 % valid first try in both modes), 2.7× prompt tokens → left off. Tests: `tests/test_codegen_rag.py`.
