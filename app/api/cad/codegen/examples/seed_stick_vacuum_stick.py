"""Stick Vacuum (stick) — seed program of our parametric family.

Cordless stick vacuum: floor head, wand, cyclone + clear bin, motor pod, pistol handle, battery. Full product: parameters dict P, geometry helpers, labelled parts.
tags: vacuum, cleaner, stick, wand, cyclone, bin, handle, floor head, appliance, stick
"""
import math

from build123d import *

P = {
    'height': 1180.0,
    'wand_diameter': 38.0,
    'bin_diameter': 96.0,
    'bin_length': 230.0,
    'cyclone_count': 10.0,
    'motor_diameter': 72.0,
    'handle_length': 150.0,
    'head_width': 250.0,
    'head_depth': 115.0,
    'head_height': 58.0,
}

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
    parts.append(lab(named(motor_lower, "Motor housing (lower)", role="shell_bottom"), "body", 2))
    parts.append(lab(named(motor_upper, "Motor housing (upper)", role="shell_top"), "body", 6))
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
    release = Pos(bx + br + 4.5, 0, z_bin + 6) * Box(4, 14, 10)
    kit.append(named(release, "Bin release button", role="button", look_role="button"))
    return add_parts(parts, kit, "accent")


def build():
    return pro_details(P, build_parts(P))
