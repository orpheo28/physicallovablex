"""Tapered hose nozzle.

A garden-hose nozzle: a hexagonal grip nut (extrude of RegularPolygon) and a hollow tapered cone made by revolving a closed wall cross-section, so the bore narrows toward the tip. Use a closed wall profile in revolve for any hollow turned part with varying bore.
tags: nozzle, hose, spray, tip, taper, cone, revolve, wall profile, hollow, hex, nut, garden
"""
import math

from build123d import *

P = {"hex_r": 16.0, "hex_h": 18.0, "base_r": 13.0, "tip_r": 4.5, "length": 70.0, "wall": 2.2,
     "bore_in": 9.5, "bore_out": 1.6}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    hh, L = P["hex_h"], P["length"]
    top = hh + L
    nut = extrude(RegularPolygon(P["hex_r"], 6), amount=hh) - Cylinder(P["bore_in"], 200)
    try:
        nut = chamfer(nut.edges().group_by(Axis.Z)[-1], length=1.2)
    except Exception:
        pass

    # outer contour going up, inner bore coming down: one closed profile -> hollow cone
    wall = Polyline((P["bore_in"], hh - 2), (P["base_r"], hh - 2), (P["base_r"], hh + 6), (P["tip_r"], top - 3),
                    (P["tip_r"] - 1, top), (P["bore_out"], top), (P["bore_out"], top - 6),
                    (P["bore_in"], hh + 8), close=True)
    cone = revolve(make_face(Plane.XZ * wall), Axis.Z)
    return [lab(nut, "rubber", 1), lab(cone, "accent", 1)]
