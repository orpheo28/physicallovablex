"""Mug with swept handle.

A coffee mug: cylindrical body, a C-shaped handle swept along a Spline in the XZ plane with a perpendicular Ellipse profile, fused to the body, then the cavity is cut last so the handle ends never poke inside. Rim fillet in try/except.
tags: mug, cup, coffee, tea, handle, sweep, spline, ellipse, boolean, cavity, fillet, kitchen
"""
import math

from build123d import *

P = {"radius": 41.0, "height": 95.0, "wall": 3.5, "base": 6.0, "handle_reach": 30.0,
     "handle_w": 12.0, "handle_t": 8.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, H, t = P["radius"], P["height"], P["wall"]
    base = (Align.CENTER, Align.CENTER, Align.MIN)
    body = Cylinder(R, H, align=base)

    # handle path starts and ends 3 mm inside the wall so the sweep fuses cleanly
    x0, reach = R - 3, R + P["handle_reach"]
    path = Spline((x0, 0, H * 0.78), (reach - 4, 0, H * 0.74), (reach, 0, H * 0.5), (reach - 6, 0, H * 0.25),
                  (x0, 0, H * 0.22), tangents=[(1, 0, 0.1), (-1, 0, -0.2)])
    handle = sweep(Plane(origin=path @ 0, z_dir=path % 0) * Ellipse(P["handle_t"] / 2, P["handle_w"] / 2), path)

    mug = body + handle
    mug = mug - Pos(0, 0, P["base"]) * Cylinder(R - t, H, align=base)
    try:
        mug = fillet(mug.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[-1], radius=t * 0.45)
    except Exception:
        pass
    return [lab(mug, "body", 1)]
