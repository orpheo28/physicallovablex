"""Rounded handheld remote with button array.

Slim remote control: pill-shaped body with a softened top, a grid of round buttons proud of the surface sitting in
clearance holes, a D-pad ring and an IR window at the nose. Shows `GridLocations` for a keypad, `SlotOverall` extrude.
tags: remote, remote control, handheld, buttons, keypad, button array, gridlocations, pattern, fillet, ir window
"""
import math

from build123d import *

P = {"length": 170.0, "width": 45.0, "height": 16.0, "btn_d": 8.0, "btn_pitch": 12.0, "rows": 4, "cols": 3,
     "clear": 0.4}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H = P["length"], P["width"], P["height"]
    body = extrude(SlotOverall(L, W), amount=H)
    try:
        body = fillet(body.edges().group_by(Axis.Z)[-1], radius=5.0)
        body = fillet(body.edges().group_by(Axis.Z)[0], radius=2.0)
    except Exception:
        pass
    keypad = Pos(-L * 0.12, 0, 0)
    keys = [keypad * loc for loc in GridLocations(P["btn_pitch"], P["btn_pitch"], P["rows"], P["cols"])]
    buttons = []
    for i, loc in enumerate(keys):
        body = body - Pos(0, 0, H - 3) * loc * Cylinder(P["btn_d"] / 2 + P["clear"], 6)
        buttons.append(lab(Pos(0, 0, H - 1.0) * loc * Cylinder(P["btn_d"] / 2, 3.0), "button", i + 1))  # 0.5 mm proud
    # D-pad: an annulus button with a centre OK key.
    dc = Pos(L * 0.2, 0, H)
    body = body - dc * Cylinder(12.5, 6)
    ring = dc * (Cylinder(12.0, 3.0) - Cylinder(6.5, 4))
    ok = dc * Cylinder(6.0, 3.0)
    ir = Pos(L / 2 - 4, 0, H * 0.5) * Box(6, 16, 6)  # IR window pocket at the nose, filled by a diffuser insert
    body = body - ir
    parts = [lab(body, "body", 1), lab(ring, "button", 20), lab(ok, "button", 21), lab(ir, "diffuser", 1)]
    return parts + buttons
