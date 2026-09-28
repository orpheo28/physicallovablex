"""Handheld with rubberised overmold grip.

Handheld tool body (a lofted, tapering handle) with a soft-touch overmold: the rubber part is the intersection of
a slightly offset body with a grip-zone box, minus the core — a clean way to make a conforming skin on part of a
body. Shows `loft`, `offset(amount=+t)` of a solid, `&` intersection and `-` for the overmold.
tags: handheld, handle, grip, overmold, soft touch, rubber, loft, offset, intersection, boolean, tool, ergonomic
"""
import math

from build123d import *

P = {"length": 150.0, "w_base": 36.0, "d_base": 28.0, "w_top": 28.0, "d_top": 22.0, "skin": 1.5,
     "grip_from": 20.0, "grip_to": 95.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L = P["length"]
    sections = [Plane.XY.offset(0) * Ellipse(P["w_base"] / 2, P["d_base"] / 2),
                Plane.XY.offset(L * 0.45) * Ellipse(P["w_base"] / 2 * 0.88, P["d_base"] / 2 * 0.9),
                Plane.XY.offset(L) * Ellipse(P["w_top"] / 2, P["d_top"] / 2)]
    core = loft(sections)
    try:
        core = fillet(core.edges().group_by(Axis.Z)[-1], radius=5.0)
    except Exception:
        pass
    # Skin: grow the body outward by the overmold thickness, keep only the grip zone, remove the core.
    grown = offset(core, amount=P["skin"])
    zone = Pos(0, 0, P["grip_from"]) * Box(100, 100, P["grip_to"] - P["grip_from"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    grip = (grown & zone) - core
    # Finger grooves: thin slices of the skin minus a half-thickness offset -> grooves half the skin deep.
    half = offset(core, amount=P["skin"] / 2)
    for z in (40.0, 55.0, 70.0):
        grip = grip - (Pos(0, 0, z) * Box(100, 100, 1.5) - half)
    trigger = Pos(0, -P["d_base"] / 2 - 2, L * 0.72) * Box(10, 8, 18)
    return [lab(core, "body", 1), lab(grip, "rubber", 1), lab(trigger, "button", 1)]
