"""18650 battery pack in a cell holder.

A grid of cylindrical 18650 cells placed with GridLocations inside a holder block whose cell bores are cut from the same locations, nickel strips across each row and a wrapped outer sleeve. Reusing one Locations object for both parts and cutters keeps them aligned. Use for battery packs, power banks, e-bike packs, cell arrays.
tags: battery, pack, 18650, cells, holder, grid, pattern, power bank, nickel strip, electronics, cylinder, locations
"""
import math

from build123d import *

P = {"cell_r": 9.25, "cell_h": 65.0, "cols": 5, "rows": 3, "gap": 1.5, "holder_h": 12.0,
     "strip_w": 8.0, "strip_t": 0.3, "wall": 2.5}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    r, h, c, rw = P["cell_r"], P["cell_h"], P["cols"], P["rows"]
    pitch = 2 * r + P["gap"]
    L, W = c * pitch + 2 * P["wall"], rw * pitch + 2 * P["wall"]
    hh = P["holder_h"]
    grid = GridLocations(pitch, pitch, c, rw)
    cells = grid * (Pos(0, 0, h / 2 + 1) * Cylinder(r, h))
    caps = grid * (Pos(0, 0, h + 1) * Cylinder(r * 0.45, 1.0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    # bottom and top holders share the grid for their bores
    bores = grid * Cylinder(r + 0.2, 2 * h)
    holders = []
    for z in (hh / 2, h + 2 - hh / 2):
        holders.append(Pos(0, 0, z) * Box(L, W, hh) - bores)
    strips = [Pos(0, (j - (rw - 1) / 2) * pitch, h + 2 + P["strip_t"] / 2) * Box(c * pitch - 4, P["strip_w"], P["strip_t"])
              for j in range(rw)]
    cells_all = cells[0].fuse(*cells[1:])
    caps_all = caps[0].fuse(*caps[1:])
    strip_all = strips[0].fuse(*strips[1:])
    return [lab(cells_all, "coat", 1), lab(caps_all, "metal", 1), lab(holders[0], "body", 1),
            lab(holders[1], "body", 2), lab(strip_all, "metal", 2)]
