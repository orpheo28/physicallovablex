"""Studio CAD (W21): the AI CAD model (text-to-CAD) of a version, and rebuilds of product-family versions.

    enabled() -> bool                       # CODEGEN_ENABLED (default 1) and an LLM key: AI CAD is written by the LLM
    generate(pid, arts) -> result           # new AI model for a version's product (Studio start, background)
    edit(pid, k, instruction, arts)         # edit AI model k (refine: geometry beyond parameters), Cursor-style
    family_code(pid, arts) -> result|None   # families-only mode: the family's seed program becomes the version's code
    ai_entries(pid, res) -> [CadFile]       # AI glb / step / py entries of stage 3 (AI model first)
    attach(spec, entries) / split(cad_files) / current_model(spec) -> k
    recolour(pid, n, spec, direction)       # colour / material change: recoloured copy of the AI GLB (v<n>_ai.glb)
    rebuild_family(pid, n, design, spec, asked) -> notes   # family version files v<n>.*, v<n>_enclosure.*

The AI model never replaces the measured product the pipeline runs on (DFM, weight, costs use the family / enclosure
CAD); it is the model shown first, with its program (`code_url`) and its own measured bbox.
"""

from __future__ import annotations

import json
import logging
import os
import re

from api.cad import family_mode
from api.cad.build import build_direction, normalize, project_dir, publish, shape_facts
from api.cad.codegen.engine import FALLBACK_LABEL, LABEL
from contracts.artifacts import CadFile, Dimensions, LabeledValue, ProcessType

log = logging.getLogger("studio.cad")

GEO_OPS = ("regenerate_geometry", "set_shape_family", "set_dimensions")
FULL = "Full product — materials"
_SRC = re.compile(r"\(([^()]*)\)\s*$")


def enabled() -> bool:
    """AI CAD on: CODEGEN_ENABLED not 0 and an LLM configured for the "main" route."""
    from api.llm import is_configured

    return os.getenv("CODEGEN_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off") and is_configured("main")


# --------------------------------------------------------------------------- stage-3 entries


def is_ai(f: CadFile) -> bool:
    return bool(f.description) and (f.description.startswith(LABEL) or (f.format == "py" and f.description.startswith(FALLBACK_LABEL)))


def split(cad_files: list[CadFile]) -> tuple[list[CadFile], list[CadFile]]:
    ai = [f for f in cad_files if is_ai(f)]
    return ai, [f for f in cad_files if not is_ai(f)]


def attach(spec, entries: list[CadFile]) -> None:
    """AI entries first (the viewer default), then the product / DFM files."""
    _, rest = split(spec.cad_files)
    spec.cad_files = list(entries) + rest


def current_model(spec) -> int | None:
    """Program version k of the spec's AI-written model (None: no AI model; the family seed code does not count)."""
    for f in spec.cad_files if spec is not None else []:
        if f.format == "py" and f.description and f.description.startswith(LABEL):
            m = re.search(r"/cad/code/(\d+)$", f.url)
            return int(m.group(1)) if m else None
    return None


def source_of(f: CadFile) -> str | None:
    m = _SRC.search(f.description or "")
    return m.group(1) if m else None


def ai_entries(pid: str, res: dict) -> list[CadFile]:
    """Entries for a generate_cad / refine_cad result: an AI model (ok / repaired / edit kept) → glb + step + py; a
    family fallback → only the program (the family model already is the viewer model)."""
    if not res or res.get("status") == "failed":
        return []
    k = res["version"]
    ai = res.get("label") == LABEL
    bb = res.get("bbox_mm") or [0, 0, 0]
    size = lambda p: os.path.getsize(p) if p and os.path.exists(p) else None  # noqa: E731
    out: list[CadFile] = []
    if ai:
        files = res.get("files") or {}
        out.append(CadFile(format="glb", url=f"/files/{pid}/model_v{k}.glb", size_bytes=size(files.get("glb")),
                           description=f"{LABEL} — bbox {bb[0]:.0f} × {bb[1]:.0f} × {bb[2]:.0f} mm"))
        out.append(CadFile(format="step", url=f"/files/{pid}/model_v{k}.step", size_bytes=size(files.get("step")),
                           description=f"{LABEL} — STEP AP214"))
    if res.get("code"):
        out.append(CadFile(format="py", url=f"/projects/{pid}/cad/code/{k}", size_bytes=len(res["code"].encode()),
                           description=f"{res.get('label') or FALLBACK_LABEL} — build123d program v{k} ({res.get('source')})"))
    return out


