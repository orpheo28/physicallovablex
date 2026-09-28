"""Finned heatsink.

A base plate with an array of straight fins made from GridLocations * Box (one call returns a list) and fused in a single boolean, plus corner mounting holes and a thermal pad. Use for electronics coolers, motor housings with cooling fins, radiator grilles.
tags: heatsink, fins, array, grid, pattern, cooling, thermal, electronics, aluminium, extrusion, holes, boolean
"""
import math

from build123d import *

P = {"length": 100.0, "width": 80.0, "base_t": 6.0, "fin_t": 1.8, "fin_h": 32.0, "fins": 14,
     "hole_r": 1.7, "pad": 40.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, bt, fh, n = P["length"], P["width"], P["base_t"], P["fin_h"], P["fins"]
    base = Pos(0, 0, bt / 2) * Box(L, W, bt)
    pitch = (W - P["fin_t"]) / (n - 1)
    # GridLocations(x_spacing, y_spacing, x_count, y_count): one column of n fins along Y
    fins = Pos(0, 0, bt + fh / 2) * GridLocations(0, pitch, 1, n) * Box(L, P["fin_t"], fh)
    sink = base + fins  # a Part plus a list fuses everything in one boolean
    # clear two fin gaps across the middle for a clip, and drill the four corner holes
    sink -= Pos(0, 0, bt + fh / 2 + 4) * Box(8, W + 2, fh)
    sink -= Pos(0, 0, bt) * GridLocations(L - 10, W - 10, 2, 2) * Cylinder(P["hole_r"], 3 * bt)
    pad = Pos(0, 0, -0.5) * Box(P["pad"], P["pad"], 1.0)
    return [lab(Pos(0, 0, 1) * sink, "metal", 1), lab(Pos(0, 0, 1) * pad, "coat", 1)]
