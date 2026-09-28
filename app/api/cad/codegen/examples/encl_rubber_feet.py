"""Base with rubber feet.

Appliance base plate with four domed rubber feet pressed into shallow counterbores near the corners, lifting the
product 3 mm. Shows `revolve` of a profile for a domed foot, `Locations` placement, and counterbore cuts.
tags: rubber feet, feet, bumper, base, foot, revolve, counterbore, locations, appliance, non-slip, underside
"""
import math

from build123d import *

P = {"length": 200.0, "width": 140.0, "base_t": 25.0, "corner": 14.0, "foot_d": 14.0, "foot_h": 3.0,
     "sink": 1.5, "inset": 16.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, fh, sink = P["length"], P["width"], P["foot_h"], P["sink"]
    r = P["foot_d"] / 2
    z0 = fh  # the base sits on the feet
    base = Pos(0, 0, z0) * extrude(RectangleRounded(L, W, P["corner"]), amount=P["base_t"])
    try:
        base = fillet(base.edges().group_by(Axis.Z)[-1], radius=6.0)
    except Exception:
        pass
    # Foot profile in XZ: flat top (inside the counterbore) down to a rounded contact dome.
    prof = Plane.XZ * Polyline((0, 0), (r * 0.8, 0), (r, fh * 0.6), (r, fh + sink), (0, fh + sink), close=True)
    foot = revolve(make_face(prof), Axis.Z)
    dx, dy = L / 2 - P["inset"], W / 2 - P["inset"]
    feet = []
    for i, (x, y) in enumerate([(dx, dy), (-dx, dy), (dx, -dy), (-dx, -dy)]):
        base = base - Pos(x, y, z0) * Cylinder(r + 0.2, sink * 2)
        feet.append(lab(Pos(x, y, 0) * foot, "rubber", i + 1))
    return [lab(base, "body", 1)] + feet
