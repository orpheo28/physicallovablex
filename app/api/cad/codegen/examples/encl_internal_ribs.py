"""Enclosure with internal ribs.

Open shelled housing stiffened by a grid of internal ribs on the floor and wall gussets, ribs kept 60% of wall
thickness to avoid sink marks and stopping short of the rim. Shows building rib grids from `GridLocations` of thin
Boxes, clipping them to the cavity with `&` (intersection), then fusing to the shell.
tags: enclosure, housing, ribs, stiffener, gusset, grid, shell, offset, intersection, boolean, injection moulding
"""
import math

from build123d import *

P = {"length": 140.0, "width": 90.0, "height": 35.0, "corner": 10.0, "wall": 2.5, "rib_t": 1.5,
     "rib_h": 12.0, "pitch": 25.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H, t = P["length"], P["width"], P["height"], P["wall"]
    outer = extrude(RectangleRounded(L, W, P["corner"]), amount=H)
    try:
        outer = fillet(outer.edges().group_by(Axis.Z)[0], radius=4.0)  # bottom edges only (away from the opening)
    except Exception:
        pass
    shell = offset(outer, amount=-t, openings=outer.faces().sort_by(Axis.Z)[-1])
    rh, rt = P["rib_h"], P["rib_t"]
    nx, ny = int(L / P["pitch"]), int(W / P["pitch"])
    ribs_x = [loc * Box(rt, W, rh, align=(Align.CENTER, Align.CENTER, Align.MIN)) for loc in GridLocations(P["pitch"], 1, nx, 1)]
    ribs_y = [loc * Box(L, rt, rh, align=(Align.CENTER, Align.CENTER, Align.MIN)) for loc in GridLocations(1, P["pitch"], 1, ny)]
    ribs = Pos(0, 0, t) * Part(children=ribs_x + ribs_y)
    # Clip the rib grid to the cavity so rib ends meet the (filleted) inner walls exactly.
    cavity = outer - shell
    shell = shell + (ribs & cavity)
    return [lab(shell, "body", 1)]
