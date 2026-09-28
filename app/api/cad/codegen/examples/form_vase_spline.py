"""Spline-profile vase.

A decorative vase: a Spline through (radius, height) points forms the outer silhouette, closed with straight Lines to the axis, turned into a face on Plane.XZ and revolved about Axis.Z, then shelled open at the top with offset(openings=...). Change the spline points to restyle the form.
tags: vase, vessel, pot, decor, ceramic, spline, revolve, profile, silhouette, shell, offset, organic
"""
import math

from build123d import *

P = {"height": 260.0, "base_r": 45.0, "belly_r": 80.0, "neck_r": 32.0, "lip_r": 44.0, "wall": 3.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    H = P["height"]
    pts = [(P["base_r"], 0), (P["belly_r"], H * 0.3), (P["belly_r"] * 0.85, H * 0.55),
           (P["neck_r"], H * 0.82), (P["lip_r"], H)]
    silhouette = Spline(*pts)
    closing = Polyline((P["lip_r"], H), (0, H), (0, 0), (P["base_r"], 0))
    solid = revolve(make_face(Plane.XZ * (silhouette + closing)), Axis.Z)

    top = solid.faces().sort_by(Axis.Z)[-1]
    try:
        vase = offset(solid, amount=-P["wall"], openings=top)
    except Exception:
        vase = solid
    return [lab(vase, "body", 1)]
