"""Base plate with counterbored and countersunk holes.

A machined plate with counterbored holes (through Cylinder + shallow wider Cylinder), countersunk holes (through Cylinder + Cone) and a central bore, all collected in one cutter list and subtracted in a single boolean, then the top edges chamfered with chamfer(edges, length) in try/except. The CounterBoreHole/CounterSinkHole objects need a BuildPart context, so in algebra code build the cutters by hand like this.
tags: plate, base plate, counterbore, countersink, holes, chamfer, cone, machined, fixture, mounting, boolean, pattern
"""
import math

from build123d import *

P = {"length": 160.0, "width": 110.0, "t": 12.0, "cb_hole_r": 3.4, "cb_r": 5.5, "cb_depth": 6.5,
     "cs_hole_r": 2.7, "cs_r": 5.4, "bore_r": 16.0, "chamfer": 1.5}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def counterbore(x, y, top):
    return [Pos(x, y, top / 2) * Cylinder(P["cb_hole_r"], top + 2),
            Pos(x, y, top - P["cb_depth"]) * Cylinder(P["cb_r"], P["cb_depth"] + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))]


def countersink(x, y, top):
    h = P["cs_r"] - P["cs_hole_r"]  # 90 degree included angle: depth = radius difference
    return [Pos(x, y, top / 2) * Cylinder(P["cs_hole_r"], top + 2),
            Pos(x, y, top - h) * Cone(P["cs_hole_r"], P["cs_r"] + 0.01, h + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))]


def build():
    L, W, t = P["length"], P["width"], P["t"]
    plate = Pos(0, 0, t / 2) * Box(L, W, t)
    try:
        # vertical corners first, then the top rim (the reverse order fails: the rim chamfer shortens the corners)
        plate = chamfer(plate.edges().filter_by(Axis.Z), length=P["chamfer"] * 2)
        plate = chamfer(plate.edges().group_by(Axis.Z)[-1], length=P["chamfer"])
    except Exception:
        pass
    cuts = []
    for loc in GridLocations(L - 24, W - 24, 2, 2):  # iterate Locations to get each position
        cuts += counterbore(loc.position.X, loc.position.Y, t)
    for x in (-L * 0.25, L * 0.25):
        cuts += countersink(x, 0, t)
    cuts.append(Pos(0, 0, t / 2) * Cylinder(P["bore_r"], t + 2))
    plate = plate - cuts
    return [lab(plate, "metal", 1)]
