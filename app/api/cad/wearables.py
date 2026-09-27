"""Wearable shape families (W17): 3 = wearable_band (sensor pod on a strap), 4 = ring (band with a sensor bump).

    normalize_family(p, raw) -> p            # clamp to plausible wearable ranges (called by build.normalize)
    build_shape(p) -> (Compound, [bottom, top])  # the moulded parts only (STEP/STL, what DFM measures)
    assembly_parts(p) -> [labelled parts]    # viewer model: moulded parts + strap (look.build_assembly)

wearable_band — length × width × height = the pod (two drafted shells split at `split_ratio`, like the other
families, with a drafted optical sensor window on the underside); `strap_width` / `strap_length` size the strap,
which is drawn in the viewer GLB only (a moulded LSR part listed in the spec, not measured in DFM).
ring — length = width = outer diameter, height = band width (along the finger), wall = band thickness. Two
annular halves split at `split_ratio`; outer wall drafted to widen toward the split, bore drafted to open away
from it (both halves release along ±Z); a full-height sensor bump on the inside of the band.
"""

from __future__ import annotations

import logging
import math

log = logging.getLogger("cad.wearables")

WEARABLE_BAND, RING = 3, 4
WINDOW_H = 0.8  # optical sensor window proud of the pod underside (mm)
EXTRAS: dict[int, dict[str, float]] = {WEARABLE_BAND: {"strap_width": 24.0, "strap_length": 230.0}}
# plausible ranges (mm): a pod or a ring outside these is not that product any more
RANGES: dict[int, dict[str, tuple[float, float]]] = {
    WEARABLE_BAND: {"length": (25.0, 60.0), "width": (18.0, 45.0), "height": (6.0, 20.0), "wall": (1.2, 2.5),
                    "strap_width": (14.0, 32.0), "strap_length": (150.0, 300.0)},
    RING: {"length": (16.0, 30.0), "height": (4.0, 12.0), "wall": (1.2, 3.5)},
}
PRESETS: dict[int, dict[str, float]] = {
    WEARABLE_BAND: {"family": 3, "length": 44.0, "width": 30.0, "height": 10.0, "fillet": 9.0, "edge_fillet": 2.0,
                    "wall": 1.5, "draft_deg": 1.5, "split_ratio": 0.6, "boss_count": 0, "strap_width": 24.0,
                    "strap_length": 230.0},
    RING: {"family": 4, "length": 22.0, "width": 22.0, "height": 8.0, "fillet": 0.0, "edge_fillet": 0.0, "wall": 2.6,
           "draft_deg": 1.0, "split_ratio": 0.5, "boss_count": 0},
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def normalize_family(p: dict[str, float], raw: dict) -> dict[str, float]:
    fam = int(p["family"])
    for k, dv in EXTRAS.get(fam, {}).items():
        v = raw.get(k)
        p[k] = float(v) if v is not None else dv
    for k, (lo, hi) in RANGES[fam].items():
        p[k] = _clamp(p[k], lo, hi)
    p["draft_deg"] = _clamp(p["draft_deg"], 0.5, 3.0)
    p["boss_count"] = 0.0
    if fam == RING:
        p["width"] = p["length"]
        p["wall"] = min(p["wall"], p["length"] / 2 - 6.0)  # keep a finger bore ≥ 12 mm
        p["fillet"] = 0.0
        p["split_ratio"] = _clamp(p["split_ratio"], 0.4, 0.6)
        p["edge_fillet"] = 0.0  # a fillet on the drafted annulus + bump leaves faces OCCT cannot mesh for DFM
    else:
        p["height"] = max(p["height"], 4 * p["wall"] + 1.0 + WINDOW_H)
        p["split_ratio"] = _clamp(p["split_ratio"], 0.4, 0.7)
        p["fillet"] = _clamp(p["fillet"], 0.0, min(p["length"], p["width"]) / 2 - 0.5)
        shell_h = p["height"] - WINDOW_H
        p["edge_fillet"] = _clamp(p["edge_fillet"], 0.0, min(shell_h * p["split_ratio"], shell_h * (1 - p["split_ratio"])) / 2)
        p["strap_width"] = min(p["strap_width"], p["width"] - 2.0)
    return p


# --------------------------------------------------------------------------- wearable band


def _sensor_window(p: dict[str, float]):
    """Drafted optical sensor window under the pod (z ≤ 0), part of the bottom shell."""
    from build123d import Cone, Pos

    r = max(3.0, min(p["length"], p["width"]) * 0.22)
    h = WINDOW_H
    t = math.tan(math.radians(p["draft_deg"]))
    return Pos(0, 0, h / 2 + 0.05) * Cone(r - h * t, r, h + 0.1)


def _band_shape(p: dict[str, float]):
    from build123d import Compound, Location, Plane

    from api.cad.build import _shell_half

    L, W, wall, d = p["length"], p["width"], p["wall"], p["draft_deg"]
    H = p["height"] - WINDOW_H  # `height` = total pod thickness, sensor window included
    hb = round(H * p["split_ratio"], 3)
    bottom = _shell_half(0, L, W, p["fillet"], hb, wall, d, p["edge_fillet"], 0).moved(Location((0, 0, WINDOW_H)))
    try:
        bottom = bottom + _sensor_window(p)
    except Exception as e:  # noqa: BLE001 — optional feature
        log.info("sensor window dropped: %s", e)
    top = _shell_half(0, L, W, p["fillet"], H - hb, wall, d, p["edge_fillet"], 0)
    top = top.mirror(Plane.XY).moved(Location((0, 0, H + WINDOW_H)))
    bottom.label, top.label = "bottom_shell", "top_shell"
    return Compound(children=[bottom, top]), [bottom, top]


def _strap(p: dict[str, float]):
    """Closed elliptical strap loop under the pod (runs along X, width along Y). Viewer only."""
    from build123d import Ellipse, Plane, Pos, extrude

    c = p["strap_length"]
    t = 2.4  # strap thickness
    r = c / (2 * math.pi)
    rx, rz = r * 1.12, r * 0.88  # wrists are wider than deep
    sw = p["strap_width"]
    outer = extrude(Plane.XZ * Ellipse(rx + t, rz + t), amount=sw / 2, both=True)
    inner = extrude(Plane.XZ * Ellipse(rx, rz), amount=sw / 2 + 1, both=True)
    return Pos(0, 0, -(rz + t) + 0.4) * (outer - inner)


# --------------------------------------------------------------------------- ring


def _ring_half(R: float, r: float, h: float, draft: float, edge: float):
    """Annulus z ∈ [0, h]: outer widens to R at z=h (split side), bore narrows to r at z=h."""
    from build123d import Circle, extrude, fillet

    t = math.tan(math.radians(draft))
    outer = extrude(Circle(R - h * t), amount=h, taper=-draft)
    bore = extrude(Circle(r + h * t), amount=h, taper=draft)
    part = outer - bore
    if edge > 0.15:
        try:
            part = fillet(part.edges().group_by()[0], radius=edge)
        except Exception as e:  # noqa: BLE001
            log.info("ring edge fillet dropped: %s", e)
    return part


def _ring_bump(r: float, h: float, draft: float):
    """Drafted sensor bump on the inside of the band (−Y side), z ∈ [0, h], narrowing toward z=h like the bore."""
    from build123d import Pos, Rectangle, extrude

    depth, w = 0.8, min(5.0, r * 0.6)
    return Pos(0, -(r - depth / 2 + 0.3), 0) * extrude(Rectangle(w, depth + 0.6), amount=h, taper=draft)


def _ring_shape(p: dict[str, float]):
    from build123d import Compound, Location, Plane

    D, H, wall, d = p["length"], p["height"], p["wall"], p["draft_deg"]
    R, r = D / 2, D / 2 - wall
    hb = round(H * p["split_ratio"], 3)
    halves = []
    for h in (hb, H - hb):
        half = _ring_half(R, r, h, d, 0.0)
        try:
            half = half + _ring_bump(r, h, d)
        except Exception as e:  # noqa: BLE001
            log.info("ring sensor bump dropped: %s", e)
        halves.append(half)
    bottom, top = halves[0], halves[1].mirror(Plane.XY).moved(Location((0, 0, H)))
    bottom.label, top.label = "bottom_shell", "top_shell"
    return Compound(children=[bottom, top]), [bottom, top]


# --------------------------------------------------------------------------- public


def build_shape(p: dict[str, float]):
    fam = int(p["family"])
    if fam == WEARABLE_BAND:
        return _band_shape(p)
    if fam == RING:
        return _ring_shape(p)
    raise ValueError(f"not a wearable family: {fam}")


def assembly_parts(p: dict[str, float]) -> list:
    """Viewer parts labelled by role (look.apply_materials): top = body colour, bottom = accent, strap = body."""
    _, (bottom, top) = build_shape(p)
    top.label, bottom.label = "body.1", "accent.1"
    parts = [top, bottom]
    if int(p["family"]) == WEARABLE_BAND:
        try:
            s = _strap(p)
            s.label = "strap.1"
            parts.append(s)
        except Exception as e:  # noqa: BLE001 — the pod alone is still a valid model
            log.info("strap dropped: %s", e)
    return parts


__all__ = ["WEARABLE_BAND", "RING", "PRESETS", "RANGES", "EXTRAS", "normalize_family", "build_shape", "assembly_parts"]
