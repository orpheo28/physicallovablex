"""Honeycomb panel.

A framed panel with hexagonal cells from HexLocations * RegularPolygon, subtracted in 2D from the core outline and extruded once, plus a rounded frame. HexLocations(r, nx, ny) takes r as the cell APOTHEM (x pitch = sqrt(3)*r, y pitch = 2*r, flat-topped cells); draw RegularPolygon(r - wall/2, 6, major_radius=False) to leave walls of exactly `wall`. Use for lightweight panels, grilles, bee-hive textures, drone frames.
tags: honeycomb, hexagon, hex, cells, pattern, lightweight, panel, grille, sketch, 2d boolean, extrude, core
"""
import math

from build123d import *

P = {"length": 240.0, "width": 160.0, "t": 10.0, "cell_r": 9.0, "wall": 1.6, "frame": 8.0,
     "frame_h": 12.0, "corner": 10.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, t, cr, fr = P["length"], P["width"], P["t"], P["cell_r"], P["frame"]
    inner_l, inner_w = L - 2 * fr, W - 2 * fr
    nx = int(inner_l / (cr * math.sqrt(3))) + 2
    ny = int(inner_w / (2 * cr)) + 2
    # cell apothem = pitch apothem minus half a wall, so neighbours share a wall of P["wall"]
    cells = HexLocations(cr, nx, ny) * RegularPolygon(cr - P["wall"] / 2, 6, major_radius=False)
    core2d = Rectangle(inner_l + 1, inner_w + 1) - cells
    core = extrude(core2d, amount=t)
    frame2d = RectangleRounded(L, W, P["corner"]) - Rectangle(inner_l, inner_w)
    frame = extrude(frame2d, amount=P["frame_h"])
    return [lab(Pos(0, 0, (P["frame_h"] - t) / 2) * core, "accent", 1), lab(frame, "body", 1)]
