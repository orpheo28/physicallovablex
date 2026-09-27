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


def build():
    return build_parts(P)
