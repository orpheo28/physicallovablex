"""Pipe tee fitting.

A socket tee: the outer shapes (main run along X, branch along Z, three socket collars) are unioned first, then the union of the bores is subtracted once — the robust order for any branching hollow part. Rot(0, 90, 0) turns a Z cylinder onto the X axis.
tags: pipe, tee, fitting, plumbing, branch, junction, socket, cylinder, boolean, union, subtract, hollow
"""
import math

from build123d import *

P = {"pipe_r": 16.0, "wall": 2.5, "run": 110.0, "branch": 60.0, "socket_r": 20.0, "socket_l": 26.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, t, L, B = P["pipe_r"], P["wall"], P["run"], P["branch"]
    sr, sl = P["socket_r"], P["socket_l"]
    zc = sr  # main axis height so the sockets rest on z=0
    along_x = Rot(0, 90, 0)
    base = (Align.CENTER, Align.CENTER, Align.MIN)

    outer = Pos(0, 0, zc) * along_x * Cylinder(R, L)
    outer += Pos(0, 0, zc) * Cylinder(R, B, align=base)
    outer += [Pos(x, 0, zc) * along_x * Cylinder(sr, sl) for x in (-(L - sl) / 2, (L - sl) / 2)]
    outer += Pos(0, 0, zc + B - sl) * Cylinder(sr, sl, align=base)

    bore = Pos(0, 0, zc) * along_x * Cylinder(R - t, L + 2)
    bore += Pos(0, 0, zc) * Cylinder(R - t, B + 2, align=base)
    tee = outer - bore
    return [lab(tee, "body", 1)]
