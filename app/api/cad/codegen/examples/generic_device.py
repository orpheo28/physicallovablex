"""Generic device — the engine's minimal conventions example.

Rounded two-tone handheld device with a button and a status LED: rounded-rectangle extrusions, a top fillet in try/except, role labels.
tags: generic, device, handheld, rounded, two-tone, button, led, enclosure, conventions
"""
import math

from build123d import *

P = {"length": 110.0, "width": 70.0, "height": 32.0, "corner": 14.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H, r = P["length"], P["width"], P["height"], P["corner"]
    lower = extrude(RectangleRounded(L, W, r), amount=H * 0.4)
    upper = Pos(0, 0, H * 0.4) * extrude(RectangleRounded(L, W, r), amount=H * 0.6)
    try:
        upper = fillet(upper.edges().group_by(Axis.Z)[-1], radius=H * 0.25)
    except Exception:
        pass
    button = Pos(0, -W * 0.15, H) * Cylinder(W * 0.12, 3)
    led = Pos(L * 0.3, W * 0.2, H) * Cylinder(2.0, 1.5)
    return [lab(upper, "body", 1), lab(lower, "accent", 1), lab(button, "button", 1), lab(led, "led", 1)]
