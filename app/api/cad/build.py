"""build123d enclosure generator. Owner: W2.

    build_direction(params, out_dir, name=None) -> {"step": Path, "stl": Path, "glb": Path}

Three generic parametric families share one construction: a two-part moulded shell split at `split_ratio` of
the height. Each half is a tapered extrusion (draft on every vertical wall, widest at the split line so both
halves release along ±Z), hollowed to a real `wall`, with drafted screw bosses in the bottom half.

    family 0 = soft rounded box · 1 = puck (cylinder) · 2 = slim slab

Parameters (mm / deg, all floats so they fit DesignDirection.cad_parameters):
    family, length, width, height, fillet (footprint corner radius), edge_fillet (outer floor/roof edge),
    wall, draft_deg, split_ratio, boss_count

Builds are cached by parameter hash under <out_dir>/_cache/, then copied to <name>.{step,stl,glb}.
If an optional feature (edge fillet, bosses) crashes OCCT on a given shape, it is dropped — never the build.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import shutil
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("cad.build")

FAMILIES = {0: "rounded_box", 1: "puck", 2: "slab"}
FAMILY_CODES = {v: k for k, v in FAMILIES.items()}

DEFAULTS: dict[str, float] = {
    "family": 0.0,
    "length": 100.0,
    "width": 70.0,
    "height": 30.0,
    "fillet": 12.0,
    "edge_fillet": 3.0,
    "wall": 2.0,
    "draft_deg": 1.5,
    "split_ratio": 0.6,
    "boss_count": 4.0,
}
BUILD_VERSION = "v1"  # bump to invalidate caches when the geometry code changes

API_DIR = Path(__file__).resolve().parent.parent
PREBUILT_DIR = Path(__file__).resolve().parent / "prebuilt"


def files_root() -> Path:
    """Generated files live in api/data/files/<project_id>/ (override with FILES_DIR, e.g. in tests)."""
    return Path(os.getenv("FILES_DIR") or (API_DIR / "data" / "files"))


def project_dir(project_id: str) -> Path:
    d = files_root() / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- parameters


def normalize(params: dict[str, Any]) -> dict[str, float]:
    """Fill defaults and clamp to buildable ranges. Pure function, no CAD."""
    p = {**DEFAULTS, **{k: float(v) for k, v in params.items() if k in DEFAULTS and v is not None}}
    fam = int(round(p["family"]))
    p["family"] = float(fam if fam in FAMILIES else 0)
    p["wall"] = _clamp(p["wall"], 1.2, 4.0)
    p["draft_deg"] = _clamp(p["draft_deg"], 0.0, 5.0)
    p["length"] = _clamp(p["length"], 20.0, 400.0)
    p["width"] = _clamp(p["width"], 15.0, 400.0)
    if p["family"] == 1:  # puck: circular footprint
        p["width"] = p["length"]
    min_h = 4 * p["wall"] + 1.0
    p["height"] = _clamp(p["height"], min_h, 400.0)
    p["split_ratio"] = _clamp(p["split_ratio"], 0.3, 0.8)
    short = min(p["length"], p["width"])
    p["fillet"] = _clamp(p["fillet"], 0.0, short / 2 - 0.5)
    p["edge_fillet"] = _clamp(p["edge_fillet"], 0.0, min(p["height"] * p["split_ratio"], p["height"] * (1 - p["split_ratio"])) / 2)
    p["boss_count"] = float(int(_clamp(round(p["boss_count"]), 0, 4)))
    return {k: round(v, 3) for k, v in p.items()}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def params_hash(params: dict[str, Any]) -> str:
    p = normalize(params)
    blob = json.dumps({"v": BUILD_VERSION, **p}, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- geometry


def _footprint(family: int, length: float, width: float, radius: float):
    from build123d import Circle, Rectangle, RectangleRounded

    if family == 1:
        return Circle(length / 2)
    if radius <= 0.05:
        return Rectangle(length, width)
    return RectangleRounded(length, width, min(radius, min(length, width) / 2 - 0.01))


def _shell_half(family: int, length: float, width: float, radius: float, h: float, wall: float, draft: float,
                edge_fillet: float, bosses: int):
    """One moulded half: floor at z=0 (narrow), opening at z=h (widest = length × width). Pull axis +Z."""
    from build123d import Cone, Location, Pos, extrude, fillet

    t = math.tan(math.radians(draft))
    shrink = 2 * h * t  # floor is smaller than the opening by 2·h·tan(draft)
    fl, fw, fr = length - shrink, width - shrink, max(radius - h * t, 0.0)
    outer = extrude(_footprint(family, fl, fw, fr), amount=h, taper=-draft)
    if edge_fillet > 0.2:
        try:
            outer = fillet(outer.edges().group_by()[0], radius=edge_fillet)
        except Exception as e:  # noqa: BLE001 — optional cosmetic feature
            log.info("edge fillet dropped: %s", e)

    # inner cavity: outer section at z=wall, offset inward by the wall measured normal to the drafted face
    inset = wall / math.cos(math.radians(draft)) - wall * t
    il, iw, ir = fl - 2 * inset, fw - 2 * inset, max(fr - inset, 0.0)
    cavity_h = h - wall + 1.0
    cavity = extrude(_footprint(family, il, iw, ir), amount=cavity_h, taper=-draft).moved(Location((0, 0, wall)))
    inner_fillet = max(edge_fillet - wall, 0.0)
    if inner_fillet > 0.2:
        try:
            cavity = fillet(cavity.edges().group_by()[0], radius=inner_fillet)
        except Exception as e:  # noqa: BLE001
            log.info("inner fillet dropped: %s", e)
    part = outer - cavity

    boss_h = min(h - wall - 1.0, 20.0)
    if bosses and boss_h >= 2.5:
        boss_r, hole_r = 2.5, 1.1  # M2.5 self-tapping pilot; boss OD ≈ 2× hole Ø
        m = wall + boss_r + 1.0
        pts = _boss_points(family, il + 2 * wall, iw + 2 * wall, ir + wall, m, bosses)
        try:
            for x, y in pts:
                boss = Cone(boss_r, boss_r - boss_h * t, boss_h + 0.5).moved(Pos(x, y, wall - 0.5 + (boss_h + 0.5) / 2))
                hole = Cone(hole_r, hole_r + boss_h * t, boss_h).moved(Pos(x, y, wall + 0.5 + boss_h / 2))
                part = (part + boss) - hole
        except Exception as e:  # noqa: BLE001
            log.info("bosses dropped: %s", e)
    return part


def _boss_points(family: int, length: float, width: float, radius: float, m: float, n: int) -> list[tuple[float, float]]:
    if family == 1:
        r = length / 2 - m
        return [(r * math.cos(a), r * math.sin(a)) for a in [math.pi / 4 + i * math.pi / 2 for i in range(n)]]
    if radius > m:
        px = length / 2 - radius + (radius - m) / math.sqrt(2)
        py = width / 2 - radius + (radius - m) / math.sqrt(2)
    else:
        px, py = length / 2 - m, width / 2 - m
    corners = [(px, py), (-px, -py), (-px, py), (px, -py)]
    return corners[:n] if px > 0 and py > 0 else []


def build_shape(params: dict[str, Any]):
    """Return (assembly Compound, [bottom Solid-ish Part, top Part]) for normalized params."""
    from build123d import Compound, Location, Plane

    p = normalize(params)
    fam = int(p["family"])
    L, W, H, wall, d = p["length"], p["width"], p["height"], p["wall"], p["draft_deg"]
    hb = round(H * p["split_ratio"], 3)
    ht = H - hb
    bottom = _shell_half(fam, L, W, p["fillet"], hb, wall, d, p["edge_fillet"], int(p["boss_count"]))
    top = _shell_half(fam, L, W, p["fillet"], ht, wall, d, p["edge_fillet"], 0)
    top = top.mirror(Plane.XY).moved(Location((0, 0, H)))
    bottom.label, top.label = "bottom_shell", "top_shell"
    return Compound(children=[bottom, top]), [bottom, top]


def export_all(shape, stem: Path) -> dict[str, Path]:
    from build123d import export_gltf, export_step, export_stl

    out = {"step": stem.with_suffix(".step"), "stl": stem.with_suffix(".stl"), "glb": stem.with_suffix(".glb")}
    export_step(shape, str(out["step"]))
    export_stl(shape, str(out["stl"]), tolerance=0.05, angular_tolerance=0.2)
    export_gltf(shape, str(out["glb"]), binary=True, linear_deflection=0.05, angular_deflection=0.2)
    for k, f in out.items():
        if not f.exists() or f.stat().st_size == 0:
            raise RuntimeError(f"export {k} produced no file")
    return out


def publish(src: Path | str, dst: Path | str) -> Path:
    """Atomically put a copy of `src` at `dst` (temp file + rename): a concurrent GET /files never sees a half-written
    or truncated file (a length mismatch there can leave a proxied browser request hanging)."""
    dst = Path(dst)
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}.{threading.get_ident()}.tmp")  # leading dot: never served
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    return dst


def build_direction(params: dict[str, Any], out_dir: Path | str, name: str | None = None) -> dict[str, Path]:
    """Build (or reuse from cache) the enclosure for `params`; copy it to <out_dir>/<name>.{step,stl,glb}."""
    out_dir = Path(out_dir)
    cache = out_dir / "_cache"
    cache.mkdir(parents=True, exist_ok=True)
    h = params_hash(params)
    stem = cache / h
    files = {k: stem.with_suffix("." + k) for k in ("step", "stl", "glb")}
    if not all(f.exists() and f.stat().st_size > 0 for f in files.values()):
        shape, _ = build_shape(params)
        files = export_all(shape, stem)
        (cache / f"{h}.json").write_text(json.dumps(normalize(params), indent=1))
    if not name:
        return files
    named = {}
    for k, f in files.items():
        dst = out_dir / f"{name}.{k}"
        named[k] = publish(f, dst)
    return named


def shape_facts(step_path: Path | str) -> dict[str, Any]:
    """Bounding box (mm), volume (mm³) and per-solid boxes of a STEP file — for the spec (Measured)."""
    from build123d import import_step

    shape = import_step(str(step_path))
    bb = shape.bounding_box()
    solids = shape.solids()
    return {
        "size": (bb.size.X, bb.size.Y, bb.size.Z),
        "volume_mm3": sum(abs(s.volume) for s in solids),
        "solids": [
            {"size": (s.bounding_box().size.X, s.bounding_box().size.Y, s.bounding_box().size.Z), "volume_mm3": abs(s.volume)}
            for s in solids
        ],
    }
