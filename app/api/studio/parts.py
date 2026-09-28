"""Parts of a version's 3D model (W29) — contract: contracts/api.md "3D parts & anatomy".

    GET  /projects/{id}/parts?version=n            → ProjectParts {version, glb_url, parts: PartMeta[]}
    POST /projects/{id}/parts/{part_id}/edit       → 202 StudioAccepted (api.studio.edit, deterministic, no LLM)

    version_context(pid, n) -> Ctx                  # snapshot, GLB path/url, program (AI CAD) of a version
    list_parts(pid, n=None) -> ProjectParts         # node extras of the GLB + editable params, BOM links, prices

The GLB is the version's `preview.glb_url` (non-Studio projects: version 0 = the chosen direction's model). A GLB made
before W29 (no named parts yet) is finished on first read into the project's files folder — a prebuilt file is never
modified in place (the generated folder is looked up first by GET /files).
"""

from __future__ import annotations

import logging
import math
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from api.cad import glb
from api.cad.build import files_root, project_dir
from api.stages import runner
from api.studio import product as P
from api.studio import store
from contracts.artifacts import LabeledValue, PartEditRequest, PartMeta, ProjectParts, StudioAccepted

log = logging.getLogger("studio.parts")

# AI CAD parameter → W17 / W2 enclosure parameter it also drives (so DFM, weight and costs follow the edit)
ENCLOSURE_SYNC = {"pod_thickness": "height", "pod_length": "length", "pod_width": "width", "thickness": "height",
                  "length": "length", "width": "width", "height": "height", "strap_width": "strap_width",
                  "strap_length": "strap_length", "band_width": "height", "outer_diameter": "length"}
_POSITIONAL = re.compile(r"(^|_)(x|y|z|pos|position|offset|center|centre|bottom|split|opening|loop|base|top_z|gap|spacing_z|"
                         r"clearance|margin)($|_)")
_PREFERRED = re.compile(r"thickness|length|width|height|diameter|depth|size|radius|count|span|reach")
MAX_EDITABLE = 4


@dataclass
class Ctx:
    pid: str
    n: int
    arts: dict
    glb_url: str
    path: Path
    program: str | None = None  # AI / family program of the model shown (model_v<k>.py)
    program_k: int | None = None
    notes: list[str] = field(default_factory=list)


def _resolve(pid: str, url: str) -> Path | None:
    from api.cad.files import resolve_file

    return resolve_file(pid, url.rsplit("/", 1)[-1])


def version_context(pid: str, n: int | None = None) -> Ctx:
    """Raises runner.NotFound (404) for an unknown project / version / missing GLB."""
    runner.get_project(pid)
    cur = store.current(pid)
    if n is None:
        n = cur
    if n == 0 and cur == 0:
        arts = store.live_artifacts(pid)
    else:
        v = store.get_version(pid, n)
        if v is None or v.status != "done":
            raise runner.NotFound(f"version {n} not found" if v is None else f"version {n} is {v.status}")
        arts = store.load_snapshot(pid, n)
    d = P.chosen(arts.get(2))
    url = None
    if n and (v := store.get_version(pid, n)) is not None and v.preview is not None:
        url = v.preview.glb_url
    if not url:
        url = P._cad_fields(arts.get(3), d)["glb_url"] if arts.get(3) is not None else (d.glb_url if d else None)
    if not url:
        raise runner.NotFound(f"version {n} has no 3D model")
    path = _resolve(pid, url)
    if path is None:
        raise runner.NotFound(f"3D model {url} not found")
    ctx = Ctx(pid=pid, n=n, arts=arts, glb_url=url, path=path)
    k = _program_k(pid, arts, path.name)
    if k is not None:
        code = _resolve_code(pid, k)
        if code is not None:
            ctx.program, ctx.program_k = code, k
    ensure_finished(ctx)
    return ctx


