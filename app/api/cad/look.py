"""Product look: full-assembly GLBs with per-part PBR materials. Owner: W12.

    look = look_for(material, finish)                 # role -> glTF PBR material
    build_assembly(params, path, look, features)      # dN.glb: moulded shells + visible non-moulded parts
    apply_materials(glb_path, look)                   # recolour any GLB whose nodes are labelled by role

The moulded shells (`enclosure.*`, dN.step/stl) stay exactly what DFM measures. dN.glb is the *viewer* model of
the finished product: the same two shells plus parts that are real but not moulded — rubber feet, button, status
light pipe, USB-C port, LED diffuser, stainless bowl — each drawn in build123d and exported with a material taken
from the direction's material / finish / colour. Every node is labelled `<role>.<n>`; the role picks the material.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import threading
from pathlib import Path
from typing import Any

from api.cad.build import BUILD_VERSION, build_shape, normalize, publish

log = logging.getLogger("cad.look")

LOOK_VERSION = "l3"  # bump when assembly geometry or materials change

# name -> sRGB hex. Used when the finish has a colour word but no #hex.
COLOURS = {
    "warm white": "#EDEBE6", "white": "#F2F2EF", "ivory": "#EFE9DC", "cream": "#EFE6D2", "sand": "#D8CFC0",
    "beige": "#D9CDB8", "stone": "#BDB8AE", "light grey": "#C9CACC", "grey": "#9A9DA1", "gray": "#9A9DA1",
    "graphite": "#3A3D42", "charcoal": "#2E3033", "black": "#1C1D1F", "sage": "#9DB09A", "green": "#6E8F6A",
    "olive": "#7A7A55", "blue": "#4F6F95", "navy": "#27344A", "slate": "#5B6570", "teal": "#3E7C7B",
    "terracotta": "#C06A4C", "orange": "#E07A3A", "coral": "#E0795F", "red": "#B8423A", "pink": "#E3B2B0",
    "yellow": "#E8C458", "mustard": "#C9A23E", "silver": "#C8CACD", "champagne": "#D8C8A8", "bronze": "#8C6A48",
}
DEFAULT_PLASTIC = "#EDEBE6"
_HEX = re.compile(r"#([0-9A-Fa-f]{6})\b")


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(hex_: str) -> list[float]:
    h = hex_.lstrip("#")
    return [round(_lin(int(h[i : i + 2], 16) / 255), 4) for i in (0, 2, 4)]


def colour_of(text: str, default: str | None = None) -> str | None:
    """sRGB hex found in a finish/material string: explicit #RRGGBB first, then a colour word."""
    m = _HEX.search(text or "")
    if m:
        return "#" + m.group(1).upper()
    low = (text or "").lower()
    for name in sorted(COLOURS, key=len, reverse=True):
        if re.search(rf"\b{name}\b", low):
            return COLOURS[name]
    return default


def roughness_of(finish: str) -> float:
    f = (finish or "").lower()
    if any(k in f for k in ("mirror", "gloss", "polished", "spi-a", "spi a")):
        return 0.18
    if any(k in f for k in ("spi-b", "semi", "satin")):
        return 0.38
    if "soft-touch" in f or "soft touch" in f or "rubber" in f:
        return 0.78
    if any(k in f for k in ("texture", "mt-", "vdi", "matte", "matt", "bead", "powder", "sand")):
        return 0.62
    return 0.5


def _pbr(rgb: list[float], metallic: float, rough: float, emissive: list[float] | None = None, name: str = "") -> dict:
    return {"name": name, "baseColorFactor": [*rgb, 1.0], "metallicFactor": metallic, "roughnessFactor": rough,
            "emissiveFactor": emissive or [0.0, 0.0, 0.0]}


def _shade(rgb: list[float], k: float) -> list[float]:
    return [round(min(1.0, c * k), 4) for c in rgb]


