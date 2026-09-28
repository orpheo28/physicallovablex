"""Irrigation family (W19): smart irrigation kit = controller housing + solenoid valve + soil moisture probe.

Controller: upright weatherproof housing (rounded vertical edges) with a display, three buttons, status LED, a small
PV cell on the sloped roof and a cable gland. Valve: 1" inline body with hex union nuts, bonnet and solenoid coil.
Probe: sensor head on a tapered stake with two stainless electrodes. The three sit side by side on z=0 (probe tip on
the floor), controller at the origin, valve at +X, probe at -X; front faces -Y.
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp, with_detail

NAME = "irrigation"
CATEGORY = "irrigation"
DESCRIPTION = "Smart irrigation kit: controller housing with display + solenoid valve body + soil moisture probe."


@dataclass
class Params:
    housing_width: float = 150.0     # X
    housing_depth: float = 60.0      # Y
    housing_height: float = 190.0    # Z
    corner_radius: float = 14.0
    solar: float = 1.0               # PV cell on the roof 0/1
    pipe_diameter: float = 33.4      # 1" pipe OD
    valve_length: float = 170.0
    probe_length: float = 220.0
    probe_diameter: float = 44.0     # sensor head diameter
    spacing: float = 90.0            # gap between the three pieces

    def clamped(self) -> "Params":
        w = clamp(self.housing_width, 80, 320)
        d = clamp(self.housing_depth, 35, 140)
        return Params(
            housing_width=w, housing_depth=d, housing_height=clamp(self.housing_height, 90, 360),
            corner_radius=clamp(self.corner_radius, 2, min(w, d) / 2 - 2), solar=1.0 if self.solar >= 0.5 else 0.0,
            pipe_diameter=clamp(self.pipe_diameter, 16, 64), valve_length=clamp(self.valve_length, 90, 300),
            probe_length=clamp(self.probe_length, 100, 450), probe_diameter=clamp(self.probe_diameter, 25, 80),
            spacing=clamp(self.spacing, 30, 250),
        )


PRESETS = {"kit": Params()}


def default_params(variant: str = "kit") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["kit"]).clamped())


# === GEOMETRY ===
def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def soft(shape, radius, axis=None):
    try:
        edges = shape.edges() if axis is None else shape.edges().filter_by(axis)
        return fillet(edges, radius=radius)
    except Exception:
        return shape


def hex_nut(across_flats, length):
    return extrude(RegularPolygon(across_flats / 2, 6, major_radius=False), amount=length)


def build_parts(P):
    parts = []
    W, D, H, r = P["housing_width"], P["housing_depth"], P["housing_height"], P["corner_radius"]
    # controller housing: body + sloped roof lid overhanging at the front
    body = extrude(RectangleRounded(W, D, r), amount=H)
    parts.append(lab(soft(body, 3, Axis.Y), "body", 1))
    roof = Pos(0, -4, H) * extrude(RectangleRounded(W + 10, D + 14, r + 4), amount=10)
    parts.append(lab(soft(roof, 3, None), "accent", 1))
    parts.append(lab(Pos(0, -D / 2 - 1, H * 0.68) * Box(W * 0.62, 4, H * 0.24), "glass", 1))
    for i, x in enumerate((-W * 0.2, 0.0, W * 0.2)):
        b = Pos(x, -D / 2 - 2, H * 0.42) * (Rot(90, 0, 0) * Cylinder(min(W * 0.06, 11), 5))
        parts.append(lab(b, "button", 1 + i))
    parts.append(lab(Pos(W * 0.36, -D / 2 - 1, H * 0.88) * (Rot(90, 0, 0) * Cylinder(3, 3)), "led", 1))
    if P["solar"] >= 0.5:
        parts.append(lab(Pos(0, -4, H + 10) * Box(W * 0.8, D * 0.75, 2.5), "cell", 1))
    for i, y in enumerate((-D * 0.2, D * 0.2)):  # cable glands on the right wall (to the valve / the probe)
        gland = Pos(W / 2 + 7, y, H * 0.14) * (Rot(0, 90, 0) * Cylinder(7, 14))
        parts.append(lab(gland, "rubber", 1 + i))
    for i, s in enumerate((1, -1)):
        parts.append(lab(Pos(s * (W / 2 + 6), D / 2 - 4, H * 0.5) * Box(12, 8, H * 0.5), "accent", 2 + i))

    # solenoid valve at +X: pipe axis along X, resting on its nuts
    pr = P["pipe_diameter"] / 2
    vl = P["valve_length"]
    nut = pr * 2.3
    cx = W / 2 + P["spacing"] + vl / 2
    zc = nut / math.sqrt(3)  # resting on a nut corner: half the across-corners size
    pipe = Pos(cx, 0, zc) * (Rot(0, 90, 0) * Cylinder(pr * 1.05, vl))
    parts.append(lab(pipe, "coat", 1))
    for i, s in enumerate((1, -1)):
        n = Pos(cx + s * (vl / 2 - 13), 0, zc) * (Rot(0, 90, 0) * Pos(0, 0, -13) * hex_nut(nut, 26))
        parts.append(lab(n, "coat", 2 + i))
    bodyv = Pos(cx, 0, zc) * Box(vl * 0.42, pr * 2.6, pr * 2.4)
    parts.append(lab(soft(bodyv, pr * 0.4, None), "coat", 4))
    bonnet = Pos(cx, 0, zc + pr * 1.2) * Cylinder(pr * 1.15, pr * 1.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(bonnet, "coat", 5))
    coil_z = zc + pr * 2.4
    coil = Pos(cx, 0, coil_z) * Cylinder(pr * 0.9, pr * 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(soft(coil, 3, None), "rubber", 3))
    parts.append(lab(Pos(cx + pr * 0.9, 0, coil_z + pr) * (Rot(0, 90, 0) * Cylinder(4, 30)), "rubber", 4))
    parts.append(lab(Pos(cx - vl * 0.12, -pr * 1.3 - 1, zc) * Box(vl * 0.06, 2, pr * 0.8), "accent", 4))

    # soil probe at -X: tip on the floor, head at the top
    L, pd = P["probe_length"], P["probe_diameter"]
    px = -W / 2 - P["spacing"] - pd / 2
    head_h = pd * 1.1
    stake_l = L - head_h
    tip_l = min(40.0, stake_l * 0.25)
    stake = Pos(px, 0, tip_l - 1) * Box(pd * 0.45, 9, stake_l - tip_l + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
    tip = Pos(px, 0, 0) * Cone(0.5, pd * 0.26, tip_l, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(stake, "accent", 5))
    parts.append(lab(tip, "accent", 6))
    for i, s in enumerate((1, -1)):
        e = Pos(px + s * pd * 0.12, -5.2, stake_l * 0.3) * Box(3, 1.5, stake_l * 0.45)
        parts.append(lab(e, "steel", 1 + i))
    head = Pos(px, 0, stake_l) * Cylinder(pd / 2, head_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(soft(head, pd * 0.2, None), "body", 2))
    parts.append(lab(Pos(px, 0, stake_l + head_h) * Cylinder(pd * 0.36, 1.5, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                     "cell", 2))
    parts.append(lab(Pos(px, -pd / 2, stake_l + head_h * 0.55) * (Rot(90, 0, 0) * Cylinder(2.5, 3)), "led", 2))
    return parts
# === END GEOMETRY ===


# === PRO DETAIL ===
def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro: IP65 controller — EPDM perimeter gasket in a face-seal groove (25 % squeeze) under the
    lid, lid held by 4 M4 pan screws into heat-set inserts in the housing corners."""
    from api.cad.stdparts import add_parts, gasket, gasket_groove, named, screw_joint

    W, D, H, r = P["housing_width"], P["housing_depth"], P["housing_height"], P["corner_radius"]
    body = next(q for q in parts if q.label == "body.1")
    inset, cord = 6.0, 2.0
    lm, dm, rm = W - 2 * inset, D - 2 * inset, max(r - inset, 3.0)
    try:
        housing = body - Pos(0, 0, H) * gasket_groove(lm, dm, rm, cord)
    except Exception:
        housing = body
    parts = [q for q in parts if q is not body]
    parts.append(lab(named(housing, "Controller housing (gasketed)", role="shell_bottom"), "body", 1))
    seal = gasket(lm + cord, dm + cord, rm + cord / 2, cord).at(0, 0, H - 0.75 * cord)
    kit = [seal]
    c = max(r * 0.6, 9.0)
    for sx in (1, -1):
        for sy in (1, -1):
            kit += screw_joint("M4", (sx * (W / 2 - c), sy * (D / 2 - c), H + 10), (0, 0, -1), grip=10, head="pan")
    return add_parts(parts, kit, "body")
# === END PRO DETAIL ===


def build(params: Params | dict | None = None):
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    P = asdict(p.clamped())
    parts = with_detail(pro_details, P, build_parts(P))  # C1: CAD_DETAIL_LEVEL=pro adds hardware
    return Compound(children=parts), parts
