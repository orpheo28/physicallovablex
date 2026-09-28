"""Clevis pivot joint with pin.

A U-shaped clevis fork (block minus a slot), a rod-end tongue swung to an angle about the pin axis, and a headed pin with a washer and cotter. Shows cross holes with Rot(90,0,0) * Cylinder, rotating a sub-part about an Axis through the pin, and reusing one cutter for aligned holes.
tags: clevis, pivot, pin, joint, fork, rod end, tongue, cross hole, rotate, axis, linkage, mechanism
"""
import math

from build123d import *

P = {"fork_w": 30.0, "fork_d": 34.0, "fork_h": 40.0, "slot": 12.0, "pin_r": 4.0,
     "pin_z": 28.0, "tongue_len": 70.0, "tongue_w": 18.0, "angle": 35.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    fw, fd, fh, s, pr, pz = P["fork_w"], P["fork_d"], P["fork_h"], P["slot"], P["pin_r"], P["pin_z"]
    base = Pos(0, 0, 5) * Box(fw + 30, fd, 10)
    fork = Pos(0, 0, fh / 2) * Box(fw, fd, fh) - Pos(0, 0, fh / 2 + 12) * Box(fw + 2, s, fh)
    try:
        fork = fillet(fork.edges().group_by(Axis.Z)[-1].filter_by(Axis.Y), radius=6)
    except Exception:
        pass
    pin_hole = Pos(0, 0, pz) * Rot(90, 0, 0) * Cylinder(pr + 0.2, fd + 10)
    mount = [Pos(x, 0, 5) * Cylinder(3.2, 12) for x in (-(fw / 2 + 8), fw / 2 + 8)]
    clevis = (base + fork) - pin_hole - mount
    # tongue: flat bar with a round eye, built pointing up, then swung about the pin axis
    tl, tw = P["tongue_len"], P["tongue_w"]
    tongue = Pos(0, 0, pz + tl / 2) * Box(tw, s - 1, tl) + Pos(0, 0, pz) * Rot(90, 0, 0) * Cylinder(tw / 2, s - 1)
    tongue = tongue - pin_hole
    tongue = tongue.rotate(Axis((0, 0, pz), (0, 1, 0)), P["angle"])
    rod = Pos(0, 0, pz + tl) * Cylinder(6, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
    rod = rod.rotate(Axis((0, 0, pz), (0, 1, 0)), P["angle"])
    pin = Pos(0, 0, pz) * Rot(90, 0, 0) * Cylinder(pr, fd + 6)
    head = Pos(0, fd / 2 + 3, pz) * Rot(90, 0, 0) * Cylinder(pr * 1.7, 3)
    washer = Pos(0, -fd / 2 - 1, pz) * Rot(90, 0, 0) * (Cylinder(pr * 1.8, 1.5) - Cylinder(pr, 2))
    return [lab(clevis, "steel", 1), lab(tongue, "metal", 1), lab(rod, "metal", 2),
            lab(pin + head, "steel", 2), lab(washer, "steel", 3)]
