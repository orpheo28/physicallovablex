"""Retro instant camera concept model. Units: mm; front faces -Y; Z is up."""
import math
from build123d import *

P = {
    "width": 151.0,
    "depth": 89.0,
    "body_height": 116.0,
    "corner_radius": 13.0,
    "lens_diameter": 57.0,
    "lens_length": 24.0,
    "lens_height": 72.0,
    "film_slot_width": 108.0,
    "film_slot_height": 3.2,
    "flash_width": 25.0,
    "viewfinder_width": 17.0,
}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rounded_box(width, depth, height, radius):
    shape = Box(width, depth, height, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        shape = fillet(shape.edges().filter_by(Axis.Z), radius=radius)
    except Exception:
        pass
    return shape


def front_disc(x, y, z, radius, thickness):
    return Pos(x, y, z) * Rot(90, 0, 0) * Cylinder(radius, thickness)


def build():
    parts = []
    W, D, H = P["width"], P["depth"], P["body_height"]
    front = -D / 2
    lz = P["lens_height"]

    # Satin PC/ABS enclosure, with a dark leatherette lower wrap.
    body = extrude(
        RectangleRounded(W, D, P["corner_radius"]), amount=H
    )
    try:
        body = fillet(body.edges().group_by(Axis.Z)[-1], radius=5)
    except Exception:
        pass
    parts.append(lab(body, "body", 1))

    wrap_outer = Pos(0, 0, 8) * extrude(
        RectangleRounded(W + 0.8, D + 0.8, P["corner_radius"] + 0.4),
        amount=39,
    )
    wrap_inner = Pos(0, 0, 7) * extrude(
        RectangleRounded(W - 2, D - 2, P["corner_radius"] - 1),
        amount=41,
    )
    parts.append(lab(wrap_outer - wrap_inner, "rubber", 1))

    # Raised front fascia and hinged film-door panel.
    parts.append(lab(
        Pos(0, front - 0.85, 46) * rounded_box(139, 2.0, 65, 9),
        "accent", 1,
    ))
    parts.append(lab(
        Pos(0, front - 1.1, 7) * rounded_box(139, 2.3, 34, 7),
        "coat", 1,
    ))

    # Concentric lens barrel, bezel, focus ring and recessed optical glass.
    ll = P["lens_length"]
    lens_front = front - ll
    parts.append(lab(front_disc(0, front - 3, lz, 34, 5), "coat", 2))
    parts.append(lab(front_disc(0, front - ll / 2, lz, 28.5, ll), "metal", 1))
    parts.append(lab(front_disc(0, lens_front + 1.4, lz, 29.5, 3.5), "coat", 3))
    parts.append(lab(front_disc(0, lens_front - 0.7, lz, 25.2, 1.5), "metal", 2))
    parts.append(lab(front_disc(0, lens_front - 1.6, lz, 21.4, 1.1), "glass", 1))
    parts.append(lab(front_disc(0, lens_front - 2.25, lz, 9, 0.5), "glass", 2))
    parts.append(lab(
        Pos(0, lens_front - 0.9, lz) * Rot(90, 0, 0) * Torus(23.2, 0.85),
        "steel", 1,
    ))

    # Oversized flash and separate optical viewfinder.
    parts.append(lab(
        Pos(-49, front - 2.2, 100) * Box(30, 3, 18),
        "coat", 4,
    ))
    parts.append(lab(
        Pos(-49, front - 4.05, 100) *
        Box(P["flash_width"], 1.2, 13),
        "diffuser", 1,
    ))
    parts.append(lab(
        Pos(51, front - 2.2, 99) * Box(23, 3, 19),
        "coat", 5,
    ))
    parts.append(lab(
        Pos(51, front - 4.05, 99) *
        Box(P["viewfinder_width"], 1.2, 12),
        "glass", 3,
    ))

    # Film-ejection mouth, its two lips, and the door-release control.
    parts.append(lab(
        Pos(0, front - 2.65, 26) *
        Box(P["film_slot_width"], 1.1, P["film_slot_height"]),
        "port", 1,
    ))
    parts.append(lab(
        Pos(0, front - 3.3, 29) * Box(113, 1.5, 1.4),
        "metal", 3,
    ))
    parts.append(lab(
        Pos(0, front - 3.3, 23) * Box(113, 1.5, 1.4),
        "metal", 4,
    ))
    parts.append(lab(
        Pos(59, front - 2.8, 12) * Box(9, 2, 5),
        "button", 1,
    ))

    # Tactile shutter, knurled exposure dial and rear ocular.
    parts.append(lab(
        Pos(51, -19, H) *
        Cylinder(6, 5, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "button", 2,
    ))
    parts.append(lab(
        Pos(-42, 13, H) *
        Cylinder(10, 7, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        "metal", 5,
    ))
    parts.append(lab(
        Pos(-42, 13, H + 7) * Cylinder(7, 1),
        "coat", 6,
    ))
    parts.append(lab(
        Pos(51, D / 2 + 0.8, 99) * Box(18, 2, 13),
        "glass", 4,
    ))
    parts.append(lab(
        Pos(-48, D / 2 + 0.7, 90) * Box(4, 1.5, 4),
        "led", 1,
    ))

    return parts
