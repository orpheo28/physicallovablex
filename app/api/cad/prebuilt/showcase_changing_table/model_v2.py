"""Nordic baby changing table with three safety guards and open storage. Units: mm."""
import math
from build123d import *

P = {
    "length": 900.0,
    "depth": 560.0,
    "height": 875.0,          # Changing deck; guards bring overall height to 1010
    "plywood": 18.0,
    "top_thickness": 18.0,
    "corner_radius": 34.0,
    "leg_width": 76.0,
    "leg_thickness": 18.0,
    "rail_height": 80.0,
    "guard_height": 135.0,
    "guard_thickness": 18.0,
    "shelf_height": 215.0,
    "pad_thickness": 36.0,
    "basket_width": 345.0,
    "basket_depth": 300.0,
    "basket_height": 125.0,
    "basket_wall": 7.0,
    "basket_spacing": 380.0,
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


def build_parts(P):
    L, D, H = P["length"], P["depth"], P["height"]
    t = P["plywood"]
    parts = []

    # Lacquered plywood deck, with its front edge left unobstructed.
    top = Pos(0, 0, H - t) * extrude(
        RectangleRounded(L, D, P["corner_radius"]), amount=t
    )
    parts.append(lab(soft(top, 3.0), "body", 1))

    # Four broad, CNC-cut plywood uprights and under-deck stiffening rails.
    lx, ly = L / 2 - 55, D / 2 - 48
    for i, (x, y) in enumerate(
        [(lx, ly), (-lx, ly), (lx, -ly), (-lx, -ly)]
    ):
        leg = Pos(x, y, 0) * extrude(
            Rectangle(P["leg_width"], P["leg_thickness"]),
            amount=H - t,
            taper=0.25,
        )
        parts.append(lab(soft(leg, 3.0, Axis.Z), "wood", i + 1))

    rh = P["rail_height"]
    rz = H - t - rh / 2
    for i, y in enumerate((ly, -ly)):
        parts.append(lab(
            Pos(0, y, rz) * Box(2 * lx - P["leg_width"], t, rh),
            "body", i + 2,
        ))
    for i, x in enumerate((lx, -lx)):
        parts.append(lab(
            Pos(x, 0, rz) * Box(t, 2 * ly - P["leg_thickness"], rh),
            "body", i + 4,
        ))

    # Continuous back and end guards; the caregiver-facing side stays open.
    gh, gt = P["guard_height"], P["guard_thickness"]
    back = Pos(0, D / 2 - gt / 2, H + gh / 2) * Box(L - 24, gt, gh)
    parts.append(lab(soft(back, 5.0, Axis.X), "body", 6))
    for i, x in enumerate((L / 2 - gt / 2, -L / 2 + gt / 2)):
        side = Pos(x, gt / 2, H + gh / 2) * Box(
            gt, D - gt - 28, gh
        )
        parts.append(lab(soft(side, 5.0, Axis.Y), "body", 7 + i))

    # Open lower supply shelf, with a low retaining lip at its back.
    sh = P["shelf_height"]
    shelf = Pos(0, 0, sh) * Box(2 * lx + 35, 2 * ly + 24, t)
    parts.append(lab(soft(shelf, 3.0, Axis.Z), "wood", 5))
    lip = Pos(0, ly + 6, sh + t / 2 + 24) * Box(
        2 * lx + 20, t, 48
    )
    parts.append(lab(soft(lip, 3.0, Axis.X), "wood", 6))

    # Two open-top storage baskets sit side by side on the shelf.
    bw = P["basket_width"]
    bd = P["basket_depth"]
    bh = P["basket_height"]
    wall = P["basket_wall"]
    basket_z = sh + t / 2
    for i, x in enumerate((-P["basket_spacing"] / 2,
                            P["basket_spacing"] / 2)):
        outer = Pos(x, -10, basket_z) * extrude(
            RectangleRounded(bw, bd, 16), amount=bh
        )
        cavity = Pos(x, -10, basket_z + wall) * extrude(
            RectangleRounded(bw - 2 * wall, bd - 2 * wall, 9),
            amount=bh
        )
        parts.append(lab(outer - cavity, "fabric", i + 1))

    # Removable, rounded wipe-clean changing pad.
    pad = Pos(0, -gt / 2 - 7, H) * extrude(
        RectangleRounded(L - 2 * gt - 38, D - gt - 47, 55),
        amount=P["pad_thickness"],
    )
    parts.append(lab(soft(pad, 10.0), "coat", 1))

    # Two rear wall-anchor tabs, each with a through-hole for a fixing.
    for i, x in enumerate((-320, 320)):
        tab = Pos(x, D / 2 + 2, 967) * Box(48, 5, 76)
        hole = Pos(x, D / 2 + 2, 986) * Rot(90, 0, 0) * Cylinder(5, 12)
        parts.append(lab(tab - hole, "steel", i + 1))

    return parts


def _basic_build():
    return build_parts(P)


# === PRO DETAIL === (C5: the seed family 'furniture' CAD_DETAIL_LEVEL=pro block, appended deterministically, no LLM)
P_PRO = {**{'length': 900.0, 'depth': 560.0, 'height': 900.0, 'top_thickness': 24.0, 'corner_radius': 40.0, 'leg_size': 44.0, 'rail_height': 70.0, 'guard_height': 110.0, 'guard_thickness': 18.0, 'guard_sides': 3.0, 'shelf': 1.0, 'shelf_height': 230.0, 'pad': 1.0, 'pad_thickness': 45.0}, **P, **{}}


def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro: flat-pack joinery — each apron rail joins its leg with 2 fluted beech dowels Ø8 × 35
    (DIN 68150) + 1 Minifix 15 cam connector; the top is screwed from inside the rails with 4 × 30 wood screws."""
    from api.cad.stdparts import add_parts, cam_lock, wood_dowel, wood_screw

    L, D, H = P["length"], P["depth"], P["height"]
    tt, leg, r = P["top_thickness"], P["leg_size"], P["corner_radius"]
    inset = max(r * 0.3, 10.0) + leg / 2
    lx, ly = L / 2 - inset, D / 2 - inset
    rh, rt = P["rail_height"], 18.0
    z_rail = H - tt - rh
    zm = z_rail + rh / 2
    dowel, cam, screw4 = wood_dowel(8.0), cam_lock(), wood_screw(4.0, 30.0)
    kit = []
    for sy in (1, -1):  # front / back rails along X
        for sx in (1, -1):
            ex = sx * (lx - leg / 2)
            for dz in (-rh * 0.25, rh * 0.25):
                kit.append(dowel.along((ex, sy * ly, zm + dz), (1, 0, 0)))
            kit.append(screw4.along((sx * lx * 0.5, sy * (ly - rt / 2 - 3), H - tt - 16), (0, 0, 1)))
    for sx in (1, -1):  # side rails along Y
        for sy in (1, -1):
            ey = sy * (ly - leg / 2)
            for dz in (-rh * 0.25, rh * 0.25):
                kit.append(dowel.along((sx * lx, ey, zm + dz), (0, 1, 0)))
            kit.append(screw4.along((sx * (lx - rt / 2 - 3), sy * ly * 0.5, H - tt - 16), (0, 0, 1)))
    return add_parts(parts, kit, "wood")


def build():
    r = _basic_build()
    r = r[1] if isinstance(r, tuple) else r
    parts = pro_details(P_PRO, list(r) if isinstance(r, list) else list(r.children))
    return parts
