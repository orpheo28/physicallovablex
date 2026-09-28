"""Furniture (changing table) — seed program of our parametric family.

Child furniture (changing table / activity table): top, legs, rails, raised safety edges, shelf. Full product: parameters dict P, geometry helpers, labelled parts.
tags: furniture, table, changing table, child, legs, rails, shelf, wood, frame, changing table
"""
import math

from build123d import *

P = {
    'length': 900.0,
    'depth': 560.0,
    'height': 900.0,
    'top_thickness': 24.0,
    'corner_radius': 40.0,
    'leg_size': 44.0,
    'rail_height': 70.0,
    'guard_height': 110.0,
    'guard_thickness': 18.0,
    'guard_sides': 3.0,
    'shelf': 1.0,
    'shelf_height': 230.0,
    'pad': 1.0,
    'pad_thickness': 45.0,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def soft(shape, radius, axis=None):
    """Fillet edges (all, or those parallel to `axis`); keep the raw shape if OCCT refuses."""
    try:
        edges = shape.edges() if axis is None else shape.edges().filter_by(axis)
        return fillet(edges, radius=radius)
    except Exception:
        return shape


def build_parts(P):
    L, D, H = P["length"], P["depth"], P["height"]
    tt, leg, r = P["top_thickness"], P["leg_size"], P["corner_radius"]
    parts = []
    top = Pos(0, 0, H - tt) * extrude(RectangleRounded(L, D, r), amount=tt)
    parts.append(lab(soft(top, min(4.0, tt / 3), None), "wood", 1))

    inset = max(r * 0.3, 10.0) + leg / 2
    lx, ly = L / 2 - inset, D / 2 - inset
    leg_h = H - tt
    for i, (x, y) in enumerate([(lx, ly), (-lx, ly), (lx, -ly), (-lx, -ly)]):
        post = extrude(Rectangle(leg, leg), amount=leg_h, taper=0.6)
        parts.append(lab(Pos(x, y, 0) * soft(post, leg * 0.18, Axis.Z), "wood", 2 + i))

    rh, rt = P["rail_height"], 18.0
    z_rail = H - tt - rh
    parts.append(lab(Pos(0, ly, z_rail + rh / 2) * Box(2 * lx - leg, rt, rh), "body", 1))
    parts.append(lab(Pos(0, -ly, z_rail + rh / 2) * Box(2 * lx - leg, rt, rh), "body", 2))
    parts.append(lab(Pos(lx, 0, z_rail + rh / 2) * Box(rt, 2 * ly - leg, rh), "body", 3))
    parts.append(lab(Pos(-lx, 0, z_rail + rh / 2) * Box(rt, 2 * ly - leg, rh), "body", 4))

    gh, gt, sides = P["guard_height"], P["guard_thickness"], int(P["guard_sides"])
    n = 4
    if gh > 5 and sides > 0:
        z0 = H
        back = Pos(0, D / 2 - gt / 2, z0 + gh / 2) * Box(L - 2 * r * 0.3, gt, gh)
        n += 1
        parts.append(lab(soft(back, gt * 0.45, Axis.X), "body", n))
        for s in ([1] if sides == 2 else [1, -1] if sides == 3 else []):
            side = Pos(s * (L / 2 - gt / 2), gt / 2, z0 + gh / 2) * Box(gt, D - gt - 2 * r * 0.3, gh)
            n += 1
            parts.append(lab(soft(side, gt * 0.45, Axis.Y), "body", n))

    if P["shelf"] >= 0.5:
        sh = P["shelf_height"]
        shelf = Pos(0, 0, sh) * Box(2 * lx + leg * 0.6, 2 * ly + leg * 0.6, 16)
        parts.append(lab(shelf, "wood", 6))
        bw = (2 * lx - leg) / 2 - 30
        for i, x in enumerate([-bw / 2 - 12, bw / 2 + 12]):
            bh = min(170.0, H - tt - rh - sh - 60)
            if bh < 60:
                break
            basket = Pos(x, 0, sh + 8) * extrude(RectangleRounded(bw, 2 * ly - leg - 40, 25), amount=bh)
            hollow = Pos(x, 0, sh + 14) * extrude(RectangleRounded(bw - 12, 2 * ly - leg - 52, 19), amount=bh)
            parts.append(lab(basket - hollow, "fabric", 1 + i))

    if P["pad"] >= 0.5:
        pt = P["pad_thickness"]
        pl = L - 2 * gt - 30 if sides == 3 else L - gt - 30
        pd = D - gt - 30
        px = 0 if sides != 2 else -gt / 2
        pad = Pos(px, -gt / 2, H) * extrude(RectangleRounded(pl, pd, min(60.0, pd / 4)), amount=pt)
        pad = soft(pad, pt * 0.4, None)
        rim = Pos(px, -gt / 2, H + pt - 6) * extrude(RectangleRounded(pl - 90, pd - 90, min(40.0, pd / 6)), amount=8)
        parts.append(lab(pad - rim, "fabric", 3))
    return parts


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
            kit.append(cam.along((ex - sx * 24, sy * (ly - rt / 2), zm), (0, sy, 0), x_dir=(sx, 0, 0)))
            kit.append(screw4.along((sx * lx * 0.5, sy * (ly - rt / 2 - 3), H - tt - 16), (0, 0, 1)))
    for sx in (1, -1):  # side rails along Y
        for sy in (1, -1):
            ey = sy * (ly - leg / 2)
            for dz in (-rh * 0.25, rh * 0.25):
                kit.append(dowel.along((sx * lx, ey, zm + dz), (0, 1, 0)))
            kit.append(cam.along((sx * (lx - rt / 2), ey - sy * 24, zm), (sx, 0, 0), x_dir=(0, sy, 0)))
            kit.append(screw4.along((sx * (lx - rt / 2 - 3), sy * ly * 0.5, H - tt - 16), (0, 0, 1)))
    return add_parts(parts, kit, "wood")


def build():
    return pro_details(P, build_parts(P))