def _program_k(pid: str, arts: dict, name: str) -> int | None:
    m = re.match(r"model_v(\d+)\.glb$", name)
    if m:
        return int(m.group(1))
    from api.studio import cad as studio_cad

    spec = arts.get(3)
    if name.endswith("_ai.glb") and spec is not None:
        return studio_cad.current_model(spec)
    return None


def _resolve_code(pid: str, k: int) -> str | None:
    from api.cad.files import roots

    for root in roots(pid):
        f = root / f"model_v{k}.py"
        if f.is_file():
            return f.read_text(encoding="utf-8")
    return None


def look_of(arts: dict) -> dict:
    """The version's look (colour / material / finish) as used by the GLB builders."""
    from api.cad import family_mode
    from api.cad.families import family_look

    d = P.chosen(arts.get(2))
    if d is None:
        return family_look()
    fin, _, hex_ = P.split_finish(d.finish)
    look = family_look(hex_, fin, d.material if family_mode.family_of(d) else P.material_key(d.material))
    look["_meta"] = {**look["_meta"], "material_text": d.material}
    return look


def ensure_finished(ctx: Ctx) -> None:
    """A pre-W29 GLB (no part nodes) → finished copy in the project's files folder (same name, served first)."""
    from pygltflib import GLTF2

    try:
        if glb.is_finished(GLTF2.load(str(ctx.path))):
            return
    except Exception as e:  # noqa: BLE001
        raise runner.NotFound(f"3D model unreadable: {e}") from None
    dst = project_dir(ctx.pid) / ctx.path.name
    if ctx.path.resolve() != dst.resolve():
        shutil.copyfile(ctx.path, dst)
    names = None
    if ctx.program:
        names = _names_for_program(ctx.program)
    else:
        from pygltflib import GLTF2 as G

        from api.cad.parts import fixed_names

        names = fixed_names([n.name for n in G.load(str(dst)).nodes if n.mesh is not None and n.name])
    glb.finalize(dst, look_of(ctx.arts), names=names)
    ctx.path = dst


def _names_for_program(code: str) -> dict:
    """Label → part names for a recorded program without sandbox sites (static analysis only)."""
    from api.cad.codegen.sandbox import run_code
    from api.cad.codegen.engine import program_names

    try:
        res = run_code(code, timeout_s=40)
        names = program_names(code, res) if res.get("ok") else {}
        import shutil as sh

        sh.rmtree(res.get("work_dir") or "/nonexistent", ignore_errors=True)
        return names
    except Exception:  # noqa: BLE001
        return {}


# --------------------------------------------------------------------------- editable parameters


def _step_for(v: float, key: str) -> float:
    if "count" in key or key.startswith("n_"):
        return 1.0
    a = abs(v)
    return 0.1 if a < 5 else 0.5 if a < 50 else 1.0 if a < 500 else 5.0


def _unit_for(key: str) -> str:
    if "deg" in key or "angle" in key:
        return "deg"
    if "count" in key or key.startswith("n_"):
        return "count"
    return "mm"


def _label_for(key: str) -> str:
    k = re.sub(r"_(mm|deg)$", "", key)
    return k.replace("_", " ").capitalize()


def _family_range(fam: str, key: str) -> tuple[float, float] | None:
    from dataclasses import asdict, fields

    from api.cad import families

    try:
        mod = families.module(fam)
    except KeyError:
        return None
    if key not in {f.name for f in fields(mod.Params)}:
        return None
    base = mod.default_params()
    hi = asdict(mod.Params(**{**base, key: 1e9}).clamped())[key]
    lo = asdict(mod.Params(**{**base, key: -1e9}).clamped())[key]
    return float(lo), float(hi)


def _enclosure_range(params: dict, key: str) -> tuple[float, float] | None:
    from api.cad.wearables import RANGES

    fam = int(params.get("family", 0))
    if fam in RANGES and key in RANGES[fam]:
        return RANGES[fam][key]
    return {"length": (20.0, 400.0), "width": (15.0, 400.0), "height": (4 * params.get("wall", 2.0) + 1.0, 400.0)}.get(key)


