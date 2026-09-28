"""Door pull handle swept along a spline.

A curved pull handle: an Ellipse profile swept along a 3-D Spline path. The profile is placed perpendicular to the path at its start with Plane(origin=path @ 0, z_dir=path % 0) — the standard sweep recipe — then two cylindrical mounting posts are added.
tags: handle, pull, grip, door, drawer, cabinet, sweep, spline, path, ellipse, profile, curved
"""
import math

from build123d import *

P = {"span": 128.0, "rise": 32.0, "grip_w": 14.0, "grip_t": 9.0, "post_r": 6.0, "post_h": 10.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    s, h = P["span"] / 2, P["rise"]
    z0 = P["post_h"]
    # path starts vertically on top of one post, arcs over, and ends vertically on the other
    path = Spline((-s, 0, z0), (-s * 0.8, 0, z0 + h * 0.8), (0, 0, z0 + h), (s * 0.8, 0, z0 + h * 0.8), (s, 0, z0),
                  tangents=[(0, 0, 1), (0, 0, -1)])
    profile = Plane(origin=path @ 0, z_dir=path % 0) * Ellipse(P["grip_t"] / 2, P["grip_w"] / 2)
    grip = sweep(profile, path)

    base = (Align.CENTER, Align.CENTER, Align.MIN)
    posts = [Pos(x, 0, 0) * Cylinder(P["post_r"], z0 + 1.0, align=base) for x in (-s, s)]
    return [lab(grip, "metal", 1), lab(posts[0], "steel", 1), lab(posts[1], "steel", 2)]
