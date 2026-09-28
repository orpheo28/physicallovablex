"""Knurled control knob.

Rotary knob with a straight-knurled grip (a polar array of shallow grooves cut into the side), a dished top, an
engraved pointer line, and a D-shaft bore. Shows `PolarLocations` for radial patterns, `revolve` for the dish,
and one batched subtract of many cutters.
tags: knob, control knob, dial, knurl, grip, polarlocations, radial pattern, pointer, d-shaft, revolve, boolean
"""
import math

from build123d import *

P = {"diameter": 36.0, "height": 22.0, "grooves": 30, "groove_w": 1.4, "groove_d": 1.0, "dish": 1.2,
     "shaft_d": 6.0, "shaft_flat": 4.5, "skirt_d": 42.0, "skirt_h": 3.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, H = P["diameter"] / 2, P["height"]
    skirt = Cylinder(P["skirt_d"] / 2, P["skirt_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    knob = Pos(0, 0, P["skirt_h"]) * Cylinder(R, H - P["skirt_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        knob = fillet(knob.edges().group_by(Axis.Z)[-1], radius=2.0)
    except Exception:
        pass
    # Knurl: a groove box at radius R, repeated around Z. PolarLocations rotates each copy to face outward.
    grooves = [Pos(0, 0, P["skirt_h"] + 2) * loc * Box(P["groove_d"] * 2, P["groove_w"], H,
                                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
               for loc in PolarLocations(R, P["grooves"])]
    knob = knob - grooves
    # Dished top: revolve a thin lens profile and subtract it.
    dish = revolve(make_face(Plane.XZ * Polyline((0, H - P["dish"]), (R - 3, H), (R - 3, H + 1), (0, H + 1), close=True)), Axis.Z)
    knob = knob - dish
    pointer = Pos(R * 0.55, 0, H - P["dish"] * 0.5) * Box(R * 0.6, 1.2, 2.0)
    knob = knob - pointer  # engraved groove, filled by a coloured pointer insert
    shaft = Cylinder(P["shaft_d"] / 2, 30) - Pos(P["shaft_flat"] - P["shaft_d"] / 2 + 3, 0, 0) * Box(6, 10, 40)
    knob = knob - shaft
    skirt = skirt - Cylinder(P["shaft_d"] / 2 + 1, 20)
    return [lab(knob, "body", 1), lab(skirt, "metal", 1), lab(pointer, "led", 1)]