def look_for(material: str, finish: str, colour: str | None = None) -> dict[str, dict]:
    """Role -> PBR material for a direction. `colour` (sRGB hex) overrides the colour found in the finish."""
    mat = (material or "").lower()
    metal_body = mat.startswith(("alumin", "zinc", "steel", "stainless")) and "+" not in mat
    hex_ = colour or colour_of(finish) or colour_of(material)
    rough = roughness_of(finish)
    if metal_body:
        body = hex_to_linear(hex_ or COLOURS["silver"])
        body_pbr = _pbr(body, 1.0, max(0.28, min(rough, 0.45)), name="anodised aluminium body")
    else:
        body = hex_to_linear(hex_ or DEFAULT_PLASTIC)
        body_pbr = _pbr(body, 0.0, rough, name="moulded body")
    lum = 0.2126 * body[0] + 0.7152 * body[1] + 0.0722 * body[2]
    accent = _shade(body, 0.62) if lum > 0.08 else [min(1.0, c * 1.6 + 0.012) for c in body]
    return {
        "body": body_pbr,
        "accent": {**body_pbr, "name": "lower shell", "baseColorFactor": [*accent, 1.0]},
        "metal": _pbr([0.80, 0.81, 0.83], 1.0, 0.32, name="anodised aluminium"),
        "coat": _pbr(hex_to_linear(colour_of(finish) or "#2E3033"), 0.0, 0.62, name="powder coat"),
        "rubber": _pbr([0.03, 0.03, 0.032], 0.0, 0.92, name="TPE rubber"),
        "diffuser": _pbr([0.93, 0.92, 0.90], 0.0, 0.55, emissive=[1.0, 0.9, 0.74], name="frosted PC diffuser (lit)"),
        "led": _pbr([0.2, 0.7, 0.9], 0.0, 0.3, emissive=[0.25, 0.75, 1.0], name="status light pipe"),
        "button": _pbr(_shade(body, 0.9) if not metal_body else [0.18, 0.18, 0.19], 0.0, min(rough + 0.1, 0.9), name="button"),
        "port": _pbr([0.015, 0.015, 0.016], 0.4, 0.4, name="USB-C port"),
        "steel": _pbr([0.86, 0.86, 0.87], 1.0, 0.24, name="stainless steel 304"),
    }


# --------------------------------------------------------------------------- GLB post-process


def apply_materials(glb_path: Path | str, look: dict[str, dict]) -> None:
    """Give every mesh node the material of its role (node name `<role>.<n>`; unknown role -> body)."""
    from pygltflib import GLTF2, Material, PbrMetallicRoughness

    g = GLTF2.load(str(glb_path))
    index: dict[str, int] = {}
    materials: list[Material] = []

    def mat_for(role: str) -> int:
        if role not in index:
            spec = look[role]
            index[role] = len(materials)
            materials.append(Material(
                name=spec["name"] or role,
                pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=spec["baseColorFactor"],
                                                          metallicFactor=spec["metallicFactor"],
                                                          roughnessFactor=spec["roughnessFactor"]),
                emissiveFactor=spec["emissiveFactor"], doubleSided=False, alphaMode="OPAQUE"))
        return index[role]

    for node in g.nodes:
        if node.mesh is None:
            continue
        role = (node.name or "body").split(".")[0].replace("_shell", "")
        role = {"top": "body", "bottom": "accent"}.get(role, role)
        m = mat_for(role if role in look else "body")
        for prim in g.meshes[node.mesh].primitives:
            prim.material = m
    g.materials = materials
    glb_path = Path(glb_path)
    tmp = glb_path.with_name(f".{glb_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")  # atomic: never serve a half file
    g.save_binary(str(tmp))
    os.replace(tmp, glb_path)


# --------------------------------------------------------------------------- assembly geometry


def features_for(brief) -> set[str]:
    """Visible non-moulded parts implied by the brief (no LLM)."""
    text = " ".join(str(x) for x in [getattr(brief, "category", ""), getattr(brief, "product_name", ""),
                                     getattr(brief, "one_liner", ""), " ".join(getattr(brief, "key_features", []) or [])]).lower()
    f = {"button", "led"}
    small = any(k in text for k in ("track", "wallet", "card", "tag", "wear", "ring", "key", "earbud", "band"))
    if not small:
        f |= {"feet", "port"}
    if any(k in text for k in ("lamp", "light", "lighting")):
        f.add("diffuser")
    if any(k in text for k in ("bowl", "feeder", "food", "water", "dog", "cat", "pet")):
        f.add("bowl")
        f.discard("button")
    return f


def _labelled(shape, role: str, n: int):
    shape.label = f"{role}.{n}"
    return shape


