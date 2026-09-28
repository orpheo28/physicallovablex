"""Two-part housing with lid lip.

Base and lid split on a horizontal parting line; the lid carries a thin tongue (lip) that drops inside the base wall
for alignment. Built from one rounded block, `split(..., Plane)` into halves, each hollowed with `offset(openings=)`.
tags: enclosure, housing, lid, base, split line, parting line, lip, tongue and groove, shell, offset, split, two-part
"""
import math

from build123d import *

P = {"length": 110.0, "width": 70.0, "height": 36.0, "corner": 12.0, "wall": 2.0, "split_z": 24.0,
     "lip_h": 3.0, "lip_t": 1.0, "gap": 0.3}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H, t = P["length"], P["width"], P["height"], P["wall"]
    block = extrude(RectangleRounded(L, W, P["corner"]), amount=H)
    try:
        block = fillet(block.edges().group_by(Axis.Z)[-1], radius=6.0)
        block = fillet(block.edges().group_by(Axis.Z)[0], radius=3.0)  # > wall, else the inward offset collapses the fillet
    except Exception:
        pass
    cut = Plane.XY.offset(P["split_z"])
    base = split(block, bisect_by=cut, keep=Keep.BOTTOM)
    lid = split(block, bisect_by=cut, keep=Keep.TOP)
    base = offset(base, amount=-t, openings=base.faces().sort_by(Axis.Z)[-1])
    lid = offset(lid, amount=-t, openings=lid.faces().sort_by(Axis.Z)[0])
    # Lip: a thin ring hanging below the lid, sitting just inside the base wall (clearance = gap).
    li, lo = L - 2 * t - 2 * P["gap"], W - 2 * t - 2 * P["gap"]
    r = P["corner"] - t - P["gap"]
    ring = RectangleRounded(li, lo, r) - RectangleRounded(li - 2 * P["lip_t"], lo - 2 * P["lip_t"], r - P["lip_t"])
    lip = Pos(0, 0, P["split_z"] - P["lip_h"]) * extrude(ring, amount=P["lip_h"])
    lid = lid + lip
    return [lab(base, "body", 1), lab(lid, "accent", 1)]