def param_spec(ctx: Ctx, key: str) -> dict | None:
    """{param, label, min, max, step, unit, value, target} of one editable parameter of the version, or None."""
    from api.cad import family_mode
    from api.cad.build import normalize
    from api.cad.parts import program_params

    d = P.chosen(ctx.arts.get(2))
    fam = family_mode.family_of(d) if d is not None else None
    prog = program_params(ctx.program) if ctx.program else {}
    value, rng, target = None, None, None
    if key in prog:
        value, target = prog[key], "program"
        if fam and key in family_mode.fparams(d):
            rng = _family_range(fam, key)
        elif not fam and d is not None and ENCLOSURE_SYNC.get(key):
            rng = _enclosure_range(normalize(d.cad_parameters or {}), ENCLOSURE_SYNC[key])
    elif fam and key in family_mode.fparams(d):
        value, target, rng = float(family_mode.fparams(d)[key]), "family", _family_range(fam, key)
    elif d is not None and not fam:
        p = normalize(d.cad_parameters or {})
        if key in p:
            value, target, rng = float(p[key]), "enclosure", _enclosure_range(p, key)
    if value is None:
        return None
    step = _step_for(value, key)
    lo, hi = (value * 0.5, value * 2.0) if value > 0 else (value - 10, value + 10)
    if rng is not None:
        lo, hi = max(lo, rng[0]), min(hi, rng[1])
    if step >= 1:
        lo, hi = math.ceil(lo), math.floor(hi)
    else:
        lo, hi = math.ceil(lo / step) * step, math.floor(hi / step) * step
    lo, hi = min(lo, value), max(hi, value)
    return {"param": key, "label": _label_for(key), "min": round(lo, 3), "max": round(hi, 3), "step": step, "unit": _unit_for(key),
            "value": round(value, 3), "target": target}


def _rank(keys: list[str], part: dict) -> list[str]:
    from api.cad.parts import _tokens

    words = set(_tokens(part["part_id"])) | set(_tokens(part["name"]))

    def score(k: str) -> tuple:
        toks = set(_tokens(k))
        return (-len(toks & {w.rstrip("s") for w in words} | toks & words), 0 if _PREFERRED.search(k) else 1, k)

    return sorted([k for k in keys if not _POSITIONAL.search(k)], key=score)


def editable_for(ctx: Ctx, part: dict, part_params: dict) -> list[dict]:
    keys = list(part_params.get(part["part_id"]) or [])
    if not keys and not ctx.program:  # enclosure families (W2 / W17): fixed parameters per part
        keys = {"shell_top": ["height", "length", "width"], "shell_bottom": ["height", "length", "width"],
                "strap": ["strap_width", "strap_length"]}.get(part["part_id"], [])
    out = []
    for k in _rank(keys, part):
        s = param_spec(ctx, k)
        if s is not None:
            out.append(s)
        if len(out) >= MAX_EDITABLE:
            break
    return out


# --------------------------------------------------------------------------- BOM links

_BOM_HINTS = {
    "strap": r"strap|band", "battery": r"batter|li-?po|li-?ion|cell pack", "button": r"button|switch|tact|trigger",
    "motor": r"motor|bldc", "prop": r"prop", "window": r"ppg|optical|sensor window|lens|glass|display|screen|bin|canister",
    "lens": r"lens|camera", "connector": r"usb|connector|port", "antenna": r"antenna", "diffuser": r"led|light pipe|diffuser",
    "shell_top": r"top shell|upper|housing|enclosure|shell|body|frame", "shell_bottom": r"bottom shell|lower|base|shell|housing",
    "frame": r"frame|chassis|rail|wand|tube|arm|leg", "arm": r"arm", "component": r"camera|gimbal|sensor|module",
}


