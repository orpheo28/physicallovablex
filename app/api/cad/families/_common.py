"""Shared helpers for the product families (W19): look (per-role PBR materials), export, measure, seed code.

Every family module has the same shape:

    NAME, CATEGORY, DESCRIPTION           # registry metadata
    @dataclass Params(...).clamped()      # plausible ranges, all floats (fit DesignDirection.cad_parameters)
    # === GEOMETRY ===  ...  # === END GEOMETRY ===
                                          # build123d + math only: `build_parts(P: dict) -> list[labelled parts]`.
                                          # This block is also the seed code the codegen LLM starts from, and it
                                          # runs unchanged in the codegen sandbox.

Parts are labelled `<role>.<n>`; the role picks the material (look.py roles + the extra roles below).
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

# extra roles on top of api.cad.look.look_for (body, accent, metal, coat, rubber, diffuser, led, button, port, steel)
EXTRA_ROLES: dict[str, dict] = {
    "wood": {"name": "oiled beech", "baseColorFactor": [0.52, 0.34, 0.19, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.6},
    "fabric": {"name": "wipe-clean foam pad", "baseColorFactor": [0.78, 0.74, 0.68, 1.0], "metallicFactor": 0.0,
               "roughnessFactor": 0.95},
    "clear": {"name": "clear polycarbonate", "baseColorFactor": [0.75, 0.78, 0.82, 0.35], "metallicFactor": 0.0,
              "roughnessFactor": 0.08},
    "glass": {"name": "dark glass / display", "baseColorFactor": [0.01, 0.012, 0.016, 1.0], "metallicFactor": 0.0,
              "roughnessFactor": 0.06},
    "cell": {"name": "monocrystalline PV cells under glass", "baseColorFactor": [0.012, 0.02, 0.05, 1.0],
             "metallicFactor": 0.35, "roughnessFactor": 0.12},
    "fin": {"name": "fibreglass fin", "baseColorFactor": [0.05, 0.06, 0.07, 0.85], "metallicFactor": 0.0,
            "roughnessFactor": 0.25},
    "roof": {"name": "roof tiles", "baseColorFactor": [0.12, 0.10, 0.09, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.85},
    "wall": {"name": "rendered wall", "baseColorFactor": [0.80, 0.78, 0.74, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.9},
    # C1 (CAD_DETAIL_LEVEL=pro): heat-set inserts / tripod socket, beech dowels
    "brass": {"name": "brass (heat-set insert)", "baseColorFactor": [0.78, 0.60, 0.26, 1.0], "metallicFactor": 1.0,
              "roughnessFactor": 0.3},
    "hardwood": {"name": "fluted beech dowel", "baseColorFactor": [0.74, 0.58, 0.40, 1.0], "metallicFactor": 0.0,
                 "roughnessFactor": 0.7},
}
for _k, _v in EXTRA_ROLES.items():
    _v.setdefault("emissiveFactor", [0.0, 0.0, 0.0])

ROLES = ("body", "accent", "metal", "coat", "rubber", "diffuser", "led", "button", "port", "steel", *EXTRA_ROLES)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def family_look(colour: str | None = None, finish: str = "", material: str = "pc_abs") -> dict[str, dict]:
    """Role -> glTF PBR material: look.py's roles (body in `colour`) plus the family roles."""
    from api.cad.look import look_for
    from api.cad.parts import PART_MATERIALS

    look = {**look_for(material, finish, colour), **{k: dict(v) for k, v in EXTRA_ROLES.items()}}
    if material in PART_MATERIALS:  # a Studio material key: the human wording goes to the part extras (W29)
        look["_meta"] = {**look["_meta"], "material_text": PART_MATERIALS[material]["name"]}
    return look


def apply_look(glb_path: Path | str, look: dict[str, dict], names: dict | None = None, overrides: dict | None = None) -> None:
    """Finish the GLB with the family look (api.cad.glb.finalize: named part nodes, role materials + KHR extensions,
    transmission instead of alpha for clear parts). Idempotent: a finished GLB is recoloured (part ids kept)."""
    from api.cad import glb

    glb.finalize(glb_path, look, names=names, overrides=overrides)