def _brief_text(brief, design) -> tuple[str, str]:
    from api.studio import product as P

    d = P.chosen(design)
    req = []
    if brief is not None:
        req += list(brief.key_features or []) + list(brief.constraints or [])
    if d is not None:
        req += [f"Design direction '{d.name}': {d.description}", f"Material: {d.material}", f"Finish: {d.finish}"]
    return brief, "; ".join(req)


def _look(design) -> dict:
    from api.studio import product as P

    d = P.chosen(design)
    fin, _, hex_ = P.split_finish(d.finish)
    return {"colour": hex_, "material": P.material_key(d.material), "finish": fin}


def _seed(arts) -> tuple[str | None, dict | None, object]:
    from api.studio import product as P

    d = P.chosen(arts.get(2))
    fam = family_mode.family_of(d) if d is not None else None
    return fam, (family_mode.fparams(d) if fam else None), d


def generate(pid: str, arts: dict, llm=None) -> dict:
    """New AI model for this product. Family products start from their family program with the chosen direction's
    parameters; wearables / generic devices from the conventions example with the pod size in the requirements."""
    from api.cad.codegen import generate_cad
    from api.cad.codegen.classify import classify
    from api.cad.build import FAMILIES

    brief, spec = arts.get(1), arts.get(3)
    _, req = _brief_text(brief, arts.get(2))
    fam, fparams, d = _seed(arts)
    dims = None
    if spec is not None:
        od = spec.overall_dimensions
        L, W, H = od.length.value, od.width.value, od.height.value
        w17 = FAMILIES.get(int((d.cad_parameters or {}).get("family", 0))) if d is not None and not fam else None
        if w17 in ("wearable_band", "ring"):
            req += f"; the sensor pod measures {L:.1f} × {W:.1f} × {H:.1f} mm (L × W × thickness)" + (
                "; draw the strap looping under the pod" if w17 == "wearable_band" else "; it is a ring worn on a finger")
        else:
            dims = (L, W, H)
    text = " ".join(str(x) for x in [getattr(brief, "product_name", ""), getattr(brief, "one_liner", ""), req])
    cat = classify(text)
    return generate_cad(brief, requirements=req, category=cat, seed_family=fam, seed_params=fparams, project_id=pid,
                        dims=dims, llm=llm, **_look(arts.get(2)))


def edit(pid: str, k: int, instruction: str, arts: dict, llm=None) -> dict:
    from api.cad.codegen import refine_cad

    return refine_cad(pid, instruction, version=k, dims=None, llm=llm, **_look(arts.get(2)))