def bom_link(part: dict, arts: dict, used: set[str]) -> dict:
    spec, costs = arts.get(3), arts.get(5)
    if spec is None:
        return {}
    rx = _BOM_HINTS.get(part["role"])
    name_rx = re.compile("|".join(re.escape(t) for t in re.findall(r"[a-z]{4,}", part["name"].lower())) or "^$")
    best = None
    for b in spec.bom:
        text = f"{b.part} {b.description or ''}".lower()
        s = (2 if name_rx.search(text) else 0) + (1 if rx and re.search(rx, text) else 0)
        if s and (best is None or s > best[0]) and not (b.id in used and s < 2):
            best = (s, b)
    if best is None:
        return {}
    b = best[1]
    used.add(b.id)
    price = next((ln.unit_price for ln in (costs.bom_lines if costs is not None else []) if ln.bom_item_id == b.id), None) \
        or b.unit_cost_est
    pkg = None
    if b.lcsc_pn:
        from api.costs.lcsc import get_part

        lp = get_part(b.lcsc_pn)
        pkg = lp.package if lp else None
    return {"bom_item_id": b.id, "lcsc_pn": b.lcsc_pn, "package": pkg,
            "unit_price": price.model_dump() if isinstance(price, LabeledValue) else price}


# --------------------------------------------------------------------------- listing


def enriched(ctx: Ctx) -> list[dict]:
    rx = glb.root_extras(ctx.path)
    part_params = rx.get("part_params") or {}
    used: set[str] = set()
    out = []
    for e in glb.read_parts(ctx.path):
        e = dict(e)
        e["editable"] = [{k: v for k, v in s.items() if k != "target"} for s in editable_for(ctx, e, part_params)]
        e.update({k: v for k, v in bom_link(e, ctx.arts, used).items() if v is not None})
        out.append(e)
    from api.cad.assembly import service as asm

    if asm.enabled():  # C2/C5: parent in the assembly tree, joint kind, joint-derived explode vector
        try:
            extra = asm.part_extras(ctx.pid, ctx.n)
            for e in out:
                e.update(extra.get(e["part_id"], {}))
        except Exception as ex:  # noqa: BLE001 — parts never fail because of the assembly
            log.info("assembly part extras skipped for %s v%s: %s", ctx.pid, ctx.n, ex)
    return out


def list_parts(pid: str, n: int | None = None) -> ProjectParts:
    ctx = version_context(pid, n)
    parts = enriched(ctx)
    if ctx.path.resolve().is_relative_to(files_root().resolve()):
        try:  # node extras = PartMeta (cheap JSON rewrite, only when something changed)
            glb.set_extras(ctx.path, {p["part_id"]: p for p in parts})
        except Exception as e:  # noqa: BLE001
            log.info("part extras not written: %s", e)
    return ProjectParts(version=ctx.n, glb_url=ctx.glb_url, parts=[PartMeta.model_validate(p) for p in parts])


def register(router: APIRouter) -> None:
    @router.get("/projects/{project_id}/parts", response_model=ProjectParts, tags=["parts"])
    def get_parts(project_id: str, version: int | None = None) -> ProjectParts:
        return list_parts(project_id, version)

    @router.post("/projects/{project_id}/parts/{part_id}/edit", response_model=StudioAccepted,
                 status_code=status.HTTP_202_ACCEPTED, tags=["parts"])
    def edit_part(project_id: str, part_id: str, req: PartEditRequest) -> StudioAccepted:
        from api.studio import edit, engine

        runner.get_project(project_id)  # DEMO_READONLY / shared Studio rate limit: api/auth.py (STUDIO_RUN)
        try:
            return StudioAccepted(version=edit.submit(project_id, part_id, req))
        except edit.Invalid as e:
            raise HTTPException(422, str(e)) from None
        except engine.Conflict as e:
            raise HTTPException(409, str(e)) from None


__all__ = ["list_parts", "version_context", "param_spec", "look_of", "Ctx", "ENCLOSURE_SYNC", "register"]
