"""Perforated speaker grille.

Round speaker puck whose top plate is perforated with a hexagonal pattern of holes, clipped to a circle.
Shows `HexLocations` for a honeycomb hole pattern, filtering locations by radius, and one batched subtract.
tags: speaker, grille, perforated, holes, hexagonal, honeycomb, hexlocations, pattern, audio, round, boolean
"""
import math

from build123d import *

P = {"diameter": 90.0, "height": 40.0, "plate_t": 1.5, "hole_d": 2.4, "pitch": 3.6, "grille_d": 74.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, H, t = P["diameter"] / 2, P["height"], P["plate_t"]
    body = Cylinder(R, H - t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        body = fillet(body.edges().group_by(Axis.Z)[0], radius=4.0)
    except Exception:
        pass
    plate = Pos(0, 0, H - t) * Cylinder(R - 1.0, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
    n = int(P["grille_d"] / P["pitch"]) + 2
    # HexLocations(radius, xcount, ycount): radius is the hex cell apothem-ish spacing; keep only holes inside the grille.
    holes = [Pos(loc.position.X, loc.position.Y, H - t) * Cylinder(P["hole_d"] / 2, t * 3)
             for loc in HexLocations(P["pitch"] / 2, n, n)
             if math.hypot(loc.position.X, loc.position.Y) < P["grille_d"] / 2 - P["hole_d"]]
    plate = plate - holes
    ring = Pos(0, 0, H - t) * (Cylinder(R, t + 0.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
                               - Cylinder(R - 1.0, 10))
    return [lab(body, "body", 1), lab(plate, "metal", 1), lab(ring, "accent", 1)]
