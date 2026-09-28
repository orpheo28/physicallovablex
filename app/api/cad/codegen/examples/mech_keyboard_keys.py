"""Keyboard with a grid of drafted keycaps.

A low case with a recessed deck, rows of keycaps placed with GridLocations, each keycap an extrude(..., taper=deg) of a rounded rectangle (draft angle), fused into one part, plus a wide spacebar. Use for keyboards, keypads, control panels with button arrays.
tags: keyboard, keycap, keys, grid, pattern, draft, taper, extrude, keypad, buttons, desk, computer
"""
import math

from build123d import *

P = {"pitch": 19.05, "cols": 12, "rows": 4, "cap": 18.0, "cap_h": 8.0, "draft": 10.0,
     "case_h": 14.0, "margin": 12.0, "space_units": 6.25}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def keycap(units=1.0):
    p = P["pitch"]
    w = P["cap"] + (units - 1) * p
    cap = extrude(RectangleRounded(w, P["cap"], 2.0), amount=P["cap_h"], taper=P["draft"])
    try:
        cap = fillet(cap.edges().group_by(Axis.Z)[-1], radius=1.0)
    except Exception:
        pass
    return cap


def build():
    p, c, r, ch = P["pitch"], P["cols"], P["rows"], P["case_h"]
    L = c * p + 2 * P["margin"]
    W = (r + 1) * p + 2 * P["margin"]
    case = Pos(0, 0, ch / 2) * Box(L, W, ch)
    case -= Pos(0, 0, ch - 2) * Box(L - 2 * P["margin"] + 4, W - 2 * P["margin"] + 4, 4)
    try:
        case = fillet(case.edges().group_by(Axis.Z)[-1].group_by(SortBy.LENGTH)[-1], radius=3)
    except Exception:
        pass
    deck = ch - 4
    one = keycap()
    rows_y = p / 2  # letter rows sit above the spacebar row
    keys = Pos(0, rows_y, deck) * GridLocations(p, p, c, r) * one  # list of located copies
    space = Pos(0, rows_y - (r + 1) * p / 2, deck) * keycap(P["space_units"])
    mods = [Pos(x, rows_y - (r + 1) * p / 2, deck) * keycap(1.5) for x in (-L / 2 + 40, L / 2 - 40)]
    all_keys = space.fuse(*keys, *mods)
    return [lab(case, "body", 1), lab(all_keys, "button", 1)]
