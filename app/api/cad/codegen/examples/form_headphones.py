"""Over-ear headphones: arc-swept headband with ear cups.

A headband made by sweeping a RectangleRounded section along a ThreePointArc (section placed with Plane(origin=arc @ 0, z_dir=arc % 0)), with ear cups built as Cylinders rotated onto the X axis (Rot(0, 90, 0)) and cushions as rubber discs. Shows placing parts at the ends of a path.
tags: headphones, headset, audio, headband, ear cups, cushion, sweep, arc, three point arc, rotate, wearable
"""
import math

from build123d import *

P = {"span": 150.0, "height": 190.0, "band_w": 32.0, "band_t": 7.0, "cup_r": 42.0, "cup_d": 26.0,
     "cushion_d": 16.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    s, H, cr = P["span"] / 2, P["height"], P["cup_r"]
    cz = cr  # cups stand on z=0
    arc = ThreePointArc((-s - P["cup_d"] / 2, 0, cz + cr * 0.6), (0, 0, H), (s + P["cup_d"] / 2, 0, cz + cr * 0.6))
    # section: width along Y (across the head), thickness in the arc plane
    band = sweep(Plane(origin=arc @ 0, z_dir=arc % 0) * RectangleRounded(P["band_t"], P["band_w"], 2.5), arc)

    parts = [lab(band, "body", 1)]
    for i, side in enumerate((-1, 1)):
        x_out = side * (s + P["cup_d"] / 2)
        cup = Pos(x_out, 0, cz) * Rot(0, 90, 0) * Cylinder(cr, P["cup_d"])
        try:
            cup = fillet(cup.edges(), radius=5)
        except Exception:
            pass
        cushion = Pos(side * (s - P["cushion_d"] / 2), 0, cz) * Rot(0, 90, 0) * Cylinder(cr * 0.92, P["cushion_d"])
        parts += [lab(cup, "accent", i + 1), lab(cushion, "rubber", i + 1)]
    return parts
