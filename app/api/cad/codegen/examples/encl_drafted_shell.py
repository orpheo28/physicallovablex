"""Drafted shell enclosure.

Moulded-plastic box with a draft angle and uniform wall: `extrude(..., taper=deg)` gives the draft, then
`offset(solid, amount=-wall, openings=top_face)` hollows it open at the top. Use for any injection-moulded housing base.
tags: enclosure, housing, box, shell, draft, taper, offset, hollow, wall thickness, injection moulding, fillet
"""
import math

from build123d import *

P = {"length": 120.0, "width": 80.0, "height": 40.0, "corner": 10.0, "draft_deg": 2.0, "wall": 2.2}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H = P["length"], P["width"], P["height"]
    # taper>0 shrinks the profile as it rises. A tub must be wider at its open top, so extrude upward with a
    # positive taper and flip it 180 deg about X (extrude(amount=-H, taper=..) gives a solid offset() cannot shell).
    outer = Pos(0, 0, H) * Rot(180, 0, 0) * extrude(RectangleRounded(L, W, P["corner"]), amount=H, taper=P["draft_deg"])
    try:
        # Fillet only edges AWAY from the opening, with radius > wall; filleting the rim breaks offset().
        outer = fillet(outer.edges().group_by(Axis.Z)[0], radius=4.0)
    except Exception:
        pass
    top = outer.faces().sort_by(Axis.Z)[-1]
    shell = offset(outer, amount=-P["wall"], openings=top)
    return [lab(shell, "body", 1)]
