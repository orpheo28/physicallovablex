"""Jar with external neck thread.

A storage jar: revolved thick-wall profile (so it is hollow by construction), plus an external thread swept along a Helix around the neck. Shows the outward-pointing thread profile on Plane(origin=helix@0, x_dir=radial, z_dir=helix%0).
tags: jar, container, storage, neck, external thread, thread, helix, sweep, revolve, hollow, wall profile, glass
"""
import math

from build123d import *

P = {"body_r": 45.0, "body_h": 95.0, "neck_r": 36.0, "neck_h": 16.0, "wall": 3.0, "base": 4.0,
     "pitch": 4.0, "turns": 1.6, "thread_depth": 1.6}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, H, r, t = P["body_r"], P["body_h"], P["neck_r"], P["wall"]
    top = H + P["neck_h"]
    # closed wall cross-section (outer contour up, inner contour down) -> revolve gives a hollow jar
    wall = Polyline((0, 0), (R - 6, 0), (R, 6), (R, H - 8), (r, H), (r, top), (r - t, top),
                    (r - t, H - 2), (R - t, H - 10), (R - t, P["base"] + 4), (R - t - 4, P["base"]),
                    (0, P["base"]), close=True)
    jar = revolve(make_face(Plane.XZ * wall), Axis.Z)

    helix = Helix(P["pitch"], P["pitch"] * P["turns"], r, center=(0, 0, H + 3))
    plane = Plane(origin=helix @ 0, x_dir=(1, 0, 0), z_dir=helix % 0)
    h = P["pitch"] * 0.3
    tooth = plane * Polygon((-0.3, -h), (P["thread_depth"], 0), (-0.3, h), align=None)
    jar = jar + sweep(tooth, helix, is_frenet=True)
    return [lab(jar, "glass", 1)]
