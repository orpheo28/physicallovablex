"""Hair dryer family (W21): pistol-style dryer standing on its handle.

Barrel (heater + fan duct) along X with a tapered concentrator nozzle at the front (+X), a removable intake filter
cap at the back, an angled handle underneath with a speed/heat switch and a cold-shot button, the cord strain relief
at the handle end. Origin: handle end on the floor, centred under the barrel.
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp

NAME = "hair_dryer"
CATEGORY = "hair_dryer"
DESCRIPTION = "Hair dryer: barrel with heater/fan duct, concentrator nozzle, intake filter cap, angled handle, switches."


@dataclass
class Params:
    barrel_length: float = 185.0
    barrel_diameter: float = 72.0
    nozzle_length: float = 60.0
    nozzle_outlet: float = 44.0     # outlet diameter (concentrator)
    filter_diameter: float = 76.0
    handle_length: float = 150.0
    handle_width: float = 38.0
    handle_depth: float = 30.0
    handle_angle_deg: float = 12.0  # rake of the handle, backwards from vertical

    def clamped(self) -> "Params":
        return Params(
            barrel_length=clamp(self.barrel_length, 110, 280), barrel_diameter=clamp(self.barrel_diameter, 45, 110),
            nozzle_length=clamp(self.nozzle_length, 20, 120), nozzle_outlet=clamp(self.nozzle_outlet, 20, 80),
            filter_diameter=clamp(self.filter_diameter, 40, 120), handle_length=clamp(self.handle_length, 90, 220),
            handle_width=clamp(self.handle_width, 24, 60), handle_depth=clamp(self.handle_depth, 20, 50),
            handle_angle_deg=clamp(self.handle_angle_deg, 0, 25),
        )


PRESETS = {
    "pistol": Params(),
    "compact": Params(barrel_length=150, barrel_diameter=62, nozzle_length=45, nozzle_outlet=38, filter_diameter=64,
                      handle_length=120, handle_width=34, handle_depth=28),
}


def default_params(variant: str = "pistol") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["pistol"]).clamped())


# === GEOMETRY ===
def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def xcyl(x0, length, r, z):
    """Cylinder along +X starting at x0, axis at height z."""
    return Pos(x0 + length / 2, 0, z) * (Rot(0, 90, 0) * Cylinder(r, length))


def build_parts(P):
    parts = []
    hl, hw, hd = P["handle_length"], P["handle_width"], P["handle_depth"]
    br, bl = P["barrel_diameter"] / 2, P["barrel_length"]
    z = hl + br * 0.7  # barrel axis height
    x_back = -bl * 0.42
    barrel = xcyl(x_back, bl, br, z)
    try:
        barrel = fillet(barrel.edges(), radius=br * 0.25)
    except Exception:
        pass
    parts.append(lab(barrel, "body", 1))
    # concentrator nozzle (cone) at the front
    nl, no = P["nozzle_length"], P["nozzle_outlet"] / 2
    nozzle = Pos(x_back + bl + nl / 2, 0, z) * (Rot(0, 90, 0) * Cone(br * 0.82, no, nl))
    parts.append(lab(nozzle, "accent", 1))
    parts.append(lab(Pos(x_back + bl + nl, 0, z) * (Rot(0, 90, 0) * Cylinder(no * 0.8, 1.2)), "coat", 1))
    # intake filter cap at the back (mesh = coat), a rim ring
    fr = P["filter_diameter"] / 2
    parts.append(lab(xcyl(x_back - 14, 16, fr, z), "coat", 2))
    parts.append(lab(xcyl(x_back - 3, 4, fr + 2, z), "accent", 2))
    # handle: raked box with rounded edges, from the barrel down to the floor
    a = P["handle_angle_deg"]
    handle = Pos(-hl * math.sin(math.radians(a)) * 0.5, 0, 0) * Rot(0, -a, 0) * Box(
        hd, hw, hl + br * 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        handle = fillet(handle.edges().filter_by(Axis.Z), radius=min(hw, hd) * 0.42)
    except Exception:
        pass
    parts.append(lab(handle, "body", 2))
    # speed / heat slide switch and cold-shot button on the front face of the handle
    fx = hd / 2 - hl * math.sin(math.radians(a)) * 0.3
    parts.append(lab(Pos(fx + 1, 0, hl * 0.62) * Box(5, hw * 0.45, 26), "button", 1))
    parts.append(lab(Pos(fx + 1, 0, hl * 0.85) * Box(6, hw * 0.4, 12), "button", 2))
    parts.append(lab(Pos(fx - 2, 0, hl * 0.4) * Box(3, hw * 0.3, 5), "led", 1))
    # cord strain relief under the handle
    parts.append(lab(Pos(-hl * math.sin(math.radians(a)) * 0.5, 0, 6) * Cylinder(7, 12), "rubber", 1))
    return parts
# === END GEOMETRY ===


def build(params: Params | dict | None = None):
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    parts = build_parts(asdict(p.clamped()))
    return Compound(children=parts), parts
