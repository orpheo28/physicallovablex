"""Home Robot (helper) — seed program of our parametric family.

Wheeled home robot: drive base with wheels, torso, head with visor, sensor mast, arm with gripper. Full product: parameters dict P, geometry helpers, labelled parts.
tags: robot, home robot, wheels, torso, head, visor, arm, gripper, mast, helper
"""
import math

from build123d import *

P = {
    'base_diameter': 460.0,
    'base_height': 130.0,
    'wheel_diameter': 130.0,
    'torso_height': 620.0,
    'torso_diameter': 300.0,
    'head_diameter': 240.0,
    'head_height': 170.0,
    'mast_height': 70.0,
    'arm': 1.0,
    'arm_length': 480.0,
}

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


def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro: a 6001-2Z bearing in each wheel hub with an M5 axle screw + washer, a rear access panel
    held by 4 countersunk M3 screws into heat-set inserts, torso screwed to the base with 4 M4 into inserts."""
    from api.cad.stdparts import add_parts, bearing, named, screw_joint, washer

    R, bh = P["base_diameter"] / 2, P["base_height"]
    wr = P["wheel_diameter"] / 2
    clear = max(wr * 0.35, 18.0)
    kit = []
    for s in (1, -1):
        yw = s * (R * 0.72)
        kit.append(bearing("6001").along((0, yw, wr), (0, -s, 0)))
        hub_face = s * (R * 0.72 + min(wr * 0.25, 22.5) + 1.5)
        kit.append(washer("M5").along((0, hub_face + s * 1.1, wr), (0, -s, 0)))
        kit += screw_joint("M5", (0, hub_face + s * 1.1, wr), (0, -s, 0), grip=1.1 + 3, head="socket", into="tap")
    # base → torso: 4 × M4 up through the 8 mm base deck (heads inside the base) into inserts in the torso floor
    for k in range(4):
        a = math.radians(45 + 90 * k)
        kit += screw_joint("M4", (R * 0.45 * math.cos(a), R * 0.45 * math.sin(a), clear + bh - 8), (0, 0, 1), grip=8,
                          head="socket", boss_len=12, wall=2.5)
    # rear access panel on the torso (−X), 4 countersunk M3 into inserts
    th, tr = P["torso_height"], P["torso_diameter"] / 2
    z = clear + bh
    zp = z + th * 0.45
    rp = tr - (tr - tr * 0.82) * 0.45
    pw, ph = tr * 0.9, th * 0.3
    panel = Pos(-rp + 1.0, 0, zp) * Box(2.0, pw, ph)
    kit.append(named(panel, "Rear access panel", role="shell_top", look_role="accent"))
    for sy in (1, -1):
        for sz in (1, -1):
            kit += screw_joint("M3", (-rp, sy * (pw / 2 - 8), zp + sz * (ph / 2 - 8)), (1, 0, 0), grip=2.0, head="countersunk",
                              boss_len=6, wall=2.5)
    return add_parts(parts, kit, "body")


def build():
    return pro_details(P, build_parts(P))
