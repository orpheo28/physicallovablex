"""Mirror-symmetric bracket from one half.

Model only the +X half of a symmetric part (base foot, upright ear with a hole, slotted mounting hole), then join it with mirror(half, about=Plane.YZ). mirror() returns ONLY the mirrored copy, so the whole part is half + mirror(half, ...). Use for any left/right symmetric bracket, yoke, frame or housing.
tags: bracket, mirror, symmetry, symmetric, half, plane, slot, mounting, yoke, sheet metal, holes, boolean
"""
import math

from build123d import *

P = {"span": 120.0, "depth": 40.0, "t": 5.0, "ear_h": 60.0, "ear_w": 30.0, "hole_r": 6.0,
     "slot_len": 14.0, "slot_r": 3.3, "bridge_h": 24.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    S, D, t, eh = P["span"], P["depth"], P["t"], P["ear_h"]
    # +X half: foot plate out to the edge, an upright ear, and half of the centre bridge
    foot = Pos(S / 4, 0, t / 2) * Box(S / 2, D, t)
    ear = Pos(S * 0.22, 0, eh / 2) * Box(t, D, eh)
    ear_top = Pos(S * 0.22, 0, eh) * Rot(0, 90, 0) * Cylinder(D / 2, t)
    bridge = Pos(S * 0.11, 0, P["bridge_h"]) * Box(S * 0.22, D * 0.5, t)
    half = foot + ear + ear_top + bridge
    half -= Pos(S * 0.22, 0, eh) * Rot(0, 90, 0) * Cylinder(P["hole_r"], 3 * t)
    # slotted hole in the foot = SlotCenterToCenter sketch extruded as a cutter
    slot = Pos(S * 0.4, 0, -1) * extrude(SlotCenterToCenter(P["slot_len"], 2 * P["slot_r"], rotation=90), amount=t + 2)
    half -= slot
    try:
        half = fillet(half.edges().filter_by(Axis.Z).group_by(Axis.X)[-1], radius=8)  # round the foot corners
    except Exception:
        pass
    whole = half + mirror(half, about=Plane.YZ)
    return [lab(whole, "metal", 1)]
