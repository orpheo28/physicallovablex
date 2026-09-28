"""Shell with internal screw bosses.

Open-top housing with four hollow screw bosses at the corners, fused to the floor and walls, each with a pilot hole.
Shows `offset(openings=)`, `Locations` to place repeated features, boss = Cylinder minus pilot Cylinder, then union.
tags: enclosure, housing, screw boss, boss, pilot hole, shell, offset, locations, pattern, fastener, self-tapping
"""
import math

from build123d import *

P = {"length": 100.0, "width": 70.0, "height": 30.0, "corner": 8.0, "wall": 2.0,
     "boss_d": 7.0, "pilot_d": 2.5, "inset": 7.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H, t = P["length"], P["width"], P["height"], P["wall"]
    outer = extrude(RectangleRounded(L, W, P["corner"]), amount=H)
    shell = offset(outer, amount=-t, openings=outer.faces().sort_by(Axis.Z)[-1])
    dx, dy = L / 2 - P["inset"], W / 2 - P["inset"]
    corners = [(dx, dy), (-dx, dy), (dx, -dy), (-dx, -dy)]
    boss_h = H - t - 2.0  # stop 2 mm below the rim so the lid can seat
    for x, y in corners:
        boss = Pos(x, y, t) * Cylinder(P["boss_d"] / 2, boss_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
        shell = shell + boss
    for x, y in corners:  # pilot holes cut after the union so they go through boss and floor
        shell = shell - Pos(x, y, t + 1.0) * Cylinder(P["pilot_d"] / 2, H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return [lab(shell, "body", 1)]