def details(p: dict[str, float], features: set[str]) -> list:
    """Labelled non-moulded parts placed on the shells described by normalized params p."""
    from build123d import Box, Circle, Cone, Cylinder, Pos, RectangleRounded, Rot, extrude, fillet, Axis

    fam, L, W, H = int(p["family"]), p["length"], p["width"], p["height"]
    t = math.tan(math.radians(p["draft_deg"]))
    hb, ht, ef = H * p["split_ratio"], H * (1 - p["split_ratio"]), p["edge_fillet"]
    # flat roof (z = H) and floor (z = 0) half extents, inside the edge fillet
    rl, rw = L / 2 - ht * t - ef, W / 2 - ht * t - ef
    fl, fw = L / 2 - hb * t - ef, W / 2 - hb * t - ef
    if fam == 1:
        rw, fw = rl, fl
    short = min(rl, rw)
    parts, n = [], 0

    def add(shape, role):
        nonlocal n
        n += 1
        parts.append(_labelled(shape, role, n))

    on_top_free = True
    if "bowl" in features and short > 15:
        R = short * 0.86
        D = max(10.0, min(R * 0.42, 50.0))
        th, z0 = 1.2, H + 0.2  # removable bowl resting on the top shell
        outer = Pos(0, 0, z0 + D / 2) * Cone(R * 0.8, R, D)
        inner = Pos(0, 0, z0 + th + D / 2) * Cone(R * 0.8 - th, R - th, D)
        rim = Pos(0, 0, z0 + D - 0.6) * (Cylinder(R + 3.0, 1.2) - Cylinder(R - th, 1.2))
        add(outer - inner + rim, "steel")
        on_top_free = False
    if "diffuser" in features and short > 8:
        prof = Circle(short * 0.72) if fam == 1 else RectangleRounded(rl * 1.6, rw * 1.5, min(rl, rw) * 0.5)
        add(Pos(0, 0, H - 0.2) * extrude(prof, 0.9), "diffuser")
        on_top_free = False
    if "button" in features and short > 6 and on_top_free:
        r = max(2.0, min(short * 0.18, 9.0))
        b = Cylinder(r, 1.2)
        try:
            b = fillet(b.edges().group_by(Axis.Z)[-1], radius=0.5)
        except Exception:  # noqa: BLE001
            pass
        add(Pos(0, 0 if fam == 1 else -rw * 0.4, H + 0.4) * b, "button")
    if "led" in features and short > 5:
        r = max(0.8, min(short * 0.05, 2.2))
        if on_top_free:
            add(Pos(rl * 0.55 if fam != 1 else 0, -rw * 0.45 if fam != 1 else rw * 0.55, H - 0.3) * Cylinder(r, 0.9), "led")
        elif H > 8:  # top is taken: light pipe on the front wall
            y = -(W / 2 - (hb - hb * 0.6) * t)
            add(Pos(0, y, hb * 0.6) * (Rot(90, 0, 0) * Cylinder(r, 1.2)), "led")
    if "port" in features and H > 8 and hb > 6:
        z = hb * 0.5
        x = L / 2 - (hb - z) * t
        port = Box(1.4, 9.0, 3.3)
        try:
            port = fillet(port.edges().filter_by(Axis.X), radius=1.3)
        except Exception:  # noqa: BLE001
            pass
        add(Pos(x - 0.2, 0, z) * port, "port")
    if "feet" in features and min(fl, fw) > 10:
        rf = max(3.0, min(min(fl, fw) * 0.1, 8.0))
        if fam == 1:
            rp = fl - rf * 1.4
            pts = [(rp * math.cos(a), rp * math.sin(a)) for a in (math.pi / 4 + i * math.pi / 2 for i in range(4))]
        else:
            px, py = fl - rf * 1.8, fw - rf * 1.8
            pts = [(px, py), (-px, py), (px, -py), (-px, -py)]
        for x, y in pts:
            add(Pos(x, y, -0.6) * Cylinder(rf, 1.6), "rubber")
    return parts


def shells_labelled(params: dict[str, Any]) -> list:
    _, (bottom, top) = build_shape(params)
    return [_labelled(top, "body", 1), _labelled(bottom, "accent", 1)]


def export_look(parts: list, path: Path | str, look: dict[str, dict]) -> Path:
    """Export labelled parts as one GLB (glTF +Y up, mm) and apply the role materials."""
    from build123d import Compound, export_gltf

    path = Path(path)
    asm = Compound(children=parts)
    asm.label = "product"
    export_gltf(asm, str(path), binary=True, linear_deflection=0.05, angular_deflection=0.2)
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("assembly GLB export produced no file")
    apply_materials(path, look)
    return path


def build_assembly(params: dict[str, Any], path: Path | str, look: dict[str, dict], features: set[str]) -> Path:
    """Full product GLB = shells of `params` + detail parts, cached by (params, features, look) hash."""
    path = Path(path)
    p = normalize(params)
    key = hashlib.sha1(json.dumps({"v": BUILD_VERSION + LOOK_VERSION, "p": p, "f": sorted(features), "l": look},
                                  sort_keys=True).encode()).hexdigest()[:16]
    cache = path.parent / "_cache" / f"asm_{key}.glb"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not (cache.exists() and cache.stat().st_size > 0):
        parts = shells_labelled(p)
        try:
            parts += details(p, features)
        except Exception as e:  # noqa: BLE001 — details are cosmetic; the shells are never dropped
            log.info("assembly details dropped: %s", e)
        export_look(parts, cache, look)
    publish(cache, path)
    return path




_FEATURE_TEXT = {
    "bowl": "a removable brushed stainless-steel bowl seated in a shallow recess on top",
    "diffuser": "a flush frosted light diffuser panel glowing warm white",
    "button": "one small round flush button on top",
    "led": "a tiny cyan status light",
    "port": "a USB-C port on the right side",
    "feet": "small black rubber feet underneath",
}


def describe_features(features: set[str]) -> str:
    """Sentence fragment for the render prompt, listing the same details as the GLB."""
    items = [_FEATURE_TEXT[k] for k in ("bowl", "diffuser", "button", "led", "port", "feet") if k in features]
    return "; details: " + ", ".join(items) if items else ""


__all__ = ["look_for", "colour_of", "apply_materials", "build_assembly", "details", "features_for", "export_look",
           "shells_labelled", "COLOURS", "describe_features"]