def family_code(pid: str, arts: dict) -> dict | None:
    """Families-only mode (CODEGEN_ENABLED=0 or no LLM): record the family's parametric program as the version's code
    (model_v<k>.py, label FALLBACK_LABEL, source seed:<family>). No sandbox run: the family model is already built."""
    from api.cad import families
    from api.cad.codegen.engine import _next_version

    fam, fparams, _ = _seed(arts)
    if not fam:
        return None
    out = project_dir(pid)
    k = _next_version(out)
    code = families.seed_code_for(fam, fparams)
    (out / f"model_v{k}.py").write_text(code, encoding="utf-8")
    meta = {"status": "fallback", "version": k, "source": f"seed:{fam}", "label": FALLBACK_LABEL, "category": fam,
            "seed_family": fam, "notes": ["AI CAD is off (CODEGEN_ENABLED=0 or no LLM key): parametric family program"]}
    (out / f"model_v{k}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return {**meta, "code": code, "code_url": f"/projects/{pid}/cad/code/{k}", "files": {}}


def recolour(pid: str, n: int, spec, direction) -> None:
    """Colour / material changed: the AI GLB gets a recoloured copy for version n (programs and STEP are unchanged)."""
    from api.cad.families import apply_look, family_look
    from api.studio import product as P

    ai, rest = split(spec.cad_files)
    glb = next((f for f in ai if f.format == "glb"), None)
    if glb is None:
        return
    src = project_dir(pid) / glb.url.rsplit("/", 1)[-1]
    if not src.exists():
        return
    dst = project_dir(pid) / f"v{n}_ai.glb"
    publish(src, dst)
    fin, _, hex_ = P.split_finish(direction.finish)
    apply_look(dst, family_look(hex_, fin, P.material_key(direction.material)))
    glb.url, glb.size_bytes = f"/files/{pid}/v{n}_ai.glb", dst.stat().st_size
    spec.cad_files = ai + rest


# --------------------------------------------------------------------------- product-family versions


def _mm(v: float, check: str) -> LabeledValue:
    return LabeledValue(value=round(v, 2), unit="mm", label="measured", source_or_assumption=check)


def _dims(size, check: str) -> Dimensions:
    return Dimensions(length=_mm(size[0], check), width=_mm(size[1], check), height=_mm(size[2], check))


def rebuild_family(pid: str, n: int, design, spec, asked: dict[str, float]) -> list[str]:
    """Version n of a family product: v<n>.{glb,step,stl} (full product, colour of the direction), v<n>_enclosure.*
    (moulded housing for shell products, the product itself for solid ones), direction + spec updated in place.
    `asked`: overall dimensions the founder gave (mm) → a per-axis scale of the family CAD (0.5-2×). Returns notes."""
    from api.cad.look import apply_materials, look_for
    from api.studio import product as P

    d = P.chosen(design)
    fam = family_mode.family_of(d)
    notes: list[str] = []
    scale = list(family_mode.scale_of(d) or (1.0, 1.0, 1.0))
    od = spec.overall_dimensions
    cur = (od.length.value, od.width.value, od.height.value)
    for i, ax in enumerate(("length", "width", "height")):
        if ax in asked and cur[i] > 0:
            f = asked[ax] / cur[i]
            fc = max(0.5, min(2.0, f))
            if abs(fc - f) > 1e-3:
                notes.append(f"{ax.capitalize()} {asked[ax]:g} mm is more than 2× away from the current {cur[i]:.0f} mm: built at {cur[i] * fc:.0f} mm")
            scale[i] *= fc
    s = tuple(round(x, 4) for x in scale) if any(abs(x - 1) > 1e-6 for x in scale) else None
    P_ = family_mode.fparams(d)
    density = (d.cad_parameters or {}).get("density_g_cm3")
    pdir = project_dir(pid)
    res = family_mode.export_product(pid, fam, f"v{n}", colour=P.split_finish(d.finish)[2], params=P_, scale=s)
    measured = res["measured"]
    bbox = measured["bbox_mm"]
    d.cad_parameters = family_mode.pack(fam, P_, bbox, density=density, scale=s)
    if s and fam not in family_mode.SOLID:  # the moulded housing follows the product scale
        hp = dict(d.cad_parameters)
        for k, f in zip(("length", "width", "height"), s):
            hp[k] = hp[k] * f
        d.cad_parameters.update({k: v for k, v in normalize(hp).items()})
    d.glb_url = f"/files/{pid}/v{n}.glb"
    note = "Bounding box of the built family CAD (build123d/OCCT)"
    d.dimensions = Dimensions(length=_mm(bbox[0], note), width=_mm(bbox[1], note), height=_mm(bbox[2], note))
    spec.overall_dimensions = _dims(bbox, "Bounding box of the full product (family CAD, build123d/OCCT)")
    size = lambda f: f.stat().st_size  # noqa: E731
    full = [CadFile(format="glb", url=d.glb_url, description=FULL, size_bytes=size(res["files"]["glb"]))]
    if fam in family_mode.SOLID:
        enc = family_mode.export_product(pid, fam, f"v{n}_enclosure", colour=P.split_finish(d.finish)[2], params=P_, scale=s,
                                         context=False)
        spec.weight = family_mode.solid_weight(fam, enc["measured"])
        spec.parts = family_mode.spec_parts(fam, enc["measured"])
        f = enc["files"]
        spec.cad_files = full + [
            CadFile(format="step", url=f"/files/{pid}/v{n}_enclosure.step", description="Product — all parts (solid bodies), STEP AP214", size_bytes=size(f["step"])),
            CadFile(format="stl", url=f"/files/{pid}/v{n}_enclosure.stl", description="Product — mesh", size_bytes=size(f["stl"])),
            CadFile(format="glb", url=f"/files/{pid}/v{n}_enclosure.glb", description="Product — viewer model", size_bytes=size(f["glb"])),
        ]
        return notes
    params = normalize(d.cad_parameters)
    files = build_direction(params, pdir)
    stems = {k: pdir / f"v{n}_enclosure.{k}" for k in ("step", "stl", "glb")}
    for k, dst in stems.items():
        publish(files[k], dst)
    try:
        apply_materials(stems["glb"], look_for(d.material, d.finish))
    except Exception as e:  # noqa: BLE001
        log.info("enclosure materials skipped: %s", e)
    facts = shape_facts(stems["step"])
    dens = density or 1.15
    vol = facts["volume_mm3"] / 1000.0
    spec.weight = LabeledValue(value=round(vol * dens, 1), unit="g", label="estimate",
                               source_or_assumption=f"Enclosure volume {vol:.1f} cm³ (measured) × {d.material.split(' (')[0]} {dens} g/cm³; electronics and battery not included")
    shells = {"Bottom shell": 0, "Top shell": 1}
    check = "Bounding box of the built STEP (build123d/OCCT), this part"
    for p in spec.parts:
        if p.name in shells and shells[p.name] < len(facts["solids"]):
            p.dimensions = _dims(facts["solids"][shells[p.name]]["size"], check)
            p.material, p.finish = d.material, d.finish
            p.process_hint = ProcessType.cnc if dens > 2 else ProcessType.injection_molding
    spec.cad_files = full + [
        CadFile(format="step", url=f"/files/{pid}/v{n}_enclosure.step", description="Moulded parts (DFM) — both shells, STEP AP214", size_bytes=size(stems["step"])),
        CadFile(format="stl", url=f"/files/{pid}/v{n}_enclosure.stl", description="Moulded parts (DFM) — mesh for 3D printing", size_bytes=size(stems["stl"])),
        CadFile(format="glb", url=f"/files/{pid}/v{n}_enclosure.glb", description="Moulded parts (DFM) — viewer model", size_bytes=size(stems["glb"])),
        CadFile(format="step", url=f"/files/{pid}/v{n}.step", description="Full product — all parts, STEP AP214", size_bytes=size(res["files"]["step"])),
    ]
    return notes


def solid_measured(direction, part_id: str | None):
    """Stage-4 measured issues of a solid family product (board / furniture / PV array)."""
    fam = family_mode.family_of(direction)
    extra = {"section_mm": family_mode.board_section_mm(direction)} if fam == "board" else None
    return family_mode.solid_issues(fam, family_mode.measured_parts(direction), part_id, extra)


__all__ = ["enabled", "generate", "edit", "family_code", "ai_entries", "attach", "split", "current_model", "recolour",
           "rebuild_family", "solid_measured", "is_ai", "source_of", "GEO_OPS"]
