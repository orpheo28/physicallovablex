"""Text-to-CAD engine (W19): the LLM writes build123d code, we execute it safely, measure it, and self-repair.

    generate_cad(product_brief, requirements=None, category=None, seed_family=None, previous_code=None,
                 instruction=None, *, project_id=None, out_dir=None, dims=None, colour=None, llm=None,
                 max_repairs=2, timeout_s=25.0) -> dict
    refine_cad(project_id, instruction, *, version=None, **kw) -> dict     # edit the latest model_vN.py (Cursor-style)

Flow: category (classify) → seed family (parametric, tested) → LLM writes/edits a full program starting from the
seed (or from previous_code in edit mode, never from scratch) → sandbox (AST policy + isolated subprocess) →
validate (real solids, volume > 0, bbox within 0.5×–2× of the requested size when given) → on failure the error is
fed back to the LLM (up to `max_repairs` times) → on final failure the seed family (or, in edit mode, the previous
version) is built instead, with a note. Output: model_vN.{py,glb,step,stl,json} in the project files dir.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Any, Callable

from api.cad.codegen import retrieval
from api.cad.codegen.classify import classify, seed_for
from api.cad.codegen.sandbox import run_code

log = logging.getLogger("cad.codegen")

LABEL = "AI-generated CAD (concept level) — geometry measured on the result"
FALLBACK_LABEL = "Parametric family CAD (concept level) — geometry measured on the result"

LLMFn = Callable[[str, str], str]  # (prompt, system) -> reply text

SYSTEM = """You are a senior industrial designer and CAD engineer. In hardware, CAD is code: you write a Python
program with build123d (v0.13) that builds a concept-level 3D model of a physical product.

Hard rules (a sandbox enforces them; any violation is rejected):
- Only `import math` and `from build123d import *` (or named imports from build123d). No other imports.
- No file, OS or network access; no open/exec/eval/getattr/type; no names or attributes starting with "_";
  no export_*/import_* functions — we export and measure the result for you.
- Define `def build():` returning a list of solid parts (build123d Part/Solid objects, not 2D sketches).
- Label every part: `part.label = "<role>.<n>"`; role picks the material and must be one of:
  body (main shell, product colour), accent (secondary colour), metal (aluminium), steel, coat (dark powder
  coat / dark plastic), rubber, button, led (glowing indicator), glass (dark glass / display), clear (transparent
  plastic), diffuser (lit frosted), port, wood, fabric (soft pad / textile), cell (PV cells), fin, roof, wall.
- Units mm. Z is up; the product rests on z=0, centred on the origin. Realistic real-world proportions.
- Keep all key dimensions in a dict `P` at the top so a human can tweak them.
- Runs in < 15 s: fewer than ~120 parts, no big loops of booleans. Wrap fragile fillets in try/except and keep
  the unfilleted shape if OCCT refuses.

build123d algebra API that works (use these):
  Box(length, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN)), Cylinder(radius, height),
  Cone(bottom_radius, top_radius, height), Sphere(radius), Torus(major_radius, minor_radius),
  Pos(x, y, z) * shape, Rot(rx, ry, rz) * shape (degrees), shape.moved(Location((x, y, z))),
  Plane(origin=(x, y, z), x_dir=(1, 0, 0), z_dir=(0, 0, 1)) * shape_or_sketch,
  2D: Rectangle(w, h), RectangleRounded(w, h, radius), Circle(r), Ellipse(rx, ry), RegularPolygon(r, n),
      Polygon(*pts), make_face(Polyline(p1, p2, ..., close=True)), make_face(Spline(...) ...)
  extrude(face, amount=h, taper=deg), revolve(face, axis=Axis.Z, revolution_arc=360),
  loft([Plane(...) * Circle(..), Plane(...) * Rectangle(..), ...]), sweep(face, path=Spline(...)),
  mirror(shape, about=Plane.YZ), a + b, a - b, a & b,
  fillet(shape.edges().filter_by(Axis.Z), radius=r), chamfer(edges, length=l),
  shape.edges().group_by(Axis.Z)[-1], shape.faces().sort_by(Axis.Z)[-1], shape.bounding_box().size.X,
  Vector(x, y, z), Axis.X/Y/Z, Align.MIN/CENTER/MAX. Cylinder/Cone/Box are centred unless align= is given.

