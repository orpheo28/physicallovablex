"""Spur gear with bore and keyway.

A spur gear built as a 2D sketch: root Circle plus one trapezoidal tooth Polygon copied with PolarLocations (rotate=True), minus a bore and a keyway Rectangle, then extruded, with a raised hub. Module / tooth-count parameters drive the radii.
tags: gear, spur gear, teeth, sprocket, transmission, polar pattern, polygon, extrude, bore, keyway, hub, mechanical
"""
import math

from build123d import *

P = {"module": 2.0, "teeth": 24, "width": 10.0, "bore": 8.0, "key_w": 3.0, "key_d": 1.5,
     "hub_r": 10.0, "hub_h": 6.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    m, z = P["module"], P["teeth"]
    rp = m * z / 2          # pitch radius
    ra, rf = rp + m, rp - 1.25 * m  # tip and root radii
    step = 2 * math.pi / z

    def polar(r, a):
        return (r * math.cos(a), r * math.sin(a))

    # one tooth centred on +X: wide at the root, narrow at the tip (approximate involute flanks)
    tooth = Polygon(polar(rf - 0.5, -step * 0.30), polar(rf, -step * 0.28), polar(rp, -step * 0.22),
                    polar(ra, -step * 0.12), polar(ra, step * 0.12), polar(rp, step * 0.22),
                    polar(rf, step * 0.28), polar(rf - 0.5, step * 0.30), align=None)
    sketch = Circle(rf) + [loc * tooth for loc in PolarLocations(0, z)]
    sketch = sketch - Circle(P["bore"] / 2)
    sketch = sketch - Pos(P["bore"] / 2, 0) * Rectangle(P["key_d"] * 2, P["key_w"])
    gear = extrude(sketch, amount=P["width"])

    hub = Pos(0, 0, P["width"]) * Cylinder(P["hub_r"], P["hub_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    hub = hub - Cylinder(P["bore"] / 2, 100) - Pos(P["bore"] / 2, 0, 0) * Box(P["key_d"] * 2, P["key_w"], 100)
    return [lab(gear, "steel", 1), lab(hub, "steel", 2)]
