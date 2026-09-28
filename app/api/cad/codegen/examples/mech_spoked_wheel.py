"""Spoked wheel with rubber tyre.

A hub, a rim ring (Cylinder minus Cylinder), radial spokes from PolarLocations * Box and a Torus tyre, all built lying flat around Z and then stood upright with one Pos * Rot(90,0,0) placement so the tyre touches z=0. Use for bicycle / cart / trolley wheels, handwheels and fans.
tags: wheel, spokes, polar, pattern, rim, hub, tyre, torus, rubber, bicycle, cart, upright
"""
import math

from build123d import *

P = {"rim_r": 250.0, "rim_w": 22.0, "rim_t": 12.0, "tyre_r": 16.0, "hub_r": 22.0, "hub_len": 60.0,
     "spokes": 18, "spoke_w": 3.0, "axle_r": 6.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, tr = P["rim_r"], P["tyre_r"]
    rim = Cylinder(R, P["rim_w"]) - Cylinder(R - P["rim_t"], P["rim_w"] + 2)
    hub = Cylinder(P["hub_r"], P["hub_len"]) - Cylinder(P["axle_r"], P["hub_len"] + 2)
    flanges = [Pos(0, 0, z) * Cylinder(P["hub_r"] + 12, 3) for z in (-P["hub_len"] * 0.35, P["hub_len"] * 0.35)]
    span = R - P["rim_t"] - P["hub_r"] + 4
    mid = P["hub_r"] + span / 2 - 2
    # alternate spokes lean to the two hub flanges (lacing), each is a thin box along the radius
    spokes = []
    for k, z in enumerate((-P["hub_len"] * 0.2, P["hub_len"] * 0.2)):
        n = P["spokes"] // 2
        spokes += PolarLocations(mid, n, start_angle=k * 180 / n) * (Pos(0, 0, z * 0.5) * Box(span, P["spoke_w"], P["spoke_w"]))
    tyre = Torus(R + tr * 0.7, tr)
    # stand the wheel up: axis Z -> Y, then lift so the tyre touches the floor
    up = Pos(0, 0, R + tr * 1.7) * Rot(90, 0, 0)
    spoke_set = spokes[0].fuse(*spokes[1:])
    return [lab(up * tyre, "rubber", 1), lab(up * rim, "metal", 1), lab(up * spoke_set, "steel", 1),
            lab(up * (hub + flanges[0] + flanges[1]), "metal", 2),
            lab(up * Cylinder(P["axle_r"], P["hub_len"] + 20), "steel", 2)]
