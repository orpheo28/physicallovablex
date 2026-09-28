"""Rectangular-to-round duct transition.

An HVAC adapter: loft() from a Rectangle to a Circle makes the outer transition, a second loft of the same sections shrunk by the wall makes the passage, and the difference is a hollow duct. Flanges are extruded frames. Loft works across different section shapes as long as each is a single closed face.
tags: duct, transition, adapter, hvac, ventilation, rectangle to round, loft, ruled, hollow, flange, boolean, sheet metal
"""
import math

from build123d import *

P = {"rect_w": 160.0, "rect_h": 80.0, "round_r": 50.0, "length": 140.0, "wall": 2.0,
     "flange": 12.0, "flange_t": 4.0, "collar_h": 25.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    W, Hh, R, L, t = P["rect_w"], P["rect_h"], P["round_r"], P["length"], P["wall"]
    outer = loft([Rectangle(W, Hh), Pos(0, 0, L) * Circle(R)])
    inner = loft([Pos(0, 0, -1) * Rectangle(W - 2 * t, Hh - 2 * t), Pos(0, 0, L + 1) * Circle(R - t)])
    duct = outer - inner

    f, ft = P["flange"], P["flange_t"]
    flange = extrude(Rectangle(W + 2 * f, Hh + 2 * f) - Rectangle(W - 2 * t, Hh - 2 * t), amount=ft)
    collar = Pos(0, 0, L) * extrude(Circle(R) - Circle(R - t), amount=P["collar_h"])
    holes = [Pos(x, y, 0) * Cylinder(2.5, 20) for x in (-W / 2 - f / 2, W / 2 + f / 2) for y in (-Hh / 2, Hh / 2)]
    flange = flange - holes
    return [lab(duct, "metal", 1), lab(flange, "steel", 1), lab(collar, "metal", 2)]
