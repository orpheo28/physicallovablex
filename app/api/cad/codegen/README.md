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
