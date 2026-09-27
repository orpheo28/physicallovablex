"""Home robot family (W19): wheeled domestic robot with a torso, head, sensor mast and a manipulator arm.

Round drive base (bumper band, two drive wheels, casters), tapered torso, head with a dark visor/face display,
sensor mast with a lidar puck, optional two-segment arm with shoulder/elbow joints and a two-finger gripper.
Origin: base centre on the floor, +Z up, facing +X.
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp

NAME = "home_robot"
CATEGORY = "home_robot"
DESCRIPTION = "Wheeled home robot: drive base with wheels, torso, head with visor, sensor mast, arm with gripper."


@dataclass
class Params:
    base_diameter: float = 460.0
    base_height: float = 130.0
    wheel_diameter: float = 130.0
    torso_height: float = 620.0
    torso_diameter: float = 300.0
    head_diameter: float = 240.0
    head_height: float = 170.0
    mast_height: float = 70.0
    arm: float = 1.0                 # 0 / 1
    arm_length: float = 480.0        # shoulder to gripper

    def clamped(self) -> "Params":
        bd = clamp(self.base_diameter, 250, 800)
        td = clamp(self.torso_diameter, 120, bd * 0.85)
        return Params(
            base_diameter=bd, base_height=clamp(self.base_height, 60, 250),
            wheel_diameter=clamp(self.wheel_diameter, 60, 250), torso_height=clamp(self.torso_height, 150, 1300),
            torso_diameter=td, head_diameter=clamp(self.head_diameter, 100, 450),
            head_height=clamp(self.head_height, 80, 350), mast_height=clamp(self.mast_height, 0, 250),
            arm=1.0 if self.arm >= 0.5 else 0.0, arm_length=clamp(self.arm_length, 200, 900),
        )


PRESETS = {"helper": Params(), "compact": Params(base_diameter=340, base_height=90, wheel_diameter=90, torso_height=260,
                                                  torso_diameter=220, head_diameter=200, head_height=140, mast_height=40,
                                                  arm=0.0)}


def default_params(variant: str = "helper") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["helper"]).clamped())


# === GEOMETRY ===
def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rod(p1, p2, r):
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
    R, bh = P["base_diameter"] / 2, P["base_height"]
    wr = P["wheel_diameter"] / 2
    clear = max(wr * 0.35, 18.0)
    base = Pos(0, 0, clear) * Cylinder(R, bh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    base = soft(base, min(bh * 0.3, 30), None)
    parts.append(lab(base, "accent", 1))
    parts.append(lab(Pos(0, 0, clear + bh * 0.25) * (Cylinder(R + 4, bh * 0.22) - Cylinder(R - 5, bh * 0.3)), "rubber", 1))
    for i, s in enumerate((1, -1)):
        wheel = Pos(0, s * (R * 0.72), wr) * (Rot(90, 0, 0) * Cylinder(wr, min(wr * 0.5, 45)))
        parts.append(lab(wheel, "rubber", 2 + i))
        hub = Pos(0, s * (R * 0.72 + min(wr * 0.25, 22.5)), wr) * (Rot(90, 0, 0) * Cylinder(wr * 0.45, 3))
        parts.append(lab(hub, "metal", 1 + i))
    for i, x in enumerate((R * 0.6, -R * 0.6)):
        parts.append(lab(Pos(x, 0, clear / 2) * Sphere(clear / 2), "rubber", 4 + i))

    z = clear + bh
    th, tr = P["torso_height"], P["torso_diameter"] / 2
    torso = Pos(0, 0, z) * Cone(tr, tr * 0.82, th, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(soft(torso, 12, None), "body", 1))
    parts.append(lab(Pos(tr * 0.92 - 2, 0, z + th * 0.55) * Box(6, tr * 0.8, th * 0.28), "glass", 1))
    parts.append(lab(Pos(tr * 0.9, 0, z + th * 0.35) * (Rot(0, 90, 0) * Cylinder(8, 6)), "led", 1))
    z += th
    neck_h = max(th * 0.06, 25.0)
    parts.append(lab(Pos(0, 0, z) * Cylinder(tr * 0.35, neck_h, align=(Align.CENTER, Align.CENTER, Align.MIN)), "coat", 1))
    z += neck_h

    hr, hh = P["head_diameter"] / 2, P["head_height"]
    head = Pos(0, 0, z) * extrude(RectangleRounded(hr * 1.9, hr * 2, hr * 0.7), amount=hh)
    parts.append(lab(soft(head, hh * 0.3, None), "body", 2))
    visor = Pos(hr * 0.95 - 8, 0, z + hh * 0.5) * Box(18, hr * 1.4, hh * 0.45)
    parts.append(lab(soft(visor, 6, Axis.X), "glass", 2))
    for i, s in enumerate((1, -1)):
        parts.append(lab(Pos(hr * 0.95 + 1.5, s * hr * 0.3, z + hh * 0.52) * (Rot(0, 90, 0) * Cylinder(hh * 0.07, 2)),
                         "led", 2 + i))
    z += hh
    mh = P["mast_height"]
    if mh > 5:
        parts.append(lab(Pos(0, 0, z) * Cylinder(hr * 0.12, mh, align=(Align.CENTER, Align.CENTER, Align.MIN)), "metal", 3))
        parts.append(lab(Pos(0, 0, z + mh) * Cylinder(hr * 0.33, 34, align=(Align.CENTER, Align.CENTER, Align.MIN)), "coat", 2))
        parts.append(lab(Pos(0, 0, z + mh + 8) * (Cylinder(hr * 0.335, 14, align=(Align.CENTER, Align.CENTER, Align.MIN))
                                                 - Cylinder(hr * 0.3, 20)), "glass", 3))

    if P["arm"] >= 0.5:
        L = P["arm_length"]
        zs = clear + bh + th * 0.82
        ys = -(tr * 0.88 + 30)
        shoulder = (0, ys, zs)
        elbow = (L * 0.35, ys - 20, zs - L * 0.38)
        wrist = (L * 0.78, ys - 20, zs - L * 0.3)
        parts.append(lab(Pos(*shoulder) * Sphere(40), "coat", 3))
        parts.append(lab(rod(shoulder, elbow, 30), "body", 3))
        parts.append(lab(Pos(*elbow) * Sphere(32), "coat", 4))
        parts.append(lab(rod(elbow, wrist, 25), "body", 4))
        parts.append(lab(Pos(*wrist) * Sphere(26), "coat", 5))
        palm = (wrist[0] + 45, wrist[1], wrist[2])
        parts.append(lab(rod(wrist, palm, 22), "metal", 4))
        for i, s in enumerate((1, -1)):
            f = Pos(palm[0] + 32, palm[1], palm[2] + s * 14) * Box(64, 20, 8)
            parts.append(lab(soft(f, 3, None), "rubber", 6 + i))
    return parts
# === END GEOMETRY ===


def build(params: Params | dict | None = None):
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    parts = build_parts(asdict(p.clamped()))
    return Compound(children=parts), parts
