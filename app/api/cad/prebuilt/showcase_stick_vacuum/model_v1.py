"""Cyclone cordless stick vacuum. Units are millimetres; Z is up."""
import math
from build123d import *

P = {
    "height": 1180.0,
    "wand_diameter": 38.0,
    "bin_diameter": 96.0,
    "bin_length": 230.0,
    "cyclone_count": 10,
    "motor_diameter": 72.0,
    "handle_length": 150.0,
    "head_width": 250.0,
    "head_depth": 115.0,
    "head_height": 58.0,
}

def labeled(shape, role, number):
    shape.label = f"{role}.{number}"
    return shape

def rod(start, end, radius):
    a, b = Vector(*start), Vector(*end)
    direction = b - a
    return Plane(origin=(a + b) * 0.5, z_dir=direction) * Cylinder(
        radius, direction.length
    )

def softened(shape, radius):
    try:
        return fillet(shape.edges(), radius=radius)
    except Exception:
        return shape

def build():
    parts = []
    hw, hd, hh = P["head_width"], P["head_depth"], P["head_height"]

    # Low motorized floor head, with a visible brush and rear swivel joint.
    housing = Pos(0, 0, 4) * extrude(
        RectangleRounded(hd, hw, 19), amount=hh - 4
    )
    parts.append(labeled(softened(housing, 8), "accent", 1))
    parts.append(labeled(
        Pos(hd * 0.22, 0, 23) * Rot(90, 0, 0) *
        Cylinder(21, hw - 18), "rubber", 1
    ))
    parts.append(labeled(
        Pos(hd * 0.08, 0, hh - 1) *
        Box(hd * 0.53, hw * 0.79, 4), "clear", 1
    ))
    for i, side in enumerate((-1, 1), 2):
        parts.append(labeled(
            Pos(-hd * 0.35, side * (hw / 2 - 14), 17) *
            Rot(90, 0, 0) * Cylinder(15, 12), "rubber", i
        ))

    wx = -hd * 0.2
    neck_z = hh + 18
    parts.append(labeled(Pos(wx, 0, neck_z) * Sphere(26), "metal", 1))
    parts.append(labeled(
        rod((wx, 0, hh - 8), (wx, 0, neck_z), 20), "accent", 2
    ))

    # Detachable satin-nickel wand and its upper release collar.
    bl, br = P["bin_length"], P["bin_diameter"] / 2
    unit_z0 = P["height"] - bl - 40
    wr = P["wand_diameter"] / 2
    parts.append(labeled(
        rod((wx, 0, neck_z), (wx, 0, unit_z0 + 30), wr), "metal", 2
    ))
    parts.append(labeled(
        rod((wx, 0, unit_z0 - 10), (wx, 0, unit_z0 + 40), wr + 5),
        "accent", 3
    ))
    parts.append(labeled(
        Pos(wx - 17, 0, unit_z0 + 25) * Box(9, 20, 17),
        "button", 1
    ))

    # Removable clear bin, central washable filter, and cyclone assembly.
    bx = wx + wr + br * 0.25
    z_bin = unit_z0 + 40
    bin_h = bl * 0.55
    parts.append(labeled(
        Pos(bx, 0, z_bin) *
        Cylinder(br, bin_h, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "clear", 2
    ))
    parts.append(labeled(
        Pos(bx, 0, z_bin + 17) *
        Cylinder(17, bin_h - 27, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "fabric", 1
    ))
    parts.append(labeled(
        Pos(bx, 0, z_bin - 4) * Cylinder(br + 2, 15),
        "accent", 4
    ))
    parts.append(labeled(
        Pos(bx + br - 3, 0, z_bin + 8) * Box(12, 24, 25),
        "button", 2
    ))
    parts.append(labeled(
        Pos(bx, 0, z_bin + bin_h - 3) * Cylinder(br + 1, 10),
        "rubber", 4
    ))

    shroud_h = bl * 0.3
    parts.append(labeled(
        Pos(bx, 0, z_bin + bin_h) *
        extrude(Circle(br * 0.92), amount=shroud_h, taper=4),
        "metal", 3
    ))
    zc = z_bin + bin_h + shroud_h
    count = P["cyclone_count"]
    ring_radius = br * 0.62
    cone_radius = 7.5
    for i in range(count):
        angle = 2 * math.pi * i / count
        parts.append(labeled(
            Pos(
                bx + ring_radius * math.cos(angle),
                ring_radius * math.sin(angle),
                zc + 16,
            ) * Cone(cone_radius, cone_radius * 0.48, 32),
            "accent", 10 + i
        ))
    parts.append(labeled(
        Pos(bx, 0, zc + 15) * Cylinder(br * 0.35, 38),
        "body", 1
    ))
    parts.append(labeled(
        Pos(bx, 0, zc + 34) * Cylinder(br * 0.45, 5),
        "coat", 1
    ))

    # Rear motor pod, pistol grip and rechargeable battery pack.
    mr = P["motor_diameter"] / 2
    mx = bx - br - mr + 8
    mz0 = z_bin + bin_h * 0.45
    mz1 = zc + bl * 0.12
    motor = Pos(mx, 0, mz0) * extrude(Circle(mr), amount=mz1 - mz0)
    parts.append(labeled(softened(motor, 8), "body", 2))
    parts.append(labeled(
        Pos(mx, 0, mz1 - 2) * Cylinder(mr * 0.78, 6),
        "coat", 2
    ))
    parts.append(labeled(
        Pos(mx, 0, mz1 + 2) * Cylinder(mr * 0.43, 3),
        "metal", 4
    ))

    hl = P["handle_length"]
    hx = mx - mr * 0.6
    top = (hx - 30, 0, mz1 - 20)
    bottom = (hx - 30 - hl * 0.3, 0, mz1 - 20 - hl)
    parts.append(labeled(rod(top, bottom, 17), "body", 3))
    parts.append(labeled(
        rod((mx - mr * 0.2, 0, mz1 - 18), top, 15), "body", 4
    ))
    parts.append(labeled(
        Pos(bottom[0] + 30, 0, bottom[2] + hl * 0.55) *
        Rot(0, -17, 0) * Box(14, 16, 40),
        "button", 3
    ))
    battery = Pos(bottom[0] + 30, 0, bottom[2] - 10) * Box(110, 58, 60)
    parts.append(labeled(softened(battery, 9), "accent", 5))
    parts.append(labeled(
        Pos(bottom[0] + 30, 0, bottom[2] - 41) * Box(92, 46, 4),
        "coat", 3
    ))
    parts.append(labeled(
        rod(
            (bottom[0] + 60, 0, bottom[2] - 10),
            (mx + mr * 0.5, 0, mz0 + 10),
            12,
        ),
        "body", 5
    ))
    parts.append(labeled(
        Pos(bottom[0] + 66, -29, bottom[2] + 7) *
        Box(20, 3, 7), "led", 1
    ))
    return parts
