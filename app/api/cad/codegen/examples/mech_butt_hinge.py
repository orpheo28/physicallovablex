"""Butt hinge with alternating knuckles.

Two flat leaves joined by alternating knuckle segments on a shared pin, each leaf with countersunk screw holes. Shows knuckles as Rot(90,0,0) * Cylinder along Y, splitting segments between leaves by index parity, a pin bore cut through every knuckle at once, and countersinks made from Cone + Cylinder cutters.
tags: hinge, butt hinge, knuckle, pin, leaf, countersunk, countersink, cone, boolean, pattern, hardware, joint
"""
import math

from build123d import *

P = {"length": 60.0, "leaf_width": 28.0, "thick": 2.0, "knuckle_r": 4.0, "knuckles": 5,
     "gap": 0.4, "pin_r": 1.5, "hole_r": 1.8, "csk_r": 3.6}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, t, rk = P["length"], P["leaf_width"], P["thick"], P["knuckle_r"]
    n, gap = P["knuckles"], P["gap"]
    axis_z = rk  # pin axis sits one knuckle radius above z=0, leaves lie flat on z=0
    seg = L / n
    left = Pos(-W / 2, 0, t / 2) * Box(W, L, t)
    right = Pos(W / 2, 0, t / 2) * Box(W, L, t)
    for i in range(n):
        y = -L / 2 + seg * (i + 0.5)
        # Rot(90,0,0) turns the cylinder axis from Z to Y
        k = Pos(0, y, axis_z) * Rot(90, 0, 0) * Cylinder(rk, seg - gap)
        if i % 2 == 0:
            left += k
        else:
            right += k
    # one cutter set per leaf: pin bore + three countersunk holes
    bore = Pos(0, 0, axis_z) * Rot(90, 0, 0) * Cylinder(P["pin_r"] + 0.1, L + 2)
    csk_h = P["csk_r"] - P["hole_r"]  # 90 degree countersink
    def holes(x):
        cut = []
        for y in (-L * 0.33, 0, L * 0.33):
            cut.append(Pos(x, y, t / 2) * Cylinder(P["hole_r"], t + 2))
            cut.append(Pos(x, y, t - csk_h) * Cone(P["hole_r"], P["csk_r"], csk_h + 0.01,
                                                   align=(Align.CENTER, Align.CENTER, Align.MIN)))
        return cut
    left = left - bore - holes(-W * 0.55)
    right = right - bore - holes(W * 0.55)
    pin = Pos(0, 0, axis_z) * Rot(90, 0, 0) * Cylinder(P["pin_r"], L + 1)
    head = Pos(0, L / 2 + 0.5, axis_z) * Rot(90, 0, 0) * Cylinder(P["pin_r"] * 1.8, 1.2)
    return [lab(left, "metal", 1), lab(right, "metal", 2), lab(pin + head, "steel", 1)]
