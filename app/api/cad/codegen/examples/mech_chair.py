"""Wooden chair.

A four-legged chair: legs placed with GridLocations, side stretchers between them, a seat slab with rounded corners, back posts rising from the rear legs and curved-look backrest slats tilted with Rot. Shows placing a set of identical members with one Locations object and tilting a sub-assembly about the seat's rear edge with rotate(Axis(...)).
tags: chair, furniture, wood, legs, grid, stretcher, seat, backrest, slats, rotate, tilt, dining chair
"""
import math

from build123d import *

P = {"seat_w": 440.0, "seat_d": 420.0, "seat_h": 450.0, "seat_t": 25.0, "leg": 38.0,
     "back_h": 420.0, "recline": 8.0, "slats": 3, "slat_h": 55.0, "slat_t": 16.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    W, D, H, st, lg = P["seat_w"], P["seat_d"], P["seat_h"], P["seat_t"], P["leg"]
    sx, sy = W - lg - 20, D - lg - 20  # leg centre spacing
    lh = H - st
    legs = Pos(0, 0, lh / 2) * GridLocations(sx, sy, 2, 2) * Box(lg, lg, lh)
    stretchers = [Pos(x, 0, 150) * Box(lg * 0.6, sy, lg * 0.6) for x in (-sx / 2, sx / 2)]
    stretchers += [Pos(0, y, 250) * Box(sx, lg * 0.5, lg * 0.8) for y in (-sy / 2, sy / 2)]
    frame = legs[0].fuse(*legs[1:], *stretchers)
    seat = Pos(0, 0, H - st / 2) * extrude(RectangleRounded(W, D, 40), amount=st / 2, both=True)
    try:
        seat = fillet(seat.edges().group_by(Axis.Z)[-1], radius=6)
    except Exception:
        pass
    # back: two posts plus slats, built upright then reclined about the rear seat edge
    by = sy / 2
    bh = P["back_h"]
    posts = [Pos(x, by, H + bh / 2) * Box(lg, lg, bh) for x in (-sx / 2, sx / 2)]
    slats = [Pos(0, by, H + bh - 30 - i * (P["slat_h"] + 45)) * Box(sx - lg, P["slat_t"], P["slat_h"])
             for i in range(P["slats"])]
    back = posts[0].fuse(posts[1], *slats)
    back = back.rotate(Axis((0, by, H), (1, 0, 0)), -P["recline"])  # negative about +X leans back toward +Y
    return [lab(frame, "wood", 1), lab(seat, "wood", 2), lab(back, "wood", 3)]