Reply with the complete Python program in ONE ```python code block, then at most 3 one-line notes."""

GENERIC_SEED = '''"""Minimal example of the conventions: a rounded two-tone device with a button and a status LED."""
import math

from build123d import *

P = {"length": 110.0, "width": 70.0, "height": 32.0, "corner": 14.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H, r = P["length"], P["width"], P["height"], P["corner"]
    lower = extrude(RectangleRounded(L, W, r), amount=H * 0.4)
    upper = Pos(0, 0, H * 0.4) * extrude(RectangleRounded(L, W, r), amount=H * 0.6)
    try:
        upper = fillet(upper.edges().group_by(Axis.Z)[-1], radius=H * 0.25)
    except Exception:
        pass
    button = Pos(0, -W * 0.15, H) * Cylinder(W * 0.12, 3)
    led = Pos(L * 0.3, W * 0.2, H) * Cylinder(2.0, 1.5)
    return [lab(upper, "body", 1), lab(lower, "accent", 1), lab(button, "button", 1), lab(led, "led", 1)]
'''

# C4 (CODEGEN_RAG=1 only): build123d do/don't list appended to SYSTEM — gotchas verified while building examples/.
RAG_RULES = """
build123d 0.13 — DO (verified in this sandbox):
- Build solids with the algebra API above; if you use BuildPart/BuildSketch, return `builder.part`, never the builder.
- Rest the product on z=0: Box/Cylinder/Cone/Sphere are CENTRED, so pass align=(Align.CENTER, Align.CENTER, Align.MIN)
  or Pos(0, 0, h / 2) * ...; extrude() of an XY sketch already starts at z=0. Polygon(*pts, align=None) keeps your coords.
- Place 2D sketches with `Plane.XZ * sketch` (normal -Y, local y = world Z), `Plane.YZ * sketch` (normal +X) or
  `Plane(origin=..., z_dir=...) * sketch`. Revolve: profile on Plane.XZ with x >= 0 (points (r, z)), about Axis.Z.
- Sweep: profile at the path start, perpendicular to it: `Plane(origin=path @ 0, z_dir=path % 0) * Circle(r)`;
  FilletPolyline(*pts, radius=r) makes a bent-tube path; sweeping `Circle(R) - Circle(r)` gives a hollow tube.
- Threads: `Helix(pitch, height, radius)`; profile on `Plane(origin=h @ 0, x_dir=(1, 0, 0), z_dir=h % 0)` (local +x =
  radially outward), buried ~0.3 mm in the wall, `sweep(profile, h, is_frenet=True)`; <= 6 turns.
- Hollow parts: `offset(solid, amount=-wall, openings=solid.faces().sort_by(Axis.Z)[-1])`. Shell FIRST, fillet only
  edges away from the opening, radius > wall. Draft: extrude UP with a positive taper, then shell.
- Patterns: `PolarLocations(r, n) * shape` / `GridLocations(dx, dy, nx, ny) * shape` return a LIST (not indexable
  locations): cut it in one boolean (`body - holes`), fuse with `a + list`. Offset a pattern with
  `Pos(...) * GridLocations(...) * shape` or `PolarLocations(...) * (Pos(...) * shape)` — `Locations * Pos` is a TypeError.
- Holes in algebra mode: subtract Cylinder (+ a wider shallow Cylinder = counterbore, + Cone = countersink);
  CounterBoreHole/Hole only work inside BuildPart.
- `mirror(shape, about=Plane.YZ)` returns ONLY the mirrored copy: use `half + mirror(half, about=Plane.YZ)`.
- `split(shape, bisect_by=Plane.XY, keep=Keep.TOP)` — always pass bisect_by (the default is Plane.XZ).
- Fillet/chamfer simple edges before booleans, each in try/except; radius < half the thinnest wall. `fillet(edges,
  radius=r)` (function) and `part.fillet(r, edges)` (method) take arguments in opposite order.
- RectangleRounded(w, h, r) needs r < min(w, h) / 2; SlotOverall(length, width) needs length > width.
- Keep P consistent with the target size and derive every position from P.
build123d 0.13 — DON'T:
- No Text/fonts, no CadQuery (Workplane, `.faces(">Z")` strings, cq.*), no import/export.
- No twisted lofts of Ellipse sections (silently broken solids): twist SlotOverall / RectangleRounded sections instead.
  Loft sections must lie on DIFFERENT planes, ordered along the path.
- No self-intersecting Polygon outlines, no zero-thickness, tangent or coincident-face booleans (overlap parts by
  >= 0.5 mm, e.g. run a post into a barrel's centre, or leave a gap).
- No variables named os, sys, socket, type, open, input, vars (the sandbox rejects them); `shape.is_valid` is a property.
- Do not return sketches, wires or edges from build(): only solids, each with a role label."""

_CODE_RX = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


# --------------------------------------------------------------------------- helpers


def extract_code(reply: str) -> str:
    """Python program from an LLM reply: the longest fenced block, else the raw text (JSON {"code": …} accepted)."""
    blocks = _CODE_RX.findall(reply or "")
    if blocks:
        return max(blocks, key=len).strip() + "\n"
    txt = (reply or "").strip()
    if txt.startswith("{"):
        try:
            return str(json.loads(txt)["code"]).strip() + "\n"
        except (ValueError, KeyError, TypeError):
            pass
    return txt + "\n"


def _text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return "; ".join(f"{k}: {v}" for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return "; ".join(_text(i) for i in x)
    if hasattr(x, "model_dump"):  # Brief / Pydantic models
        d = x.model_dump(exclude_none=True)
        keep = ("product_name", "one_liner", "category", "key_features", "target_user", "use_context", "prompt")
        return "; ".join(f"{k}: {_text(d[k])}" for k in keep if d.get(k)) or json.dumps(d, default=str)[:1500]
    return str(x)


def target_dims(dims: Any = None, requirements: Any = None) -> tuple[float, float, float] | None:
    """(L, W, H) mm from `dims` (tuple / dict / contracts Dimensions) or from length/width/height keys in requirements."""
    src = dims if dims is not None else requirements
    if src is None:
        return None
    if isinstance(src, (list, tuple)) and len(src) == 3:
        vals = [float(v) for v in src]
    elif hasattr(src, "length") and hasattr(src, "width") and hasattr(src, "height"):
        vals = [float(getattr(getattr(src, k), "value", getattr(src, k))) for k in ("length", "width", "height")]
    elif isinstance(src, dict):
        pick = [src.get(k, src.get(f"{k}_mm")) for k in ("length", "width", "height")]
        if any(v is None for v in pick):
            return None
        vals = [float(getattr(v, "value", v)) for v in pick]
    else:
        return None
    return tuple(vals) if all(v > 0 for v in vals) else None  # type: ignore[return-value]


def check_dims(bbox: list[float], dims: tuple[float, float, float] | None) -> str | None:
    """None if the measured bbox is within 0.5×–2× of the requested size (orientation-free: sorted extents)."""
    if not dims:
        if max(bbox) < 5 or max(bbox) > 30000:
            return f"implausible overall size {bbox} mm (check units: mm)"
        return None
    got, want = sorted(bbox), sorted(dims)
    bad = [(g, w) for g, w in zip(got, want) if not (0.5 * w <= g <= 2.0 * w)]
    if bad:
        return (f"Measured bounding box {[round(v) for v in bbox]} mm is outside 0.5×–2× of the requested size "
                f"{[round(v) for v in dims]} mm (L×W×H). Rescale the model to the requested size.")
    return None


def _default_llm(prompt: str, system: str) -> str:
    from api.llm import complete_text

    return complete_text("main", prompt, system=system, max_tokens=7000)


def _llm_model() -> str:
    try:
        from api.llm import model_for

        return model_for("main") or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def _next_version(out: Path) -> int:
    nums = [int(m.group(1)) for f in out.glob("model_v*.py") if (m := re.match(r"model_v(\d+)\.py$", f.name))]
    return max(nums, default=0) + 1


def system_prompt() -> str:
    """SYSTEM, plus the standard-part helpers (api.cad.stdparts.PROMPT_SNIPPET) at CAD_DETAIL_LEVEL=pro (C5)."""
    from api.cad.stdparts import PROMPT_SNIPPET, is_pro

    return SYSTEM + PROMPT_SNIPPET if is_pro() else SYSTEM


def _seed(family: str | None, variant: str | None, params: dict | None = None) -> tuple[str, str]:
    """(seed code, seed name). Families of api.cad.families have runnable seed code; others get the generic example.
    `params` (W21): the family parameters of the product being designed (Studio: the chosen direction's)."""
    from api.cad import families

    if family in families.names():
        p = families.params_for(family, **params) if params else families.params_for(family, variant)  # type: ignore[arg-type]
        return families.seed_code_for(family, p), family  # type: ignore[arg-type]
    return GENERIC_SEED, "generic_example"


# --------------------------------------------------------------------------- prompts


def _gen_prompt(brief: str, req: str, category: str, dims, seed: str, seed_name: str) -> str:
    size = f"{dims[0]:.0f} × {dims[1]:.0f} × {dims[2]:.0f} mm (L × W × H; the result must be within 0.5×–2×)" if dims \
        else "not given — use realistic real-world dimensions for this product"
    how = ("Here is a WORKING, tested parametric program for the closest product family "
           f"`{seed_name}`. Start from it: keep its structure and whatever already fits, then change parameters and "
           "add / remove / reshape features until the model is clearly THIS product (recognisable at a glance)."
           if seed_name != "generic_example" else
           "Here is a minimal WORKING example of the conventions (not the product). Design the product from scratch "
           "following the same conventions, with the recognisable features of this product.")
    return (f"Product brief: {brief}\nRequirements: {req or '—'}\nCategory: {category}\nTarget overall size: {size}\n\n"
            f"{how}\n\n```python\n{seed}```\n\nWrite the complete program for this product.")


def _edit_prompt(brief: str, code: str, instruction: str, dims) -> str:
    size = f"\nTarget overall size: {dims[0]:.0f} × {dims[1]:.0f} × {dims[2]:.0f} mm (L × W × H)." if dims else ""
    return (f"Product: {brief}{size}\n\nCurrent program (it runs and is what the user sees):\n```python\n{code}```\n\n"
            f"Change requested by the user: \"{instruction}\"\n\nEdit the existing program to apply exactly this "
            "change — keep everything else identical (same parameters, parts, labels, structure) unless the change "
            "requires otherwise. Do not rewrite from scratch. Return the complete updated program.")


def _repair_prompt(brief: str, task: str, code: str, error: str, hints: str = "") -> str:
    return (f"Product: {brief}\nTask: {task}\n\nYour program failed in our sandbox:\n{error[:3000]}\n\n"
            f"Program:\n```python\n{code}```\n\n{hints}Fix it with the smallest change that makes it run and pass the check "
            "(if a fillet, loft or boolean failed, simplify or drop that feature). Return the complete program.")


# C4 (CODEGEN_RAG=1 only): error text -> targeted fix hint for the repair prompt
REPAIR_HINTS: list[tuple[re.Pattern, str]] = [(re.compile(p, re.I), h) for p, h in (
    (r"fillet|chamfer|StdFail_NotDone|BRep_API: command not done",
     "A fillet/chamfer/boolean failed in OCCT: lower the radius (< half the thinnest wall), select fewer edges, "
     "apply it before the booleans, or wrap it in try/except and keep the unfilleted shape."),
    (r"must be > 2\*radius|width and height must", "RectangleRounded(w, h, r) needs r < min(w, h) / 2 — clamp the radius."),
    (r"no solid volume|2D sketch|expected build123d solids|returned no parts",
     "build() must return 3D solids: extrude/revolve sketches first; a boolean may have removed everything "
     "(check the cutter is not bigger than the body) — return only non-empty solids."),
    (r"Measured bounding box|outside 0\.5",
     "Scale the dimensions in P to the requested overall size, and check that no part sticks far out (a stray "
     "offset, a mis-rotated part, or a pattern radius in the wrong units)."),
    (r"Timeout|ran longer", "Too slow: fuse/cut pattern lists in one boolean, cut fewer holes, drop helix threads "
                             "and fillets on many edges."),
    (r"policy violation", "Only `import math` and `from build123d import *`; no names/attributes starting with '_', "
                          "no open/exec/eval/getattr/type, no export_*/import_* — we export the result."),
    (r"NameError|is not defined", "A name is not defined: build123d 0.13 has no such class/function (CadQuery "
                                  "names like Workplane do not exist) — use the API listed in the system prompt."),
    (r"loft", "loft needs >= 2 sections on DIFFERENT planes, ordered along the path, ideally with the same number of edges."),
    (r"sweep", "sweep needs the profile at the path start, perpendicular to it: Plane(origin=path @ 0, z_dir=path % 0) * profile."),
    (r"revolve", "revolve: draw the profile on Plane.XZ with x >= 0 and revolve about Axis.Z; the profile must not cross the axis."),
)]


def repair_hints(error: str) -> str:
    hits = [h for rx, h in REPAIR_HINTS if rx.search(error or "")]
    return ("Likely fix:\n" + "\n".join(f"- {h}" for h in hits[:3]) + "\n\n") if hits else ""


# --------------------------------------------------------------------------- engine


def _attempt(code: str, dims, timeout_s: float) -> tuple[dict, str | None]:
    res = run_code(code, timeout_s=timeout_s)
    if not res.get("ok"):
        return res, res.get("error") or "unknown sandbox error"
    dim_err = check_dims(res["bbox_mm"], dims)
    if dim_err:
        return res, "Validation failed: " + dim_err
    return res, None


def _publish(res: dict, code: str, out: Path, n: int, look: dict, pid: str | None) -> dict[str, Any]:
    from api.cad.build import publish

    files: dict[str, Path] = {}
    for k in ("step", "stl", "glb"):
        files[k] = publish(res["files"][k], out / f"model_v{n}.{k}")
    finish_program_glb(files["glb"], look, code, res)
    (out / f"model_v{n}.py").write_text(code, encoding="utf-8")
    shutil.rmtree(res.get("work_dir") or "/nonexistent", ignore_errors=True)
    urls = {k: f"/files/{pid}/model_v{n}.{k}" for k in files} if pid else {}
    return {"files": files, "urls": urls}


def program_names(code: str, res: dict) -> dict:
    """W29: label → semantic part (api.cad.parts) from the program and the label call sites the sandbox traced.
    C5: standard parts the program placed (api.cad.stdparts, `std_meta` carried out of the sandbox) are named by
    api.cad.stdparts.bom.hardware_names (one BOM-linked node per spec, anatomy layer "fasteners")."""
    from api.cad.parts import names_from_source

    sites = res.get("label_sites") or {}
    mark = code.find("# === PRO DETAIL === (C5:")
    if mark >= 0:  # C5: a pro block appended to a recorded program only wraps build(): name parts by the program's frames
        first = code.count("\n", 0, mark) + 1
        sites = {lb: ([x for x in ln if x < first] or ln) for lb, ln in sites.items()}
    try:
        names = names_from_source(code, sites, [r["label"] for r in res.get("parts") or []])
    except Exception:  # noqa: BLE001 — naming is metadata: default names are still valid parts
        names = {}
    hw = program_hardware(res)
    return {**names, **hw} if hw else names


def program_hardware(res: dict) -> dict:
    """label → hardware info for the standard parts of a sandbox result ({} when the program placed none)."""
    from types import SimpleNamespace

    rows = [r for r in res.get("parts") or [] if isinstance(r.get("std_meta"), dict)]
    if not rows:
        return {}
    try:
        from api.cad.stdparts.bom import hardware_names

        return hardware_names([SimpleNamespace(label=r["label"], std_meta=r["std_meta"]) for r in rows])
    except Exception as e:  # noqa: BLE001 — naming is metadata
        log.info("program hardware names skipped: %s", e)
        return {}


def finish_program_glb(glb_path: Path, look: dict | None, code: str, res: dict) -> None:
    """Finish a program's GLB: W29 names + look, then the standard parts' BOM facts on their nodes (C1/C5)."""
    from api.cad.families import apply_look
    from api.cad.families._common import stamp_hardware

    apply_look(glb_path, look, names=program_names(code, res))
    hw = program_hardware(res)
    if hw:
        stamp_hardware(glb_path, hw)


def _fallback_existing(category: str, out: Path, n: int, look: dict, pid: str | None) -> dict[str, Any] | None:
    """Wearables: W17's in-process family (api/cad/build.py 3/4) — there is no seed program for it here."""
    if category != "wearable":
        return None
    from api.cad.build import build_direction, normalize, shape_facts
    from api.cad.look import build_assembly
    from api.cad.wearables import PRESETS

    params = normalize(PRESETS[3])
    f = build_direction(params, out, name=f"model_v{n}")
    facts = shape_facts(f["step"])  # the moulded parts (at pro, build_assembly then puts the full product's STEP here)
    build_assembly(params, out / f"model_v{n}.glb", look, set())
    files = {"step": f["step"], "stl": f["stl"], "glb": out / f"model_v{n}.glb"}
    return {"files": files, "urls": {k: f"/files/{pid}/model_v{n}.{k}" for k in files} if pid else {},
            "bbox_mm": [round(v, 2) for v in facts["size"]], "volume_mm3": round(facts["volume_mm3"], 1),
            "parts": [{"label": "wearable_band", "role": "body", "bbox_mm": [round(v, 2) for v in facts["size"]],
                       "volume_mm3": round(facts["volume_mm3"], 1)}]}


def generate_cad(product_brief: Any, requirements: Any = None, category: str | None = None,
                 seed_family: str | None = None, previous_code: str | None = None, instruction: str | None = None, *,
                 project_id: str | None = None, out_dir: Path | str | None = None, dims: Any = None,
                 colour: str | None = None, variant: str | None = None, llm: LLMFn | None = None,
                 max_repairs: int = 2, timeout_s: float = 25.0, seed_params: dict | None = None,
                 material: str = "pc_abs", finish: str = "") -> dict[str, Any]:
    """Write → run → measure → self-repair. Never raises for bad model code; see the module docstring."""
    from api.cad import families
    from api.cad.build import project_dir
    from api.llm import LLMError

    t0 = time.monotonic()
    brief = _text(product_brief)
    req = _text(requirements)
    category = category or classify(f"{brief} {req}")
    fam, var = seed_for(category, f"{brief} {req}")
    seed_family = seed_family or fam
    variant = variant or var
    dims_t = target_dims(dims, requirements if isinstance(requirements, dict) else None)
    out = Path(out_dir) if out_dir else (project_dir(project_id) if project_id else None)
    if out is None:
        raise ValueError("generate_cad needs project_id or out_dir")
    out.mkdir(parents=True, exist_ok=True)
    n = _next_version(out)
    look = families.family_look(colour or families.DEFAULT_COLOUR.get(seed_family or "", None), finish, material)
    seed, seed_name = _seed(seed_family, variant, seed_params)
    edit = bool(previous_code)
    task = f'edit: "{instruction}"' if edit else "write the program for this product"
    call = llm or _default_llm
    attempts: list[dict[str, Any]] = []
    notes: list[str] = []
    code, res, err = None, None, None

    prompt = _edit_prompt(brief, previous_code, instruction or "improve the model", dims_t) if edit else \
        _gen_prompt(brief, req, category, dims_t, seed, seed_name)
    system, rag = system_prompt(), None
    if retrieval.enabled():  # C4: retrieved library examples + do/don't list + repair hints (off = prompts unchanged)
        system += RAG_RULES
        query = f"{brief} {req} {category} {instruction or ''}"
        block = retrieval.examples_block(query, k=2 if edit else 4, budget_chars=5000 if edit else 9000,
                                         exclude_family=None if edit else seed_name)
        rag = {"examples": retrieval.last_ids(block)}
        if block:
            prompt += "\n\n" + block
    for i in range(1 + max(0, max_repairs)):
        a: dict[str, Any] = {"n": i + 1, "kind": "edit" if edit and i == 0 else ("repair" if i else "generate")}
        t = time.monotonic()
        try:
            reply = call(prompt, system)
        except LLMError as e:
            a.update(error=f"LLM unavailable: {e}", seconds=round(time.monotonic() - t, 2))
            attempts.append(a)
            notes.append(f"LLM unavailable ({type(e).__name__}) — fell back without AI code")
            err = str(e)
            code = None
            break
        a["llm_seconds"] = round(time.monotonic() - t, 2)
        cand = extract_code(reply)
        res, err = _attempt(cand, dims_t, timeout_s)
        a.update(run_seconds=res.get("seconds_total", res.get("seconds")), error=err[:1200] if err else None,
                 error_kind=res.get("kind") if err else None)
        attempts.append(a)
        code = cand
        if err is None:
            break
        log.info("codegen attempt %d failed: %s", i + 1, err[:300])
        if res.get("work_dir"):
            shutil.rmtree(res["work_dir"], ignore_errors=True)
        prompt = _repair_prompt(brief, task, cand, err, repair_hints(err) if rag is not None else "")

    if err is None and code is not None and res is not None:
        status = "ok" if len(attempts) == 1 else "repaired"
        source = f"llm:{_llm_model()}" if llm is None else "llm:injected"
        pub = _publish(res, code, out, n, look, project_id)
        measured = {"bbox_mm": res["bbox_mm"], "volume_mm3": res["volume_mm3"], "parts": res["parts"]}
        label = LABEL
    else:
        # final failure: previous version (edit mode) or the seed family — both are known-good programs
        status = "fallback"
        fb_code = previous_code if edit else seed
        if not edit and category == "wearable" and seed_name == "generic_example":
            fb_code = None  # W17's band family (below) is a better fallback than the generic example
        label = FALLBACK_LABEL
        pub = None
        if fb_code is not None:
            res2, err2 = _attempt(fb_code, None, timeout_s)
            if err2 is None:
                pub = _publish(res2, fb_code, out, n, look, project_id)
                measured = {"bbox_mm": res2["bbox_mm"], "volume_mm3": res2["volume_mm3"], "parts": res2["parts"]}
                code = fb_code
                what = "previous version kept" if edit else f"seed family `{seed_name}` used"
                notes.append(f"AI code failed after {len(attempts)} attempt(s) — {what}. Last error: {(err or '')[:300]}")
                if edit:
                    label = LABEL
        if pub is None:
            ex = _fallback_existing(category, out, n, look, project_id)
            if ex is None:
                return {"status": "failed", "attempts": attempts, "notes": notes + [f"no fallback worked: {err}"],
                        "category": category, "seed_family": seed_family, "label": label, "code": code,
                        "seconds": round(time.monotonic() - t0, 2)}
            pub = {"files": ex["files"], "urls": ex["urls"]}
            measured = {k: ex[k] for k in ("bbox_mm", "volume_mm3", "parts")}
            code = None
            notes.append("AI code failed — W17 wearable family built in-process (no program to edit)")
        source = "previous_version" if edit else (f"seed:{seed_name}" if code else "family:wearable_band")

    result = {
        "status": status, "version": n, "code": code, "source": source, "label": label,
        "category": category, "seed_family": seed_family, "variant": variant,
        "files": {k: str(v) for k, v in pub["files"].items()}, "urls": pub["urls"],
        "code_path": str(out / f"model_v{n}.py") if code else None,
        "code_url": f"/projects/{project_id}/cad/code/{n}" if project_id and code else None,
        "bbox_mm": measured["bbox_mm"], "volume_mm3": measured["volume_mm3"], "parts": measured["parts"],
        "target_dims_mm": list(dims_t) if dims_t else None, "attempts": attempts, "notes": notes,
        "instruction": instruction, "parent_version": _parent_version(out, previous_code) if edit else None,
        "seconds": round(time.monotonic() - t0, 2),
    }
    if rag is not None:
        result["rag"] = rag
    meta = {k: v for k, v in result.items() if k != "code"}
    meta["brief"] = brief[:2000]
    (out / f"model_v{n}.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    return result


def _parent_version(out: Path, previous_code: str | None) -> int | None:
    for f in sorted(out.glob("model_v*.py"), key=lambda p: -int(re.sub(r"\D", "", p.stem) or 0)):
        try:
            if f.read_text(encoding="utf-8") == previous_code:
                m = re.match(r"model_v(\d+)\.py$", f.name)
                return int(m.group(1)) if m else None
        except OSError:
            continue
    return None


def latest_version(project_id: str | None = None, out_dir: Path | str | None = None) -> int | None:
    from api.cad.build import files_root

    out = Path(out_dir) if out_dir else files_root() / str(project_id)
    n = _next_version(out) - 1 if out.exists() else 0
    return n or None


def refine_cad(project_id: str | None, instruction: str, *, version: int | None = None,
               out_dir: Path | str | None = None, **kw: Any) -> dict[str, Any]:
    """Studio refine: edit model_v{version or latest}.py per `instruction` → a new version (never from scratch)."""
    from api.cad.build import files_root

    out = Path(out_dir) if out_dir else files_root() / str(project_id)
    v = version or latest_version(out_dir=out)
    if not v or not (out / f"model_v{v}.py").exists():
        raise FileNotFoundError(f"no generated CAD program to refine for {project_id or out}")
    code = (out / f"model_v{v}.py").read_text(encoding="utf-8")
    meta_path = out / f"model_v{v}.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    kw.setdefault("category", meta.get("category"))
    kw.setdefault("seed_family", meta.get("seed_family"))
    kw.setdefault("dims", meta.get("target_dims_mm"))
    brief = kw.pop("product_brief", None) or meta.get("brief", "")
    return generate_cad(brief, previous_code=code, instruction=instruction, project_id=project_id,
                        out_dir=out, **kw)
