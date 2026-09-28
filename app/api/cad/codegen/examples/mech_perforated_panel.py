"""Perforated panel with a hole grid.

A flanged sheet panel whose perforation is made in 2D first (Rectangle minus GridLocations * Circle, a fast sketch boolean) and extruded once, instead of hundreds of 3D cuts. Use for speaker grilles, vent panels, guards, perforated shelves or covers.
tags: perforated, panel, grille, vent, holes, grid, pattern, sketch, 2d boolean, extrude, sheet metal, speaker
"""
import math

from build123d import *

P = {"length": 300.0, "width": 200.0, "t": 2.0, "flange_h": 15.0, "hole_r": 3.0, "pitch": 10.0,
     "border": 18.0, "mount_r": 2.5}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, t, fh, p, b = P["length"], P["width"], P["t"], P["flange_h"], P["pitch"], P["border"]
    nx = int((L - 2 * b) // p)
    ny = int((W - 2 * b) // p)
    # 2D: outline minus perforation minus mounting holes, then one extrude
    sheet = Rectangle(L, W) - GridLocations(p, p, nx, ny) * Circle(P["hole_r"])
    sheet -= GridLocations(L - b, W - b, 2, 2) * Circle(P["mount_r"])
    face = Pos(0, 0, fh - t) * extrude(sheet, amount=t)
    # downturned flange around the edge: outer box minus inner box
    flange = Pos(0, 0, (fh - t) / 2) * (Box(L, W, fh - t) - Box(L - 2 * t, W - 2 * t, fh))
    panel = face + flange
    return [lab(panel, "metal", 1)]
