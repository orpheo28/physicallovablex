"""PCB tray with standoffs.

Shallow shelled tray with four hollow standoffs on the PCB hole pattern and a board resting on them, plus a pair
of locating ribs. Shows `offset(openings=)` for the tray, `GridLocations` for the standoff pattern, tube = outer
Cylinder minus inner, and a Box PCB with the same hole pattern cut through.
tags: pcb, circuit board, standoff, spacer, tray, mounting holes, gridlocations, shell, offset, electronics, boss
"""
import math

from build123d import *

P = {"tray_l": 110.0, "tray_w": 80.0, "tray_h": 20.0, "wall": 2.0, "pcb_l": 85.0, "pcb_w": 56.0,
     "pcb_t": 1.6, "hole_dx": 77.0, "hole_dy": 48.0, "standoff_h": 6.0, "standoff_d": 6.0, "screw_d": 2.5}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    t = P["wall"]
    outer = extrude(RectangleRounded(P["tray_l"], P["tray_w"], 6.0), amount=P["tray_h"])
    tray = offset(outer, amount=-t, openings=outer.faces().sort_by(Axis.Z)[-1])
    holes = GridLocations(P["hole_dx"], P["hole_dy"], 2, 2)
    for loc in holes:
        post = Pos(0, 0, t) * loc * Cylinder(P["standoff_d"] / 2, P["standoff_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
        tray = tray + post
    for loc in holes:
        tray = tray - Pos(0, 0, t) * loc * Cylinder(P["screw_d"] / 2, P["standoff_h"] * 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    zb = t + P["standoff_h"]
    pcb = Pos(0, 0, zb) * Box(P["pcb_l"], P["pcb_w"], P["pcb_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    pcb = pcb - [Pos(0, 0, zb) * loc * Cylinder(1.6, 10) for loc in holes]
    chip = Pos(10, 0, zb + P["pcb_t"]) * Box(14, 14, 1.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return [lab(tray, "body", 1), lab(pcb, "accent", 1), lab(chip, "metal", 1)]
