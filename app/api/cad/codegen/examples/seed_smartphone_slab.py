"""Smartphone (slab) — seed program of our parametric family.

Smartphone: rounded slab frame, cover glass, rear camera bump with lenses + flash, buttons, USB-C. Full product: parameters dict P, geometry helpers, labelled parts.
tags: smartphone, phone, slab, glass, camera bump, buttons, usb-c, handheld, slab
"""
import math

from build123d import *

P = {
    'width': 71.5,
    'length': 147.0,
    'thickness': 8.2,
    'corner_radius': 10.0,
    'bump_size': 30.0,
    'bump_height': 1.8,
    'lens_count': 2.0,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build_parts(P):
    parts = []
    W, L, T, r = P["width"], P["length"], P["thickness"], P["corner_radius"]
    bh = P["bump_height"]
    z0 = bh  # frame sits on top of the bump height
    frame = Pos(0, 0, z0) * extrude(RectangleRounded(W, L, r), amount=T - 0.7)
    try:
        frame = fillet(frame.edges().group_by(Axis.Z)[0], radius=min(1.6, T * 0.2))
    except Exception:
        pass
    parts.append(lab(frame, "metal", 1))
    parts.append(lab(Pos(0, 0, z0 + T - 0.7) * extrude(RectangleRounded(W - 0.6, L - 0.6, r - 0.3), amount=0.7), "glass", 1))
    # camera island on the back (top-left seen from the back)
    s = P["bump_size"]
    bx, by = W / 2 - s / 2 - 5, L / 2 - s / 2 - 5
    parts.append(lab(Pos(bx, by, 0) * extrude(RectangleRounded(s, s, s * 0.25), amount=bh), "glass", 2))
    n = int(P["lens_count"])
    lr = s * (0.2 if n > 1 else 0.28)
    spots = [(bx - s * 0.2, by + s * 0.2), (bx - s * 0.2, by - s * 0.2), (bx + s * 0.2, by + s * 0.2)][:n] if n > 1 else [(bx, by)]
    for i, (x, y) in enumerate(spots, 1):
        parts.append(lab(Pos(x, y, -0.6) * Cylinder(lr, 1.2, align=(Align.CENTER, Align.CENTER, Align.MIN)), "metal", 1 + i))
        parts.append(lab(Pos(x, y, -0.8) * Cylinder(lr * 0.7, 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN)), "glass", 2 + i))
    parts.append(lab(Pos(bx + s * 0.22, by - s * 0.22, -0.3) * Cylinder(s * 0.07, 0.6, align=(Align.CENTER, Align.CENTER, Align.MIN)), "diffuser", 1))
    # buttons on the right edge (+X): volume rocker + power
    parts.append(lab(Pos(W / 2 + 0.4, L * 0.18, z0 + T / 2) * Box(1.4, 24, 2.6), "button", 1))
    parts.append(lab(Pos(W / 2 + 0.4, L * 0.02, z0 + T / 2) * Box(1.4, 12, 2.6), "button", 2))
    # USB-C port + speaker grille on the bottom edge (-Y)
    parts.append(lab(Pos(0, -L / 2 + 0.4, z0 + T / 2) * Box(9, 1.2, 3.2), "port", 1))
    for i in range(5):
        parts.append(lab(Pos(12 + i * 3.2, -L / 2 + 0.3, z0 + T / 2) * Box(1.6, 0.8, 1.6), "coat", 1 + i))
    return parts


def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro (ODM): 2 countersunk M1.6 at the bottom edge beside the USB-C port into the tapped aluminium
    frame, 6 M1.6 board screws into tapped bosses of the midframe (internal, seen in anatomy / exploded views)."""
    from api.cad.stdparts import add_parts, screw_joint

    W, L, T = P["width"], P["length"], P["thickness"]
    z0 = P["bump_height"]
    kit = []
    for sx in (1, -1):
        kit += screw_joint("M1.6", (sx * 7.0, -L / 2, z0 + T / 2), (0, 1, 0), grip=0.8, head="countersunk", into="tap")
        for y in (L / 2 - 14, 0.0, -L / 2 + 14):
            kit += screw_joint("M1.6", (sx * (W / 2 - 5), y, z0 + T * 0.62), (0, 0, -1), grip=0.8, head="pan", into="tap",
                               boss_len=T * 0.62 - 1.6, wall=1.0)
    return add_parts(parts, kit, "metal")


def build():
    return pro_details(P, build_parts(P))
