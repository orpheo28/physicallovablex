"""Lofted lamp shade.

A table-lamp shade: loft() through several Circle sections at increasing heights gives a smooth bell, then offset(openings=[top, bottom]) turns it into a thin open shell. A metal ring and bulb complete it. Sections must be listed bottom-to-top.
tags: lamp, lamp shade, shade, lighting, bell, loft, sections, circle, shell, offset, thin wall, diffuser
"""
import math

from build123d import *

P = {"bottom_r": 110.0, "top_r": 55.0, "height": 170.0, "wall": 1.5, "ring_r": 18.0, "bulb_r": 30.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    Rb, Rt, H = P["bottom_r"], P["top_r"], P["height"]
    # (height fraction, radius) — a slight waist then a flared skirt
    stations = [(0.0, Rb), (0.15, Rb * 0.93), (0.5, (Rb + Rt) / 2 * 0.95), (0.85, Rt * 1.05), (1.0, Rt)]
    sections = [Pos(0, 0, f * H) * Circle(r) for f, r in stations]
    solid = loft(sections)
    faces = solid.faces().sort_by(Axis.Z)
    try:
        shade = offset(solid, amount=-P["wall"], openings=[faces[0], faces[-1]])
    except Exception:
        shade = solid

    ring = Pos(0, 0, H - 4) * (Cylinder(P["ring_r"], 3) - Cylinder(P["ring_r"] - 4, 3))
    spokes = [Rot(0, 0, a) * Pos((Rt + P["ring_r"]) / 2 - 1, 0, H - 4) * Box(Rt - P["ring_r"], 3, 3)
              for a in (0, 120, 240)]
    bulb = Pos(0, 0, H - 4 - P["bulb_r"] * 1.2) * Sphere(P["bulb_r"])
    return [lab(shade, "fabric", 1), lab(ring + spokes, "metal", 1), lab(bulb, "diffuser", 1)]
