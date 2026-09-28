"""Ergonomic grip lofted through ellipses.

A tool / controller handle: loft() through a stack of Ellipse sections, each with its own size and X offset (Pos(x, 0, z) * Ellipse(a, b)), gives a palm swell, finger waist and forward lean in one smooth solid. A trigger button and rubber base cap complete it.
tags: grip, handle, ergonomic, tool, controller, joystick, loft, ellipse, sections, organic, trigger, button
"""
import math

from build123d import *

P = {"height": 115.0, "base_a": 22.0, "base_b": 16.0, "swell": 1.18, "waist": 0.9, "lean": 10.0,
     "cap_h": 6.0, "trigger_w": 14.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    H, a, b, c = P["height"], P["base_a"], P["base_b"], P["cap_h"]
    # (height fraction, size factor, forward offset fraction) — bottom to top
    stations = [(0.0, 1.0, 0.0), (0.3, P["swell"], 0.25), (0.6, P["waist"], 0.6), (0.85, 1.0, 0.85), (1.0, 0.8, 1.0)]
    sections = [Pos(P["lean"] * f, 0, c + z * (H - c)) * Ellipse(a * k, b * k) for z, k, f in stations]
    grip = loft(sections)
    try:
        grip = fillet(grip.edges().group_by(Axis.Z)[-1], radius=5)
    except Exception:
        pass

    cap = extrude(Ellipse(a * 1.05, b * 1.05), amount=c)
    trigger = Pos(P["lean"] * 0.8 + a * 0.95, 0, H * 0.78) * Box(8, P["trigger_w"], 18)
    try:
        trigger = fillet(trigger.edges().filter_by(Axis.Y), radius=3)
    except Exception:
        pass
    return [lab(grip, "body", 1), lab(cap, "rubber", 1), lab(trigger, "button", 1)]
