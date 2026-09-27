"""Furniture family (W19): baby changing table / children's activity table.

Top (rounded-corner slab), four legs (rounded square section, slight taper), aprons (rails) under the top, raised
safety edges on the back and sides (changing table), optional lower shelf with two storage baskets, optional wipe-
clean changing pad. Origin: footprint centre on the floor, +Z up; X = length, Y = depth (front at -Y).
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp

NAME = "furniture"
CATEGORY = "furniture_child"
DESCRIPTION = "Child furniture (changing table / activity table): top, legs, rails, raised safety edges, shelf."


@dataclass
class Params:
    length: float = 900.0           # X
    depth: float = 560.0            # Y
    height: float = 900.0           # floor to top surface
    top_thickness: float = 24.0
    corner_radius: float = 40.0     # plan corner radius of the top
    leg_size: float = 44.0          # square leg section
    rail_height: float = 70.0       # apron height under the top
    guard_height: float = 110.0     # raised safety edge above the top (0 = none, activity table)
    guard_thickness: float = 18.0
    guard_sides: float = 3.0        # 0 none · 1 back · 2 back + left · 3 back + both sides
    shelf: float = 1.0              # lower shelf 0/1
    shelf_height: float = 230.0
    pad: float = 1.0                # changing pad 0/1
    pad_thickness: float = 45.0

    def clamped(self) -> "Params":
        L = clamp(self.length, 500, 1600)
        D = clamp(self.depth, 350, 900)
        H = clamp(self.height, 400, 1050)
        tt = clamp(self.top_thickness, 15, 45)
        leg = clamp(self.leg_size, 25, 80)
        return Params(
            length=L, depth=D, height=H, top_thickness=tt,
            corner_radius=clamp(self.corner_radius, 3, min(L, D) / 4),
            leg_size=leg, rail_height=clamp(self.rail_height, 30, 150),
            guard_height=clamp(self.guard_height, 0, 250), guard_thickness=clamp(self.guard_thickness, 12, 30),
            guard_sides=float(int(clamp(round(self.guard_sides), 0, 3))),
            shelf=1.0 if self.shelf >= 0.5 and H > 450 else 0.0,
            shelf_height=clamp(self.shelf_height, 120, max(H - 300, 121)),
            pad=1.0 if self.pad >= 0.5 else 0.0, pad_thickness=clamp(self.pad_thickness, 20, 80),
        )


PRESETS = {
    "changing_table": Params(),
    "activity_table": Params(length=800, depth=600, height=500, top_thickness=22, corner_radius=90, leg_size=48,
                             rail_height=55, guard_height=25, guard_thickness=14, guard_sides=3, shelf=0, pad=0),
}


def default_params(variant: str = "changing_table") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["changing_table"]).clamped())


# === GEOMETRY ===
def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def soft(shape, radius, axis=None):
    """Fillet edges (all, or those parallel to `axis`); keep the raw shape if OCCT refuses."""
    try:
        edges = shape.edges() if axis is None else shape.edges().filter_by(axis)
        return fillet(edges, radius=radius)
    except Exception:
        return shape


def build_parts(P):
    L, D, H = P["length"], P["depth"], P["height"]
    tt, leg, r = P["top_thickness"], P["leg_size"], P["corner_radius"]
    parts = []
    top = Pos(0, 0, H - tt) * extrude(RectangleRounded(L, D, r), amount=tt)
    parts.append(lab(soft(top, min(4.0, tt / 3), None), "wood", 1))

    inset = max(r * 0.3, 10.0) + leg / 2
    lx, ly = L / 2 - inset, D / 2 - inset
    leg_h = H - tt
    for i, (x, y) in enumerate([(lx, ly), (-lx, ly), (lx, -ly), (-lx, -ly)]):
        post = extrude(Rectangle(leg, leg), amount=leg_h, taper=0.6)
        parts.append(lab(Pos(x, y, 0) * soft(post, leg * 0.18, Axis.Z), "wood", 2 + i))

    rh, rt = P["rail_height"], 18.0
    z_rail = H - tt - rh
    parts.append(lab(Pos(0, ly, z_rail + rh / 2) * Box(2 * lx - leg, rt, rh), "body", 1))
    parts.append(lab(Pos(0, -ly, z_rail + rh / 2) * Box(2 * lx - leg, rt, rh), "body", 2))
    parts.append(lab(Pos(lx, 0, z_rail + rh / 2) * Box(rt, 2 * ly - leg, rh), "body", 3))
    parts.append(lab(Pos(-lx, 0, z_rail + rh / 2) * Box(rt, 2 * ly - leg, rh), "body", 4))

    gh, gt, sides = P["guard_height"], P["guard_thickness"], int(P["guard_sides"])
    n = 4
    if gh > 5 and sides > 0:
        z0 = H
        back = Pos(0, D / 2 - gt / 2, z0 + gh / 2) * Box(L - 2 * r * 0.3, gt, gh)
        n += 1
        parts.append(lab(soft(back, gt * 0.45, Axis.X), "body", n))
        for s in ([1] if sides == 2 else [1, -1] if sides == 3 else []):
            side = Pos(s * (L / 2 - gt / 2), gt / 2, z0 + gh / 2) * Box(gt, D - gt - 2 * r * 0.3, gh)
            n += 1
            parts.append(lab(soft(side, gt * 0.45, Axis.Y), "body", n))

    if P["shelf"] >= 0.5:
        sh = P["shelf_height"]
        shelf = Pos(0, 0, sh) * Box(2 * lx + leg * 0.6, 2 * ly + leg * 0.6, 16)
        parts.append(lab(shelf, "wood", 6))
        bw = (2 * lx - leg) / 2 - 30
        for i, x in enumerate([-bw / 2 - 12, bw / 2 + 12]):
            bh = min(170.0, H - tt - rh - sh - 60)
            if bh < 60:
                break
            basket = Pos(x, 0, sh + 8) * extrude(RectangleRounded(bw, 2 * ly - leg - 40, 25), amount=bh)
            hollow = Pos(x, 0, sh + 14) * extrude(RectangleRounded(bw - 12, 2 * ly - leg - 52, 19), amount=bh)
            parts.append(lab(basket - hollow, "fabric", 1 + i))

    if P["pad"] >= 0.5:
        pt = P["pad_thickness"]
        pl = L - 2 * gt - 30 if sides == 3 else L - gt - 30
        pd = D - gt - 30
        px = 0 if sides != 2 else -gt / 2
        pad = Pos(px, -gt / 2, H) * extrude(RectangleRounded(pl, pd, min(60.0, pd / 4)), amount=pt)
        pad = soft(pad, pt * 0.4, None)
        rim = Pos(px, -gt / 2, H + pt - 6) * extrude(RectangleRounded(pl - 90, pd - 90, min(40.0, pd / 6)), amount=8)
        parts.append(lab(pad - rim, "fabric", 3))
    return parts
# === END GEOMETRY ===


def build(params: Params | dict | None = None):
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    parts = build_parts(asdict(p.clamped()))
    return Compound(children=parts), parts
