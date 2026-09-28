"""Box with a hinged lid rotated open.

A hollow box (outer Box minus inner Box) and a lid modelled closed, then swung open with shape.rotate(Axis(hinge_point, direction), angle) about the real hinge line at the back top edge. Use this idiom for any lid, door or flap that must be shown open at a given angle.
tags: box, lid, hinge, rotate, axis, open, hollow, shell, knuckle, storage, jewelry box, boolean
"""
import math

from build123d import *

P = {"length": 160.0, "width": 110.0, "height": 70.0, "wall": 5.0, "lid_h": 14.0,
     "open_deg": 105.0, "barrel_r": 3.5, "barrel_len": 22.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H, w, lh = P["length"], P["width"], P["height"], P["wall"], P["lid_h"]
    box = Pos(0, 0, H / 2) * Box(L, W, H) - Pos(0, 0, H / 2 + w) * Box(L - 2 * w, W - 2 * w, H)
    lid = Pos(0, 0, H + lh / 2) * Box(L, W, lh) - Pos(0, 0, H + lh / 2 - w) * Box(L - 2 * w, W - 2 * w, lh)
    try:
        lid = fillet(lid.edges().group_by(Axis.Z)[-1], radius=4)
    except Exception:
        pass
    # hinge line: along X at the back (+Y) top edge of the box
    hinge = Axis((0, W / 2 + P["barrel_r"] * 0.3, H), (1, 0, 0))
    barrels = [Pos(x, W / 2 + P["barrel_r"] * 0.3, H) * Rot(0, 90, 0) * Cylinder(P["barrel_r"], P["barrel_len"])
               for x in (-L * 0.3, L * 0.3)]
    # negative angle about +X lifts the front (-Y) edge of the lid upward
    lid_open = lid.rotate(hinge, -P["open_deg"])
    knob = Pos(0, -W / 2 - 3, H + lh / 2) * Box(24, 6, 6)
    knob_open = knob.rotate(hinge, -P["open_deg"])
    return [lab(box, "wood", 1), lab(lid_open, "wood", 2), lab(knob_open, "metal", 1),
            lab(barrels[0], "metal", 2), lab(barrels[1], "metal", 3)]
