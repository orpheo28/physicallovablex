"""Rib-stiffened L bracket with gussets.

An angle bracket (horizontal flange + vertical flange) stiffened by triangular gussets drawn as a Polygon on Plane.YZ and extruded symmetrically (both=True), then drilled in one boolean per flange. Use for shelf supports, machine frames, mounting angles and any corner that needs ribs.
tags: bracket, l bracket, angle, gusset, rib, stiffener, polygon, plane, extrude, holes, sheet, structural
"""
import math

from build123d import *

P = {"width": 80.0, "leg_h": 70.0, "leg_d": 70.0, "t": 6.0, "rib_t": 5.0, "rib": 50.0,
     "hole_r": 3.3}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    W, H, D, t, rt, r = P["width"], P["leg_h"], P["leg_d"], P["t"], P["rib_t"], P["rib"]
    # horizontal flange extends toward +Y, vertical flange stands at y=0..t
    base = Pos(0, D / 2, t / 2) * Box(W, D, t)
    wall = Pos(0, t / 2, H / 2) * Box(W, t, H)
    bracket = base + wall
    # Plane.YZ: local x -> global Y, local y -> global Z (right triangle in the inside corner)
    tri = Plane.YZ * Polygon((t, t), (t + r, t), (t, t + r))
    ribs = [Pos(x, 0, 0) * extrude(tri, amount=rt / 2, both=True) for x in (-W / 2 + rt / 2 + 6, 0, W / 2 - rt / 2 - 6)]
    bracket = bracket + ribs
    base_holes = [Pos(x, D * 0.72, t / 2) * Cylinder(P["hole_r"], 3 * t) for x in (-W * 0.28, W * 0.28)]
    wall_holes = [Pos(x, t / 2, H * 0.72) * Rot(90, 0, 0) * Cylinder(P["hole_r"], 3 * t) for x in (-W * 0.28, W * 0.28)]
    bracket = bracket - base_holes - wall_holes
    try:
        bracket = fillet(bracket.edges().filter_by(Axis.X).group_by(Axis.Y)[0].group_by(Axis.Z)[-1], radius=4)
    except Exception:
        pass
    return [lab(Pos(0, -D / 2, 0) * bracket, "steel", 1)]
