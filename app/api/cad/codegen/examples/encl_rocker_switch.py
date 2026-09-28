"""Rocker switch in a housing.

Power-strip style housing with a rectangular bezel opening and a rocker paddle tilted in it. The rocker's curved
top is a 2D profile (`ThreePointArc` + lines) on `Plane.XZ` extruded to width, then tilted with `Rot`. Shows
bezel-frame-as-difference and a tilted inserted part.
tags: rocker switch, switch, power switch, toggle, bezel, housing, arc, extrude, profile, rot, button, power strip
"""
import math

from build123d import *

P = {"length": 90.0, "width": 50.0, "height": 34.0, "corner": 6.0, "open_l": 22.0, "open_w": 14.0,
     "rocker_h": 7.0, "tilt_deg": 8.0, "frame": 2.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H = P["length"], P["width"], P["height"]
    body = extrude(RectangleRounded(L, W, P["corner"]), amount=H)
    try:
        body = fillet(body.edges().group_by(Axis.Z)[-1], radius=3.0)
    except Exception:
        pass
    ol, ow, fr = P["open_l"], P["open_w"], P["frame"]
    # Raised bezel frame: outer rounded rect minus the opening, sitting on the top face.
    frame = Pos(0, 0, H) * extrude(RectangleRounded(ol + 2 * fr, ow + 2 * fr, 2.0) - Rectangle(ol, ow), amount=1.5)
    body = body - Pos(0, 0, H) * Box(ol, ow, 20)  # switch cavity
    # Rocker profile in XZ: flat bottom, arced (concave-to-convex) top so one end sits proud when tilted.
    a = ol / 2 - 0.3
    rh = P["rocker_h"]
    top = ThreePointArc((a, rh * 0.75), (0, rh), (-a, rh * 0.75))
    prof = Plane.XZ * make_face([Line((-a, 0), (a, 0)), Line((a, 0), (a, rh * 0.75)), top, Line((-a, rh * 0.75), (-a, 0))])
    rocker = extrude(prof, amount=(ow - 0.6) / 2, both=True)
    rocker = Pos(0, 0, H - rh + 2.5) * Rot(0, P["tilt_deg"], 0) * rocker
    mark = Pos(-ol * 0.25, 0, H + 2.5) * Rot(0, P["tilt_deg"], 0) * Box(1.0, ow * 0.4, 1.2)  # "I" mark
    rocker = rocker - mark
    return [lab(body, "body", 1), lab(frame, "accent", 1), lab(rocker, "button", 1)]
