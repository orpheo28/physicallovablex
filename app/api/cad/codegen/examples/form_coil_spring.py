"""Helical compression spring.

A coil spring: a Circle wire section placed perpendicular to a Helix at its start (Plane(origin=helix @ 0, z_dir=helix % 0)) and swept with is_frenet=True so the section follows the coil without twisting. Centre the helix at z = wire radius so the spring rests on z=0.
tags: spring, coil, compression spring, helix, sweep, frenet, wire, suspension, mechanical, steel
"""
import math

from build123d import *

P = {"coil_r": 12.0, "wire_r": 1.4, "pitch": 7.0, "turns": 6}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    w = P["wire_r"]
    # Helix(pitch, height, radius, center=...) — height = pitch * turns
    helix = Helix(P["pitch"], P["pitch"] * P["turns"], P["coil_r"], center=(0, 0, w))
    section = Plane(origin=helix @ 0, z_dir=helix % 0) * Circle(w)
    spring = sweep(section, helix, is_frenet=True)
    return [lab(spring, "steel", 1)]
