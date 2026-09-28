"""Tripod with splayed legs placed around Z.

Three legs splayed outward and spaced 120 degrees around the Z axis, each made with a reusable rod(p0, p1, r) helper (Plane(origin, z_dir) * Cylinder aligned at MIN) that places a cylinder between two 3D points. Also a centre column, a head plate and rubber feet. Use rod() for any strut, leg, spoke or brace between two points.
tags: tripod, legs, splay, polar, rod, strut, plane, z_dir, camera stand, stand, rubber feet, pattern
"""
import math

from build123d import *

P = {"hub_z": 900.0, "foot_radius": 420.0, "leg_r": 11.0, "hub_r": 38.0, "column_r": 14.0,
     "column_h": 160.0, "foot_r": 16.0, "head_r": 30.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rod(p0, p1, r):
    # cylinder from p0 to p1: a Plane whose z_dir points along the segment
    d = Vector(p1) - Vector(p0)
    return Plane(origin=p0, z_dir=d) * Cylinder(r, d.length, align=(Align.CENTER, Align.CENTER, Align.MIN))


def build():
    hz, fr, lr, fo = P["hub_z"], P["foot_radius"], P["leg_r"], P["foot_r"]
    legs, feet = [], []
    for i in range(3):
        a = math.radians(90 + 120 * i)
        top = (P["hub_r"] * math.cos(a), P["hub_r"] * math.sin(a), hz - 20)
        foot = (fr * math.cos(a), fr * math.sin(a), fo)  # foot sphere centre, sphere touches z=0
        legs.append(rod(top, foot, lr))
        feet.append(Pos(*foot) * Sphere(fo))
    legs_all = legs[0] + legs[1] + legs[2]
    hub = Pos(0, 0, hz - 20) * Cylinder(P["hub_r"] + 6, 40)
    column = Pos(0, 0, hz) * Cylinder(P["column_r"], P["column_h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    ctop = hz + P["column_h"]
    head = Pos(0, 0, ctop) * Sphere(P["head_r"] * 0.7)
    plate = Pos(0, 0, ctop + P["head_r"] * 0.7) * Box(70, 55, 8)
    parts = [lab(legs_all, "metal", 1), lab(hub, "body", 1), lab(column, "metal", 2),
             lab(head, "body", 2), lab(plate, "rubber", 1)]
    return parts + [lab(f, "rubber", i + 2) for i, f in enumerate(feet)]
