"""Drone family (W21): compact quadcopter with foldable arms, a camera gimbal pod and a top-mounted battery.

Centre body (rounded, tapered nose) at the origin, 4 arms at ±45° (X forward), a BLDC motor and a 2-blade propeller
at each arm tip, the battery pack on top of the body, a 2-axis gimbal pod with the camera under the nose, landing
skids under the arms. Origin: body centre on the ground plane (skids on z=0).
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp

NAME = "drone"
CATEGORY = "drone"
DESCRIPTION = "Quadcopter: centre body, 4 foldable arms with motors + props, top battery, camera gimbal pod, skids."


@dataclass
class Params:
    body_length: float = 150.0      # X (nose forward)
    body_width: float = 82.0
    body_height: float = 48.0
    arm_length: float = 118.0       # body edge to motor axis
    arm_diameter: float = 13.0
    arm_angle_deg: float = 45.0     # from the X axis (40-60)
    motor_diameter: float = 26.0
    motor_height: float = 16.0
    prop_diameter: float = 178.0    # 7 inch
    battery_length: float = 95.0
    battery_width: float = 48.0
    battery_height: float = 26.0
    gimbal_diameter: float = 38.0
    skid_height: float = 34.0

    def clamped(self) -> "Params":
        return Params(
            body_length=clamp(self.body_length, 80, 320), body_width=clamp(self.body_width, 50, 200),
            body_height=clamp(self.body_height, 25, 110), arm_length=clamp(self.arm_length, 60, 320),
            arm_diameter=clamp(self.arm_diameter, 8, 30), arm_angle_deg=clamp(self.arm_angle_deg, 35, 60),
            motor_diameter=clamp(self.motor_diameter, 14, 60), motor_height=clamp(self.motor_height, 8, 40),
            prop_diameter=clamp(self.prop_diameter, 76, 460), battery_length=clamp(self.battery_length, 40, 220),
            battery_width=clamp(self.battery_width, 25, 120), battery_height=clamp(self.battery_height, 12, 70),
            gimbal_diameter=clamp(self.gimbal_diameter, 20, 90), skid_height=clamp(self.skid_height, 15, 120),
        )


PRESETS = {
    "follow": Params(),
    "mini": Params(body_length=110, body_width=62, body_height=38, arm_length=78, arm_diameter=10, motor_diameter=18,
                   motor_height=12, prop_diameter=127, battery_length=70, battery_width=36, battery_height=20,
                   gimbal_diameter=28, skid_height=24),
}


def default_params(variant: str = "follow") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["follow"]).clamped())


# === GEOMETRY ===
def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rod(p1, p2, r):
    """Cylinder of radius r from point p1 to point p2."""
    a, b = Vector(*p1), Vector(*p2)
    d = b - a
    return Plane(origin=(a + b) * 0.5, z_dir=d) * Cylinder(r, d.length)


def soft(shape, radius):
    try:
        return fillet(shape.edges(), radius=radius)
    except Exception:
        return shape


def build_parts(P):
    parts = []
    L, W, H = P["body_length"], P["body_width"], P["body_height"]
    z0 = P["skid_height"]
    # centre body: rounded plan, slightly tapered to the top, nose forward (+X)
    body = Pos(0, 0, z0) * extrude(RectangleRounded(L, W, min(L, W) * 0.3), amount=H, taper=6)
    parts.append(lab(soft(body, min(H, W) * 0.18), "body", 1))
    # arms at ±angle, front and back, motors + props at the tips
    a = math.radians(P["arm_angle_deg"])
    ar = P["arm_diameter"] / 2
    zc = z0 + H * 0.55
    reach = P["arm_length"] + min(L, W) * 0.35
    md, mh = P["motor_diameter"], P["motor_height"]
    n = 0
    for sx in (1, -1):
        for sy in (1, -1):
            n += 1
            x0, y0 = sx * L * 0.25, sy * W * 0.3
            x1, y1 = sx * reach * math.cos(a), sy * reach * math.sin(a)
            parts.append(lab(rod((x0, y0, zc), (x1, y1, zc), ar), "coat", n))
            parts.append(lab(Pos(x1, y1, zc) * Cylinder(md / 2, mh, align=(Align.CENTER, Align.CENTER, Align.MIN)), "metal", n))
            hub_z = zc + mh
            parts.append(lab(Pos(x1, y1, hub_z) * Cylinder(md * 0.22, 5, align=(Align.CENTER, Align.CENTER, Align.MIN)), "accent", n))
            blade = Pos(x1, y1, hub_z + 2) * Rot(0, 0, 30 * n) * Box(P["prop_diameter"], P["prop_diameter"] * 0.075, 2.2)
            parts.append(lab(blade, "accent", 10 + n))
            # skid leg under each motor
            parts.append(lab(rod((x1 * 0.8, y1 * 0.8, zc), (x1 * 0.8, y1 * 0.8, 2), ar * 0.55), "rubber", n))
            parts.append(lab(Pos(x1 * 0.8, y1 * 0.8, 2) * Sphere(ar * 0.9), "rubber", 10 + n))
    # battery on top
    bl, bw, bh = P["battery_length"], P["battery_width"], P["battery_height"]
    batt = Pos(-L * 0.05, 0, z0 + H - 2) * Box(bl, bw, bh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(soft(batt, min(bh, bw) * 0.2), "accent", 30))
    parts.append(lab(Pos(-L * 0.05 + bl / 2 - 6, 0, z0 + H - 2 + bh) * Box(8, bw * 0.5, 3), "led", 1))
    # gimbal pod under the nose: yoke + camera ball + lens
    gd = P["gimbal_diameter"]
    gx = L * 0.36
    parts.append(lab(Pos(gx, 0, z0 - 4) * Box(gd * 0.5, gd * 1.1, 8), "coat", 20))
    ball = Pos(gx, 0, z0 - 6 - gd / 2) * Sphere(gd / 2)
    parts.append(lab(ball, "coat", 21))
    parts.append(lab(Pos(gx + gd * 0.42, 0, z0 - 6 - gd / 2) * (Rot(0, 90, 0) * Cylinder(gd * 0.26, gd * 0.25)), "glass", 1))
    return parts
# === END GEOMETRY ===


def build(params: Params | dict | None = None):
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    parts = build_parts(asdict(p.clamped()))
    return Compound(children=parts), parts
