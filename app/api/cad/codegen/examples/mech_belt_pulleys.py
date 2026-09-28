"""Belt drive: two pulleys and a belt.

A driver and a driven pulley (revolved flanged profile with a bore and keyway) on shafts standing on a base plate, and a flat belt made in 2D as make_hull of two offset circles minus make_hull of the pitch circles, then extruded. make_hull(edges) returns the convex outline around both circles, i.e. the exact belt path with tangent spans.
tags: belt, pulley, drive, transmission, make_hull, hull, revolve, shaft, keyway, motor, mechanism, timing belt
"""
import math

from build123d import *

P = {"r1": 30.0, "r2": 55.0, "centre": 170.0, "belt_w": 14.0, "belt_t": 2.5, "flange": 4.0,
     "shaft_r": 6.0, "base_t": 10.0, "hub_h": 10.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def pulley(r, w, fl, bore):
    # half-profile in XZ (x = radius, z = height) revolved about Z: groove between two flanges
    prof = Plane.XZ * Polygon((bore, 0), (r + fl, 0), (r + fl, 1.5), (r, 3), (r, w + 3), (r + fl, w + 4.5),
                              (r + fl, w + 6), (bore, w + 6))
    body = revolve(prof, axis=Axis.Z)
    return body - Pos(bore, 0, (w + 6) / 2) * Box(3, 4, w + 8)  # keyway


def build():
    r1, r2, c, bw, bt = P["r1"], P["r2"], P["centre"], P["belt_w"], P["belt_t"]
    bz = P["base_t"] + P["hub_h"]  # pulley bottom
    x1, x2 = -c / 2, c / 2
    base = Pos(0, 0, P["base_t"] / 2) * Box(c + 2 * r2 + 40, 2 * r2 + 30, P["base_t"])
    base -= Pos(0, 0, P["base_t"] / 2) * GridLocations(c + 2 * r2 + 10, 2 * r2 + 5, 2, 2) * Cylinder(3.4, 30)
    p1 = Pos(x1, 0, bz) * pulley(r1, bw, P["flange"], P["shaft_r"])
    p2 = Pos(x2, 0, bz) * pulley(r2, bw, P["flange"], P["shaft_r"])
    hubs = [Pos(x, 0, P["base_t"]) * Cylinder(P["shaft_r"] * 2.5, P["hub_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
            for x in (x1, x2)]
    shafts = [Pos(x, 0, P["base_t"]) * Cylinder(P["shaft_r"], bw + 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
              for x in (x1, x2)]
    outer = make_hull((Pos(x1, 0) * Circle(r1 + bt) + Pos(x2, 0) * Circle(r2 + bt)).edges())
    inner = make_hull((Pos(x1, 0) * Circle(r1) + Pos(x2, 0) * Circle(r2)).edges())
    belt = Pos(0, 0, bz + 3.2) * extrude(outer - inner, amount=bw - 0.4)
    return [lab(base, "body", 1), lab(p1, "metal", 1), lab(p2, "metal", 2), lab(belt, "rubber", 1),
            lab(hubs[0] + hubs[1], "steel", 1), lab(shafts[0] + shafts[1], "steel", 2)]
