"""Three-blade propeller with spinner.

A drone / boat propeller: one blade lofted through tapered, twisted SlotOverall sections (high pitch at the root, low at the tip, chord widest near the root; use SlotOverall or RectangleRounded, not Ellipse, for twisted lofts), patterned three times around Z, plus a revolved spinner cone. Same twisted-loft idiom as a fan but with free tips.
tags: propeller, prop, drone, boat, blades, twist, taper, loft, sections, spinner, revolve, pattern
"""
import math

from build123d import *

P = {"blades": 3, "radius": 120.0, "hub_r": 12.0, "hub_h": 20.0, "root_pitch": 45.0, "tip_pitch": 12.0,
     "chord_root": 22.0, "chord_max": 30.0, "chord_tip": 10.0, "thickness": 3.0, "spinner_h": 22.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, hr, hh = P["radius"], P["hub_r"], P["hub_h"]
    # (radius fraction, chord, pitch in degrees, thickness)
    table = [(0.0, P["chord_root"], P["root_pitch"], P["thickness"]),
             (0.3, P["chord_max"], (P["root_pitch"] * 2 + P["tip_pitch"]) / 3, P["thickness"] * 0.8),
             (0.7, P["chord_max"] * 0.7, (P["root_pitch"] + P["tip_pitch"] * 2) / 3, P["thickness"] * 0.6),
             (1.0, P["chord_tip"], P["tip_pitch"], P["thickness"] * 0.4)]
    sections = []
    for f, chord, pitch, th in table:
        r = hr - 3 + (R - hr + 3) * f
        sections.append(Plane.YZ.offset(r) * Pos(0, hh / 2) * Rot(0, 0, pitch) * SlotOverall(chord, th))
    blade = loft(sections)

    hub = Cylinder(hr, hh, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Cylinder(2.5, 100)
    prop = hub + [Rot(0, 0, i * 360 / P["blades"]) * blade for i in range(P["blades"])]
    spinner = revolve(make_face(Plane.XZ * Polyline((0, hh), (hr, hh), (hr * 0.5, hh + P["spinner_h"] * 0.7),
                                                    (0, hh + P["spinner_h"]), close=True)), Axis.Z)
    return [lab(prop, "body", 1), lab(spinner, "accent", 1)]
