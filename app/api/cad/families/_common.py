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
import os
import threading
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
}
for _k, _v in EXTRA_ROLES.items():
    _v.setdefault("emissiveFactor", [0.0, 0.0, 0.0])

ROLES = ("body", "accent", "metal", "coat", "rubber", "diffuser", "led", "button", "port", "steel", *EXTRA_ROLES)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def family_look(colour: str | None = None, finish: str = "", material: str = "pc_abs") -> dict[str, dict]:
    """Role -> glTF PBR material: look.py's roles (body in `colour`) plus the family roles."""
    from api.cad.look import look_for

    return {**look_for(material, finish, colour), **{k: dict(v) for k, v in EXTRA_ROLES.items()}}


def apply_look(glb_path: Path | str, look: dict[str, dict]) -> None:
    """Material per node role (`<role>.<n>`, unknown -> body). Like look.apply_materials, plus alpha blending."""
    from pygltflib import GLTF2, Material, PbrMetallicRoughness

    g = GLTF2.load(str(glb_path))
    index: dict[str, int] = {}
    materials: list = []
    for node in g.nodes:
        if node.mesh is None:
            continue
        role = (node.name or "body").split(".")[0]
        role = role if role in look else "body"
        if role not in index:
            spec = look[role]
            alpha = spec["baseColorFactor"][3]
            index[role] = len(materials)
            materials.append(Material(
                name=spec.get("name") or role,
                pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=spec["baseColorFactor"],
                                                          metallicFactor=spec["metallicFactor"],
                                                          roughnessFactor=spec["roughnessFactor"]),
                emissiveFactor=spec.get("emissiveFactor", [0.0, 0.0, 0.0]), doubleSided=alpha < 1.0,
                alphaMode="BLEND" if alpha < 1.0 else "OPAQUE"))
        for prim in g.meshes[node.mesh].primitives:
            prim.material = index[role]
    g.materials = materials
    glb_path = Path(glb_path)
    tmp = glb_path.with_name(f".{glb_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    g.save_binary(str(tmp))
    os.replace(tmp, glb_path)


def export_parts(parts: list, stem: Path | str, look: dict[str, dict] | None = None) -> dict[str, Path]:
    """Labelled parts -> <stem>.step / .stl / .glb (GLB with per-role materials)."""
    from build123d import Compound

    from api.cad.build import export_all

    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    asm = Compound(children=parts)
    asm.label = "product"
    out = export_all(asm, stem)
    apply_look(out["glb"], look or family_look())
    return out


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


def geometry_source(module) -> str:
    src = inspect.getsource(module)
    a, b = src.index(START), src.index(END)
    return src[a + len(START):b].strip("\n") + "\n"


def seed_code(module, params: dict[str, float]) -> str:
    """Stand-alone build123d program for a family: parameters + geometry + `build()`. Runs in the codegen sandbox."""
    lines = ",\n".join(f"    {k!r}: {round(float(v), 3)!r}" for k, v in params.items())
    return (f'"""{module.DESCRIPTION} Seed: parametric family `{module.NAME}`. Units mm, Z up, product on z=0."""\n'
            f"import math\n\nfrom build123d import *\n\nP = {{\n{lines},\n}}\n\n"
            f"{geometry_source(module)}\n\ndef build():\n    return build_parts(P)\n")
