"""Security-camera dome from a split sphere.

A hemispherical dome: a hollow sphere (Sphere - Sphere) cut in half with split(..., bisect_by=Plane.XY, keep=Keep.TOP), lifted onto a cylindrical base with a lens inside. Use split to trim any solid by a plane (Keep.TOP keeps the side the plane normal points to).
tags: dome, hemisphere, sphere, split, keep, camera, security camera, cover, clear, shell, base, lens
"""
import math

from build123d import *

P = {"dome_r": 55.0, "wall": 2.0, "base_r": 62.0, "base_h": 22.0, "lens_r": 14.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, t, bh = P["dome_r"], P["wall"], P["base_h"]
    shell = Sphere(R) - Sphere(R - t)
    dome = Pos(0, 0, bh) * split(shell, bisect_by=Plane.XY, keep=Keep.TOP)

    base = Cylinder(P["base_r"], bh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        base = fillet(base.edges().group_by(Axis.Z)[0], radius=6)
    except Exception:
        pass
    # camera ball inside the dome, lens facing forward-down
    ball = Pos(0, 0, bh + 12) * Sphere(R * 0.55)
    lens = Pos(0, 0, bh + 12) * Rot(0, 60, 0) * Pos(0, 0, R * 0.55) * Cylinder(P["lens_r"], 8)
    return [lab(dome, "clear", 1), lab(base, "body", 1), lab(ball, "accent", 1), lab(lens, "glass", 1)]
