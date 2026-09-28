"""Solar smart-irrigation kit: controller, 1-inch solenoid valve, and soil-moisture probe. Units: mm."""
import math
from build123d import *

P = {
    "housing_width": 150.0,
    "housing_depth": 60.0,
    "housing_height": 190.0,
    "corner_radius": 14.0,
    "roof_width": 166.0,
    "roof_depth": 74.0,
    "roof_thickness": 8.0,
    "roof_tilt": 7.0,
    "pipe_diameter": 33.4,
    "valve_length": 170.0,
    "probe_length": 220.0,
    "probe_diameter": 44.0,
    "spacing": 95.0,
}


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


def _basic_build():
    parts = []
    W, D, H = P["housing_width"], P["housing_depth"], P["housing_height"]
    r = P["corner_radius"]

    # Warm-white ASA controller, with a front display and manual override controls.
    body = extrude(RectangleRounded(W, D, r), amount=H)
    parts.append(lab(soft(body, 2, Axis.Y), "body", 1))
    parts.append(lab(Pos(0, -D / 2 - 1, H * 0.68) *
                     Box(W * 0.62, 3, H * 0.24), "glass", 1))
    for i, x in enumerate((-W * 0.20, 0, W * 0.20)):
        button = Pos(x, -D / 2 - 3, H * 0.42) * (
            Rot(90, 0, 0) * Cylinder(9, 5))
        parts.append(lab(button, "button", i + 1))
    parts.append(lab(Pos(W * 0.36, -D / 2 - 2, H * 0.88) *
                     (Rot(90, 0, 0) * Cylinder(3, 3)), "led", 1))

    # Slightly pitched, overhanging photovoltaic roof.
    tilt = P["roof_tilt"]
    roof_pose = Pos(0, -4, H + 9) * Rot(tilt, 0, 0)
    roof = roof_pose * extrude(
        RectangleRounded(P["roof_width"], P["roof_depth"], 9),
        amount=P["roof_thickness"])
    parts.append(lab(roof, "accent", 1))
    panel_pose = roof_pose * Pos(0, 0, P["roof_thickness"])
    parts.append(lab(panel_pose * Box(149, 61, 2,
                     align=(Align.CENTER, Align.CENTER, Align.MIN)), "coat", 1))
    for row in range(3):
        for col in range(4):
            cell = panel_pose * Pos((col - 1.5) * 36, (row - 1) * 19, 2) * Box(
                33, 16, 0.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
            parts.append(lab(cell, "cell", row * 4 + col + 1))

    for i, y in enumerate((-D * 0.2, D * 0.2)):
        gland = Pos(W / 2 + 7, y, H * 0.14) * (
            Rot(0, 90, 0) * Cylinder(7, 14))
        parts.append(lab(gland, "rubber", i + 1))

    # Separate 1-inch pipe and electrically actuated irrigation valve.
    pr = P["pipe_diameter"] / 2
    vl = P["valve_length"]
    nut = pr * 2.3
    cx = W / 2 + P["spacing"] + vl / 2
    zc = nut / math.sqrt(3)
    parts.append(lab(Pos(cx, 0, zc) *
                     (Rot(0, 90, 0) * Cylinder(pr * 1.05, vl)), "coat", 2))
    for i, side in enumerate((1, -1)):
        fitting = Pos(cx + side * (vl / 2 - 13), 0, zc) * (
            Rot(0, 90, 0) * Pos(0, 0, -13) * hex_nut(nut, 26))
        parts.append(lab(fitting, "metal", i + 1))
    valve = Pos(cx, 0, zc) * Box(vl * 0.42, pr * 2.6, pr * 2.4)
    parts.append(lab(soft(valve, pr * 0.35), "coat", 3))
    parts.append(lab(Pos(cx, 0, zc + pr * 1.2) *
                     Cylinder(pr * 1.15, pr * 1.2,
                              align=(Align.CENTER, Align.CENTER, Align.MIN)),
                     "coat", 4))
    coil_z = zc + pr * 2.4
    coil = Pos(cx, 0, coil_z) * Cylinder(
        pr * 0.9, pr * 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(soft(coil, 3), "rubber", 3))
    parts.append(lab(Pos(cx + pr * 0.9, 0, coil_z + pr) *
                     (Rot(0, 90, 0) * Cylinder(4, 30)), "rubber", 4))

    # Ground-insertion probe with exposed soil-contact electrodes.
    L, pd = P["probe_length"], P["probe_diameter"]
    px = -W / 2 - P["spacing"] - pd / 2
    head_h = pd * 1.1
    stake_l = L - head_h
    tip_l = 40.0
    parts.append(lab(Pos(px, 0, tip_l - 1) *
                     Box(pd * 0.45, 9, stake_l - tip_l + 1,
                         align=(Align.CENTER, Align.CENTER, Align.MIN)),
                     "accent", 2))
    parts.append(lab(Pos(px, 0, 0) *
                     Cone(0.5, pd * 0.26, tip_l,
                          align=(Align.CENTER, Align.CENTER, Align.MIN)),
                     "accent", 3))
    for i, side in enumerate((1, -1)):
        electrode = Pos(px + side * pd * 0.12, -5.2, stake_l * 0.3) * Box(
            3, 1.5, stake_l * 0.45)
        parts.append(lab(electrode, "steel", i + 1))
    head = Pos(px, 0, stake_l) * Cylinder(
        pd / 2, head_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(soft(head, pd * 0.2), "body", 2))
    parts.append(lab(Pos(px, 0, stake_l + head_h) *
                     Cylinder(pd * 0.36, 1.5,
                              align=(Align.CENTER, Align.CENTER, Align.MIN)),
                     "cell", 13))
    parts.append(lab(Pos(px, -pd / 2, stake_l + head_h * 0.55) *
                     (Rot(90, 0, 0) * Cylinder(2.5, 3)), "led", 2))
    return parts


# === PRO DETAIL === (C5: the seed family 'irrigation' CAD_DETAIL_LEVEL=pro block, appended deterministically, no LLM)
P_PRO = {**{'housing_width': 150.0, 'housing_depth': 60.0, 'housing_height': 190.0, 'corner_radius': 14.0, 'solar': 1.0, 'pipe_diameter': 33.4, 'valve_length': 170.0, 'probe_length': 220.0, 'probe_diameter': 44.0, 'spacing': 90.0}, **P, **{}}


def _f_lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


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
    parts.append(_f_lab(named(housing, "Controller housing (gasketed)", role="shell_bottom"), "body", 1))
    seal = gasket(lm + cord, dm + cord, rm + cord / 2, cord).at(0, 0, H - 0.75 * cord)
    kit = [seal]
    c = max(r * 0.6, 9.0)
    for sx in (1, -1):
        for sy in (1, -1):
            kit += screw_joint("M4", (sx * (W / 2 - c), sy * (D / 2 - c), H + 10), (0, 0, -1), grip=10, head="pan")
    return add_parts(parts, kit, "body")


def build():
    r = _basic_build()
    r = r[1] if isinstance(r, tuple) else r
    parts = pro_details(P_PRO, list(r) if isinstance(r, list) else list(r.children))
    return parts
