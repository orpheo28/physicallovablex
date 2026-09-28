"""Revolved bottle with shelled wall.

A drink bottle made by revolving a half-profile drawn on Plane.XZ (local x = radius, local y = height) about Axis.Z, then hollowed with offset(openings=top face) to a thin wall. Use for any turned, axisymmetric container: bottles, flasks, tumblers.
tags: bottle, flask, container, drink, revolve, profile, polyline, spline, shell, offset, hollow, axisymmetric
"""
import math

from build123d import *

P = {"radius": 34.0, "height": 200.0, "shoulder_z": 135.0, "neck_r": 13.0, "neck_h": 24.0,
     "base_round": 5.0, "wall": 1.6, "cap_h": 20.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, H, S, n = P["radius"], P["height"], P["shoulder_z"], P["neck_r"]
    neck_z = H - P["neck_h"]
    # half-profile in (radius, height) coordinates; Plane.XZ maps local y onto global Z
    lower = Polyline((0, 0), (R - P["base_round"], 0), (R, P["base_round"]), (R, S))
    shoulder = Spline((R, S), (R * 0.7, S + (neck_z - S) * 0.6), (n, neck_z),
                      tangents=[(0, 1), (0, 1)])
    upper = Polyline((n, neck_z), (n, H), (0, H), (0, 0))
    profile = make_face(Plane.XZ * (lower + shoulder + upper))
    solid = revolve(profile, Axis.Z)

    # shell inwards, leaving the flat top of the neck open
    top = solid.faces().sort_by(Axis.Z)[-1]
    try:
        bottle = offset(solid, amount=-P["wall"], openings=top)
    except Exception:
        bottle = solid

    cap = Pos(0, 0, H - P["cap_h"] * 0.6) * Cylinder(n + 2.5, P["cap_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        cap = fillet(cap.edges().group_by(Axis.Z)[-1], radius=2.0)
    except Exception:
        pass
    return [lab(bottle, "clear", 1), lab(cap, "accent", 1)]
