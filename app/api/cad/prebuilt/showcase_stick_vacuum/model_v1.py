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

def _basic_build():
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


# === PRO DETAIL === (C5: the seed family 'stick_vacuum' CAD_DETAIL_LEVEL=pro block, appended deterministically, no LLM)
P_PRO = {**{'height': 1180.0, 'wand_diameter': 38.0, 'bin_diameter': 96.0, 'bin_length': 230.0, 'cyclone_count': 10.0, 'motor_diameter': 72.0, 'handle_length': 150.0, 'head_width': 250.0, 'head_depth': 115.0, 'head_height': 58.0}, **P, **{}}


def _f_lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro: motor housing split on its parting line and closed by 3 radial thread-forming screws into
    bosses, floor-head clamshell screwed from underneath, cantilever snap-fit bin latch with a release button."""
    from api.cad.stdparts import add_parts, named, parting_split, screw_joint, snap_fit

    hd, hw, hh = P["head_depth"], P["head_width"], P["head_height"]
    H, wr = P["height"], P["wand_diameter"] / 2
    bl, br = P["bin_length"], P["bin_diameter"] / 2
    unit_z0 = H - bl - 40
    wx = -hd * 0.2
    bx = wx + wr - br * 0.35 + br * 0.6
    z_bin = unit_z0 + 40
    bin_h = bl * 0.55
    zc = z_bin + bin_h + bl * 0.3
    mr = P["motor_diameter"] / 2
    mx = bx - br - mr + 8
    mz0 = z_bin + bin_h * 0.45
    mz1 = zc + bl * 0.12
    # motor housing: two halves on a parting line, 3 radial screws on the rear half (away from the bin)
    motor = next(q for q in parts if q.label == "body.2")
    zs = mz0 + (mz1 - mz0) * 0.55
    motor_lower, motor_upper = parting_split(motor, zs)
    parts = [q for q in parts if q is not motor]
    parts.append(_f_lab(named(motor_lower, "Motor housing (lower)", role="shell_bottom"), "body", 2))
    parts.append(_f_lab(named(motor_upper, "Motor housing (upper)", role="shell_top"), "body", 6))
    kit = []
    for deg in (130, 180, 230):
        a = math.radians(deg)
        at = (mx + mr * math.cos(a), mr * math.sin(a), zs + 6)
        kit += screw_joint("M3", at, (-math.cos(a), -math.sin(a), 0), grip=2.2, head="pan", into="pt", boss_len=8, wall=2.2)
    # floor head: 4 screws from underneath into the upper clamshell
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        kit += screw_joint("M3", (sx * hd * 0.32, sy * (hw / 2 - 20), 4.0), (0, 0, 1), grip=2.2, head="pan", into="pt",
                          boss_len=hh * 0.5, wall=2.2)
    # bin latch: cantilever snap on the bin cap (+X side) + a release button on the shroud collar
    latch = snap_fit(14.0, 1.6, 8.0, "pc_abs")
    kit.append(latch.moved(Location((bx + br + 2.5, 0, z_bin - 12), (0, 0, 1), 180)))
    kit[-1].std_meta = dict(latch.std_meta, name="Bin latch (snap-fit)", group="bin_latch", look_role="accent")
    return add_parts(parts, kit, "accent")


def build():
    r = _basic_build()
    r = r[1] if isinstance(r, tuple) else r
    parts = pro_details(P_PRO, list(r) if isinstance(r, list) else list(r.children))
    return parts
