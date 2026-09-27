"""Stick vacuum family (W19): Dyson-style cordless stick vacuum, standing upright.

Floor head (rounded housing + brush roll + swivel neck) at z=0, straight wand up to the hand unit: clear dust bin
under a cyclone shroud crowned by a ring of mini cyclone cones, motor pod behind it, pistol-grip handle with a
trigger, battery pack under the grip. Origin: floor head centre on the floor, wand axis on Z, cleaning direction +X.
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp

NAME = "stick_vacuum"
CATEGORY = "vacuum"
DESCRIPTION = "Cordless stick vacuum: floor head, wand, cyclone + clear bin, motor pod, pistol handle, battery."


@dataclass
class Params:
    height: float = 1180.0          # floor to top of the hand unit
    wand_diameter: float = 38.0
    bin_diameter: float = 96.0
    bin_length: float = 230.0       # clear bin + cyclone shroud length
    cyclone_count: float = 10.0     # mini cyclone cones in the ring
    motor_diameter: float = 72.0
    handle_length: float = 150.0
    head_width: float = 250.0       # across the cleaning path (Y)
    head_depth: float = 115.0       # X
    head_height: float = 58.0

    def clamped(self) -> "Params":
        return Params(
            height=clamp(self.height, 900, 1350), wand_diameter=clamp(self.wand_diameter, 28, 50),
            bin_diameter=clamp(self.bin_diameter, 70, 140), bin_length=clamp(self.bin_length, 150, 320),
            cyclone_count=float(int(clamp(round(self.cyclone_count), 0, 16))),
            motor_diameter=clamp(self.motor_diameter, 50, 100), handle_length=clamp(self.handle_length, 110, 190),
            head_width=clamp(self.head_width, 180, 330), head_depth=clamp(self.head_depth, 80, 160),
            head_height=clamp(self.head_height, 40, 80),
        )


PRESETS = {"stick": Params()}


def default_params(variant: str = "stick") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["stick"]).clamped())


# === GEOMETRY ===
def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rod(p1, p2, r):
    """Cylinder of radius r from point p1 to point p2."""
    a, b = Vector(*p1), Vector(*p2)
    d = b - a
    return Plane(origin=(a + b) * 0.5, z_dir=d) * Cylinder(r, d.length)


def soft(shape, radius, axis=None):
    try:
        edges = shape.edges() if axis is None else shape.edges().filter_by(axis)
        return fillet(edges, radius=radius)
    except Exception:
        return shape


def build_parts(P):
    parts = []
    hw, hd, hh = P["head_width"], P["head_depth"], P["head_height"]
    # floor head: housing (rounded in plan), brush roll window at the front, swivel neck at the back
    head = Pos(0, 0, 4) * extrude(RectangleRounded(hd, hw, min(hd, hw) * 0.18), amount=hh - 4)
    head = soft(head, (hh - 4) * 0.3, None)
    parts.append(lab(head, "accent", 1))
    roll_r = hh * 0.36
    parts.append(lab(Pos(hd * 0.22, 0, roll_r + 2) * (Rot(90, 0, 0) * Cylinder(roll_r, hw - 16)), "rubber", 1))
    parts.append(lab(Pos(hd * 0.05, 0, hh - 1) * Box(hd * 0.55, hw * 0.8, 4), "clear", 1))
    for s in (1, -1):
        parts.append(lab(Pos(-hd * 0.35, s * (hw / 2 - 14), 16) * (Rot(90, 0, 0) * Cylinder(15, 12)), "rubber", 2 + (s > 0)))
    neck_z = hh + 18
    parts.append(lab(Pos(-hd * 0.2, 0, neck_z) * Sphere(26), "metal", 1))
    parts.append(lab(rod((-hd * 0.2, 0, hh - 8), (-hd * 0.2, 0, neck_z), 20), "accent", 2))

    # wand
    H, wr = P["height"], P["wand_diameter"] / 2
    bl, br = P["bin_length"], P["bin_diameter"] / 2
    unit_z0 = H - bl - 40  # hand unit starts here
    wx = -hd * 0.2
    parts.append(lab(rod((wx, 0, neck_z), (wx, 0, unit_z0 + 30), wr), "metal", 2))
    parts.append(lab(rod((wx, 0, unit_z0 - 10), (wx, 0, unit_z0 + 40), wr + 5), "accent", 3))

    # clear bin + cyclone shroud + cyclone cone ring (axis parallel to the wand, just ahead of it)
    bx = wx + wr - br * 0.35 + br * 0.6
    z_bin = unit_z0 + 40
    bin_h = bl * 0.55
    parts.append(lab(Pos(bx, 0, z_bin) * extrude(Circle(br), amount=bin_h), "clear", 2))
    parts.append(lab(Pos(bx, 0, z_bin - 12) * Cylinder(br + 2, 24), "accent", 4))
    shroud = Pos(bx, 0, z_bin + bin_h) * extrude(Circle(br * 0.92), amount=bl * 0.3, taper=4)
    parts.append(lab(shroud, "metal", 3))
    zc = z_bin + bin_h + bl * 0.3
    n = int(P["cyclone_count"])
    rc = br * 0.62
    cone_r = max(6.0, min(2 * math.pi * rc / max(n, 1) * 0.42, br * 0.3))
    for i in range(n):
        a = 2 * math.pi * i / n
        c = Pos(bx + rc * math.cos(a), rc * math.sin(a), zc + bl * 0.07) * Cone(cone_r, cone_r * 0.45, bl * 0.14)
        parts.append(lab(c, "accent", 5 + i))
    parts.append(lab(Pos(bx, 0, zc) * Cylinder(br * 0.35, bl * 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                     "body", 1))

    # motor pod behind the bin, handle below it, battery under the grip
    mr = P["motor_diameter"] / 2
    mx = bx - br - mr + 8
    mz0 = z_bin + bin_h * 0.45
    mz1 = zc + bl * 0.12
    motor = Pos(mx, 0, mz0) * extrude(Circle(mr), amount=mz1 - mz0)
    parts.append(lab(soft(motor, mr * 0.3, None), "body", 2))
    vent = Pos(mx, 0, mz1 - 2) * Cylinder(mr * 0.75, 6)
    parts.append(lab(vent, "coat", 1))
    hl = P["handle_length"]
    hx0 = mx - mr * 0.6
    top = (hx0 - 30, 0, mz1 - 20)
    bot = (hx0 - 30 - hl * 0.3, 0, mz1 - 20 - hl)
    parts.append(lab(rod(top, bot, 17), "body", 3))
    parts.append(lab(rod((mx - mr * 0.2, 0, mz1 - 18), top, 15), "body", 4))
    parts.append(lab(Pos(bot[0] + 30, 0, bot[2] + hl * 0.55) * Rot(0, -17, 0) * Box(14, 16, 40), "button", 1))
    batt = Pos(bot[0] + 30, 0, bot[2] - 10) * Box(110, 58, 60)
    parts.append(lab(soft(batt, 10, None), "accent", 40))
    parts.append(lab(rod((bot[0] + 60, 0, bot[2] - 10), (mx + mr * 0.5, 0, mz0 + 10), 12), "body", 5))
    return parts
# === END GEOMETRY ===


def build(params: Params | dict | None = None):
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    parts = build_parts(asdict(p.clamped()))
    return Compound(children=parts), parts
