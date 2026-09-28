"""Bent tube along a filleted path.

A bent handrail / frame tube: a FilletPolyline (straight runs joined by bend-radius arcs) used as a sweep path for an annulus section (Circle - Circle), which gives a hollow tube in one call. The section is placed with Plane(origin=path @ 0, z_dir=path % 0). Use for handlebars, frame tubes, exhaust pipes.
tags: tube, pipe, bent tube, handlebar, frame, rail, sweep, path, arc, fillet polyline, annulus, hollow
"""
import math

from build123d import *

P = {"tube_r": 11.0, "wall": 1.5, "bend_r": 35.0, "width": 420.0, "rise": 220.0, "depth": 160.0,
     "foot_r": 18.0, "foot_h": 8.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    r, W, H, D = P["tube_r"], P["width"] / 2, P["rise"], P["depth"]
    z0 = P["foot_h"]
    # U-shaped frame: up, back, across, forward, down — corners rounded by bend_r
    path = FilletPolyline((-W, 0, z0), (-W, 0, H), (-W, D, H), (W, D, H), (W, 0, H), (W, 0, z0),
                          radius=P["bend_r"])
    section = Plane(origin=path @ 0, z_dir=path % 0) * (Circle(r) - Circle(r - P["wall"]))
    tube = sweep(section, path)

    base = (Align.CENTER, Align.CENTER, Align.MIN)
    feet = [Pos(x, 0, 0) * Cylinder(P["foot_r"], z0, align=base) for x in (-W, W)]
    return [lab(tube, "metal", 1), lab(feet[0], "rubber", 1), lab(feet[1], "rubber", 2)]
