"""Round thermostat wall unit.

Round smart thermostat: a flat wall back plate, a revolved domed body, a rotating metal outer ring and a recessed
round glass display. The body cross-section is a `Polyline` + `revolve` about Z — the idiom for any axisymmetric
housing. The unit lies face-up (the wall is z = 0).
tags: thermostat, round, wall unit, smart home, revolve, dome, ring, dial, display, glass, axisymmetric, bezel
"""
import math

from build123d import *

P = {"diameter": 84.0, "base_d": 90.0, "base_t": 4.0, "body_h": 22.0, "ring_h": 10.0, "ring_t": 3.0,
     "glass_d": 60.0, "recess": 1.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, bt, H = P["diameter"] / 2, P["base_t"], P["body_h"]
    base = Cylinder(P["base_d"] / 2, bt, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        base = fillet(base.edges().group_by(Axis.Z)[-1], radius=1.5)
    except Exception:
        pass
    # Body section (r, z): straight side then a gentle crown; revolve 360 deg about Z.
    rin = R - P["ring_t"]
    sec = Polyline((0, bt), (rin, bt), (rin, bt + H - 3), (rin - 6, bt + H), (0, bt + H), close=True)
    body = revolve(make_face(Plane.XZ * sec), Axis.Z)
    # Metal ring: an annulus around the body's side, a touch shorter than the body.
    ring = Pos(0, 0, bt + 2) * (Cylinder(R, P["ring_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
                                - Cylinder(rin + 0.2, 50))
    try:
        ring = fillet(ring.edges().group_by(Axis.Z)[-1], radius=0.8)
    except Exception:
        pass
    top = bt + H
    body = body - Pos(0, 0, top) * Cylinder(P["glass_d"] / 2, 2 * P["recess"])
    glass = Pos(0, 0, top - P["recess"] - 0.8) * Cylinder(P["glass_d"] / 2 - 0.2, 0.8, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return [lab(base, "body", 1), lab(body, "body", 2), lab(ring, "metal", 1), lab(glass, "glass", 1)]
