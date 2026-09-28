"""Snap-fit cantilever clip.

A cantilever snap arm with a ramped hook, standing on a base plate, next to the mating wall with a catch window.
The hook profile is a Polyline sketch extruded sideways (`Plane.XZ * ...`); window is a Box boolean cut.
tags: snap fit, cantilever, clip, hook, latch, catch, polyline, extrude, plane, boolean, enclosure, assembly
"""
import math

from build123d import *

P = {"arm_len": 16.0, "arm_t": 1.6, "arm_w": 8.0, "hook_depth": 1.2, "hook_len": 3.0, "base_t": 2.0,
     "base_l": 30.0, "base_w": 20.0, "wall_gap": 0.2, "wall_t": 2.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    t, Lr, w = P["arm_t"], P["arm_len"], P["arm_w"]
    base = Pos(0, 0, P["base_t"] / 2) * Box(P["base_l"], P["base_w"], P["base_t"])
    z0 = P["base_t"]
    arm = Pos(0, 0, z0 + Lr / 2) * Box(t, w, Lr)
    # Hook in the XZ plane: flat catch face at the bottom, lead-in ramp at the top (x outward = +x).
    hz = z0 + Lr - P["hook_len"]
    hook_pts = [(t / 2, hz), (t / 2 + P["hook_depth"], hz), (t / 2, z0 + Lr)]
    hook = extrude(Plane.XZ * Polygon(*hook_pts, align=None), amount=w / 2, both=True)
    clip = base + arm + hook
    # Mating wall with a window the hook snaps into.
    wx = t / 2 + P["wall_gap"] + P["wall_t"] / 2
    wall = Pos(wx, 0, z0 + Lr / 2 + 2) * Box(P["wall_t"], w + 8, Lr + 4)
    wall = wall - Pos(wx, 0, hz + 1.0) * Box(P["wall_t"] * 2, w + 0.6, 2.4)
    return [lab(clip, "body", 1), lab(wall, "accent", 1)]
