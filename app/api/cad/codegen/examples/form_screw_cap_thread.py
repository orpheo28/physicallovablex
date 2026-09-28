"""Threaded screw cap with grip ribs.

A bottle cap: a cup (Cylinder minus Cylinder), an internal thread made by sweeping a triangular profile along a Helix, and knurl-like grip ribs placed with PolarLocations. The profile sits on Plane(origin=path@0, x_dir=radial, z_dir=path%0) so it is perpendicular to the helix at its start.
tags: cap, screw cap, lid, closure, thread, internal thread, helix, sweep, polar pattern, ribs, grip, bottle
"""
import math

from build123d import *

P = {"outer_r": 17.0, "height": 16.0, "wall": 1.6, "top": 1.8, "pitch": 3.2, "turns": 2.2,
     "thread_depth": 1.1, "rib_count": 36, "rib_w": 0.9, "rib_h": 0.6}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    Ro, H, w = P["outer_r"], P["height"], P["wall"]
    Ri = Ro - w
    base = (Align.CENTER, Align.CENTER, Align.MIN)
    # cap is modelled open side down, resting on its rim at z=0
    cap = Cylinder(Ro, H, align=base) - Cylinder(Ri, H - P["top"], align=base)

    # internal thread: helix on the inner wall, triangle pointing inwards (-x of the profile plane)
    helix = Helix(P["pitch"], P["pitch"] * P["turns"], Ri, center=(0, 0, 1.5))
    plane = Plane(origin=helix @ 0, x_dir=(1, 0, 0), z_dir=helix % 0)
    d, half = P["thread_depth"], P["pitch"] * 0.3
    tooth = plane * Polygon((0.3, -half), (-d, 0), (0.3, half), align=None)  # 0.3 mm buried in the wall
    thread = sweep(tooth, helix, is_frenet=True)
    cap = cap + thread

    # vertical grip ribs around the outside
    rib = Box(P["rib_h"] * 2, P["rib_w"], H * 0.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ribs = [loc * Pos(Ro, 0, H * 0.05) * rib for loc in PolarLocations(0, P["rib_count"])]
    cap = cap + ribs
    try:
        cap = fillet(cap.edges().group_by(Axis.Z)[-1].sort_by(SortBy.RADIUS)[-1:], radius=1.2)
    except Exception:
        pass
    return [lab(cap, "body", 1)]
