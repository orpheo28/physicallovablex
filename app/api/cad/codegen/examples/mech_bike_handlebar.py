"""Bicycle riser handlebar with grips.

A tube swept along a 3D FilletPolyline path (sweep of a Circle placed on Plane(origin=path @ 0, z_dir=path % 0)), a stem clamp around the centre, rubber grips and bar-end plugs on the straight ends. Use sweep along a filleted polyline for bent tubes, rails, handles, frames and pipes.
tags: handlebar, bicycle, bike, tube, sweep, path, polyline, fillet, bent tube, grips, rubber, clamp
"""
import math

from build123d import *

P = {"width": 720.0, "rise": 30.0, "bar_r": 11.0, "clamp_r": 15.9, "clamp_w": 50.0,
     "flat": 70.0, "bend_r": 30.0, "grip_len": 130.0, "grip_r": 16.0, "sweepback": 20.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    hw, rise, cz = P["width"] / 2, P["rise"], P["clamp_r"] + 4  # bar centre above the floor
    sb = P["sweepback"]
    pts = [(-hw, -sb, cz + rise), (-hw + 200, -sb * 0.3, cz + rise), (-P["flat"], 0, cz),
           (P["flat"], 0, cz), (hw - 200, -sb * 0.3, cz + rise), (hw, -sb, cz + rise)]
    path = FilletPolyline(*pts, radius=P["bend_r"])
    # profile sits at the path start, normal to the path tangent there (path % 0)
    bar = sweep(Plane(origin=path @ 0, z_dir=path % 0) * Circle(P["bar_r"]), path=path)
    clamp = Rot(0, 90, 0) * Cylinder(P["clamp_r"] + 4, P["clamp_w"]) - Rot(0, 90, 0) * Cylinder(P["bar_r"], P["clamp_w"] + 2)
    clamp = Pos(0, 0, cz) * clamp
    stem = Pos(0, -60, cz) * Box(40, 90, 28) - Pos(0, 0, cz) * Rot(0, 90, 0) * Cylinder(P["clamp_r"] + 3, P["clamp_w"] + 2)
    parts = [lab(bar, "metal", 1), lab(clamp, "metal", 2), lab(stem, "body", 1)]
    # grips and plugs: along the straight end segments, aligned with the end tangent
    for i, t in enumerate((0.0, 1.0)):
        end = path @ t
        d = path % t if t == 0.0 else -(path % t)  # direction pointing inward from each end
        frame = Plane(origin=end, z_dir=d)
        grip = frame * (Cylinder(P["grip_r"], P["grip_len"], align=(Align.CENTER, Align.CENTER, Align.MIN))
                        - Cylinder(P["bar_r"], 3 * P["grip_len"]))
        plug = frame * Pos(0, 0, -4) * Cylinder(P["grip_r"] + 1, 8)
        parts += [lab(grip, "rubber", i + 1), lab(plug, "accent", i + 1)]
    return parts