def export_parts(parts: list, stem: Path | str, look: dict[str, dict] | None = None, names: dict | None = None) -> dict[str, Path]:
    """Labelled parts -> <stem>.step / .stl / .glb (GLB with per-role materials; `names`: label → part info, W29)."""
    from build123d import Compound

    from api.cad.build import export_all

    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    asm = Compound(children=parts)
    asm.label = "product"
    hw = hardware_names(parts)  # C1: standard parts (pro detail) → named nodes + BOM extras; {} at basic
    if hw:
        names = {**(names or {}), **hw}
    out = export_all(asm, stem)
    apply_look(out["glb"], look or family_look(), names=names)
    if hw:
        stamp_hardware(out["glb"], hw)
    return out


def hardware_names(parts: list) -> dict[str, dict]:
    if not any(getattr(p, "std_meta", None) for p in parts):
        return {}
    from api.cad.stdparts.bom import hardware_names as names_of

    return names_of(parts)


def stamp_hardware(glb_path: Path | str, hw: dict[str, dict]) -> None:
    """Standard parts in a finished GLB: PartMeta fields on their nodes (bom_item_id, unit_price Estimate, material,
    package = standard + size) and the full facts (standard, size, count, DFM rule…) in root extras `stdparts`."""
    from pygltflib import GLTF2

    from api.cad import glb
    from api.cad.stdparts.bom import node_extras, root_facts

    by_pid = {info["part_id"]: info for info in hw.values()}
    g = GLTF2.load(str(glb_path))
    facts = {}
    for n in g.nodes:
        info = by_pid.get(n.extras.get("part_id")) if isinstance(n.extras, dict) else None
        if info:
            n.extras = {**n.extras, **node_extras(info)}
            facts[info["part_id"]] = root_facts(info)
    root = g.nodes[g.scenes[g.scene or 0].nodes[0]]
    root.extras = {**(root.extras if isinstance(root.extras, dict) else {}), "detail_level": "pro", "stdparts": facts}
    glb._atomic_save(g, Path(glb_path))


def measure_parts(parts: list) -> dict[str, Any]:
    """Measured facts of the built geometry: overall bbox (mm), total solid volume (mm³), per part."""
    from build123d import Compound

    bb = Compound(children=parts).bounding_box()
    rows = []
    for p in parts:
        b = p.bounding_box()
        rows.append({"label": p.label or "", "role": (p.label or "body").split(".")[0],
                     "bbox_mm": [round(b.size.X, 2), round(b.size.Y, 2), round(b.size.Z, 2)],
                     "volume_mm3": round(sum(abs(s.volume) for s in p.solids()), 1)})
    return {"bbox_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
            "volume_mm3": round(sum(r["volume_mm3"] for r in rows), 1), "parts": rows}


START, END = "# === GEOMETRY ===", "# === END GEOMETRY ==="
PRO_START, PRO_END = "# === PRO DETAIL ===", "# === END PRO DETAIL ==="


def geometry_source(module) -> str:
    src = inspect.getsource(module)
    a, b = src.index(START), src.index(END)
    return src[a + len(START):b].strip("\n") + "\n"


def pro_source(module) -> str | None:
    """The family's CAD_DETAIL_LEVEL=pro block (`pro_details(P, parts)`), or None."""
    src = inspect.getsource(module)
    if PRO_START not in src:
        return None
    a, b = src.index(PRO_START), src.index(PRO_END)
    return src[a + len(PRO_START):b].strip("\n") + "\n"


def seed_code(module, params: dict[str, float], level: str | None = None) -> str:
    """Stand-alone build123d program for a family: parameters + geometry + `build()`. Runs in the codegen sandbox.
    At CAD_DETAIL_LEVEL=pro the family's pro block (standard parts from api.cad.stdparts) is appended."""
    from api.cad.stdparts.level import is_pro

    lines = ",\n".join(f"    {k!r}: {round(float(v), 3)!r}" for k, v in params.items())
    pro = pro_source(module) if is_pro(level) else None
    body = (f"{geometry_source(module)}\n\n{pro}\n\ndef build():\n    return pro_details(P, build_parts(P))\n" if pro
            else f"{geometry_source(module)}\n\ndef build():\n    return build_parts(P)\n")
    return (f'"""{module.DESCRIPTION} Seed: parametric family `{module.NAME}`. Units mm, Z up, product on z=0."""\n'
            f"import math\n\nfrom build123d import *\n\nP = {{\n{lines},\n}}\n\n{body}")


def with_detail(pro_details, P: dict, parts: list, level: str | None = None) -> list:
    """C1: the family parts plus its pro details when CAD_DETAIL_LEVEL=pro (basic: `parts` unchanged)."""
    from api.cad.stdparts.level import is_pro

    return pro_details(P, parts) if is_pro(level) else parts
