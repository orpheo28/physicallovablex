"""Minimalist Mini smartphone. Units: mm. Z is up; the camera island rests on z=0."""
import math
from build123d import *

P = {
    "width": 65.0,
    "length": 131.0,
    "thickness": 9.1,
    "bump_height": 1.9,
    "corner_radius": 9.0,
    "camera_island": 22.0,
    "lens_radius": 5.8,
    "glass_thickness": 0.7,
    "ui_height": 0.035,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape

def build_parts(P):
    parts = []
    W, L, T = P["width"], P["length"], P["thickness"]
    r, bh = P["corner_radius"], P["bump_height"]
    gh = P["glass_thickness"]
    top = bh + T
    ui_z = top + 0.012

    # Bead-blasted graphite aluminium slab and edge-to-edge cover glass.
    frame = Pos(0, 0, bh) * extrude(
        RectangleRounded(W, L, r), amount=T - gh
    )
    try:
        frame = fillet(frame.edges().group_by(Axis.Z)[0], radius=1.0)
    except Exception:
        pass
    parts.append(lab(frame, "metal", 1))
    parts.append(lab(
        Pos(0, 0, top - gh) * extrude(
            RectangleRounded(W - 0.7, L - 0.7, r - 0.35), amount=gh
        ), "glass", 1
    ))

    # A quiet, nearly full-face display with a narrow visible glass margin.
    parts.append(lab(
        Pos(0, 0, ui_z) * extrude(
            RectangleRounded(W - 5.0, L - 6.0, r - 2.0),
            amount=P["ui_height"]
        ), "coat", 1
    ))

    # Single rear camera island, seen on the underside of the handset.
    s = P["camera_island"]
    bx, by = -W / 2 + s / 2 + 5, L / 2 - s / 2 - 5
    parts.append(lab(
        Pos(bx, by, 0) * extrude(
            RectangleRounded(s, s, 5.5), amount=bh
        ), "glass", 2
    ))
    lr = P["lens_radius"]
    ring = Cylinder(lr, 0.45, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ring = ring - Cylinder(lr - 1.15, 0.45,
                           align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(Pos(bx - 2.4, by + 2.4, 0.02) * ring, "metal", 2))
    parts.append(lab(
        Pos(bx - 2.4, by + 2.4, 0.03) *
        Cylinder(lr - 1.2, 0.25,
                 align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "glass", 3
    ))
    parts.append(lab(
        Pos(bx + 5.9, by - 6.0, 0.02) *
        Cylinder(1.45, 0.32,
                 align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "diffuser", 1
    ))

    # Tactile side controls and the bottom-edge charging connector.
    parts.append(lab(
        Pos(W / 2 + 0.38, 24, bh + 4.2) * Box(1.25, 19, 2.0),
        "button", 1
    ))
    parts.append(lab(
        Pos(W / 2 + 0.38, 2, bh + 4.2) * Box(1.25, 10, 2.0),
        "button", 2
    ))
    parts.append(lab(
        Pos(0, -L / 2 + 0.15, bh + 4.1) * Box(9.0, 0.45, 2.8),
        "port", 1
    ))
    for i in range(5):
        parts.append(lab(
            Pos(13 + i * 3.0, -L / 2 + 0.12, bh + 4.1) *
            Box(1.35, 0.35, 1.1),
            "coat", i + 2
        ))

    # Restrained monochrome home screen: time, separator, and four tools.
    ink_z = ui_z + P["ui_height"]
    ink_h = 0.025

    def mark(x, y, w, h, number):
        return lab(
            Pos(x, y, ink_z) *
            Box(w, h, ink_h, align=(Align.CENTER, Align.CENTER, Align.MIN)),
            "diffuser", number
        )

    # Thin seven-segment numerals spelling 12:04.
    segments = {
        "1": ("b", "c"),
        "2": ("a", "b", "g", "e", "d"),
        "0": ("a", "b", "c", "d", "e", "f"),
        "4": ("f", "g", "b", "c"),
    }
    layout = {
        "a": (0, 5.5, 5.2, 0.8),
        "g": (0, 0, 5.2, 0.8),
        "d": (0, -5.5, 5.2, 0.8),
        "f": (-2.8, 2.75, 0.8, 5.0),
        "b": (2.8, 2.75, 0.8, 5.0),
        "e": (-2.8, -2.75, 0.8, 5.0),
        "c": (2.8, -2.75, 0.8, 5.0),
    }
    number = 2
    for digit, x in (("1", -16), ("2", -8), ("0", 8), ("4", 16)):
        for segment in segments[digit]:
            dx, dy, sw, sh = layout[segment]
            parts.append(mark(x + dx, 19 + dy, sw, sh, number))
            number += 1
    for y in (22, 16):
        parts.append(lab(
            Pos(0, y, ink_z) *
            Cylinder(0.65, ink_h,
                     align=(Align.CENTER, Align.CENTER, Align.MIN)),
            "diffuser", number
        ))
        number += 1

    parts.append(mark(0, 5, 24, 0.45, number))
    number += 1

    # Four simple, non-social app tiles: call, message, maps, calendar.
    tile_y = -37
    for i, x in enumerate((-21, -7, 7, 21), 1):
        parts.append(lab(
            Pos(x, tile_y, ink_z) *
            extrude(RectangleRounded(10, 10, 2.4), amount=ink_h),
            "accent", i
        ))
    # Sparse pictograms sit just above the tiles.
    icon_z = ink_z + ink_h
    parts.append(lab(
        Pos(-21, tile_y, icon_z) * Rot(0, 0, -35) *
        Box(1.5, 6.0, ink_h), "diffuser", number
    ))
    number += 1
    parts.append(lab(
        Pos(-7, tile_y + 0.5, icon_z) *
        Box(5.5, 3.5, ink_h), "diffuser", number
    ))
    number += 1
    parts.append(lab(
        Pos(7, tile_y, icon_z) *
        extrude(RegularPolygon(3.4, 3), amount=ink_h),
        "diffuser", number
    ))
    number += 1
    parts.append(lab(
        Pos(21, tile_y, icon_z) *
        Box(5.4, 5.0, ink_h), "diffuser", number
    ))
    number += 1
    parts.append(lab(
        Pos(21, tile_y + 1, icon_z + ink_h) *
        Box(5.5, 0.55, ink_h), "coat", 7
    ))

    # Earpiece, front camera, and a subtle gesture bar.
    parts.append(mark(0, 56.5, 12, 0.85, number))
    number += 1
    parts.append(lab(
        Pos(9, 56.5, ink_z) *
        Cylinder(1.05, ink_h,
                 align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "glass", 4
    ))
    parts.append(mark(0, -56, 15, 0.75, number))
    return parts

def build():
    return build_parts(P)
