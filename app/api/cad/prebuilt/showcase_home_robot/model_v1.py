"""Toy-tidying home robot. Units: mm; Z is up."""
import math
from build123d import *

P = {
    "base_diameter": 460.0,
    "base_height": 130.0,
    "wheel_diameter": 130.0,
    "torso_height": 565.0,
    "torso_diameter": 300.0,
    "head_width": 240.0,
    "head_height": 170.0,
    "mast_height": 65.0,
    "arm_length": 410.0,
    "bin_length": 245.0,
    "bin_width": 260.0,
    "bin_height": 255.0,
    "bin_wall": 12.0,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape

def rod(p1, p2, radius):
    a, b = Vector(*p1), Vector(*p2)
    direction = b - a
    return Plane(origin=(a + b) * 0.5, z_dir=direction) * Cylinder(radius, direction.length)

def soft(shape, radius, axis=None):
    try:
        edges = shape.edges() if axis is None else shape.edges().filter_by(axis)
        return fillet(edges, radius=radius)
    except Exception:
        return shape

def _basic_build():
    parts = []
    radius = P["base_diameter"] / 2
    wheel_radius = P["wheel_diameter"] / 2
    clearance = 35.0
    base_top = clearance + P["base_height"]

    base = Pos(0, 0, clearance) * Cylinder(
        radius, P["base_height"], align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    parts.append(lab(soft(base, 22), "body", 1))

    bumper = Pos(0, 0, clearance + 27) * (
        Cylinder(radius + 4, 28) - Cylinder(radius - 7, 32)
    )
    parts.append(lab(bumper, "rubber", 1))

    for i, side in enumerate((-1, 1)):
        y = side * 174
        wheel = Pos(0, y, wheel_radius) * Rot(90, 0, 0) * Cylinder(wheel_radius, 39)
        hub = Pos(0, y + side * 20, wheel_radius) * Rot(90, 0, 0) * Cylinder(27, 4)
        parts.append(lab(wheel, "rubber", 2 + i))
        parts.append(lab(hub, "metal", 1 + i))

    for i, x in enumerate((-145, 145)):
        parts.append(lab(Pos(x, 0, 18) * Sphere(18), "rubber", 4 + i))

    # Low forward-facing floor scanner.
    scanner = Pos(205, 0, 112) * Box(18, 145, 42)
    parts.append(lab(soft(scanner, 7), "coat", 1))
    for i, y in enumerate((-43, 43)):
        eye = Pos(216, y, 112) * Rot(0, 90, 0) * Cylinder(13, 3)
        parts.append(lab(eye, "glass", 1 + i))

    torso_radius = P["torso_diameter"] / 2
    torso = Pos(0, 0, base_top) * Cone(
        torso_radius, 119, P["torso_height"],
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    parts.append(lab(soft(torso, 10), "body", 2))

    # Open-top rear collection basket, reachable by the single arm.
    bin_x = -216
    bin_bottom = 187
    outer = Pos(bin_x, 0, bin_bottom) * Box(
        P["bin_length"], P["bin_width"], P["bin_height"],
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    inner = Pos(bin_x, 0, bin_bottom + P["bin_wall"]) * Box(
        P["bin_length"] - 2 * P["bin_wall"],
        P["bin_width"] - 2 * P["bin_wall"],
        P["bin_height"],
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    parts.append(lab(soft(outer - inner, 5, Axis.Z), "accent", 1))
    bin_lip = Pos(bin_x, 0, bin_bottom + P["bin_height"] - 8) * (
        Box(P["bin_length"] + 8, P["bin_width"] + 8, 16)
        - Box(P["bin_length"] - 18, P["bin_width"] - 18, 20)
    )
    parts.append(lab(bin_lip, "rubber", 6))

    chest = Pos(145, 0, 515) * Box(12, 126, 108)
    parts.append(lab(soft(chest, 5), "glass", 3))
    parts.append(lab(
        Pos(153, 0, 474) * Rot(0, 90, 0) * Cylinder(7, 3),
        "led", 1
    ))

    neck_z = base_top + P["torso_height"]
    parts.append(lab(
        Pos(0, 0, neck_z) * Cylinder(49, 36, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "coat", 2
    ))

    head_z = neck_z + 36
    head = Pos(0, 0, head_z) * extrude(
        RectangleRounded(P["head_width"], 232, 57),
        amount=P["head_height"]
    )
    parts.append(lab(soft(head, 22), "body", 3))

    visor = Pos(117, 0, head_z + 91) * Box(17, 179, 86)
    parts.append(lab(soft(visor, 7), "glass", 4))
    for i, y in enumerate((-43, 43)):
        parts.append(lab(
            Pos(127, y, head_z + 96) * Rot(0, 90, 0) * Cylinder(11, 3),
            "led", 2 + i
        ))

    mast_z = head_z + P["head_height"]
    parts.append(lab(
        Pos(0, 0, mast_z) * Cylinder(
            12, P["mast_height"], align=(Align.CENTER, Align.CENTER, Align.MIN)
        ),
        "metal", 3
    ))
    parts.append(lab(
        Pos(0, 0, mast_z + P["mast_height"]) * Cylinder(38, 23),
        "coat", 3
    ))
    parts.append(lab(
        Pos(0, 0, mast_z + P["mast_height"]) * (
            Cylinder(39, 10) - Cylinder(34, 14)
        ),
        "glass", 5
    ))

    # Articulated arm reaches down toward toys on the floor.
    shoulder = (28, -165, 654)
    elbow = (157, -184, 438)
    wrist = (270, -184, 318)
    parts.append(lab(Pos(*shoulder) * Sphere(39), "coat", 4))
    parts.append(lab(rod(shoulder, elbow, 29), "body", 4))
    parts.append(lab(Pos(*elbow) * Sphere(32), "coat", 5))
    parts.append(lab(rod(elbow, wrist, 24), "body", 5))
    parts.append(lab(Pos(*wrist) * Sphere(27), "coat", 6))

    palm = (315, -184, 304)
    parts.append(lab(rod(wrist, palm, 20), "metal", 4))
    for i, side in enumerate((-1, 1)):
        finger = Pos(347, -184 + side * 25, 293) * Box(65, 13, 16)
        parts.append(lab(soft(finger, 5), "rubber", 7 + i))

    # Visible rear charging contacts.
    for i, y in enumerate((-35, 35)):
        contact = Pos(-234, y, 105) * Rot(0, 90, 0) * Cylinder(12, 5)
        parts.append(lab(contact, "metal", 5 + i))

    return parts


# === PRO DETAIL === (C5: the seed family 'home_robot' CAD_DETAIL_LEVEL=pro block, appended deterministically, no LLM)
P_PRO = {**{'base_diameter': 460.0, 'base_height': 130.0, 'wheel_diameter': 130.0, 'torso_height': 620.0, 'torso_diameter': 300.0, 'head_diameter': 240.0, 'head_height': 170.0, 'mast_height': 70.0, 'arm': 1.0, 'arm_length': 480.0}, **P, **{}}


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
    r = _basic_build()
    r = r[1] if isinstance(r, tuple) else r
    parts = pro_details(P_PRO, list(r) if isinstance(r, list) else list(r.children))
    return parts
