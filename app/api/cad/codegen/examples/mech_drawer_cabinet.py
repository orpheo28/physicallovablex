"""Cabinet with a drawer pulled out.

A carcass (outer Box minus a front-open cavity), a drawer box (Box minus Box) with a larger front panel and a bar handle on standoffs, and metal runners. The drawer is built closed and slid out along -Y by a single Pos offset, so changing P["open"] animates it. Use for dressers, filing cabinets, nightstands, tool chests.
tags: cabinet, drawer, furniture, box, hollow, slide, runner, handle, open, storage, wood, dresser
"""
import math

from build123d import *

P = {"width": 500.0, "depth": 450.0, "height": 400.0, "wall": 18.0, "plinth": 60.0,
     "drawer_h": 150.0, "open": 220.0, "front_t": 20.0, "handle_len": 160.0, "clear": 3.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    W, D, H, w, pl = P["width"], P["depth"], P["height"], P["wall"], P["plinth"]
    # carcass: cavity box pushed toward -Y so the front face is open
    carcass = Pos(0, 0, H / 2) * Box(W, D, H)
    carcass -= Pos(0, -w, (H + pl) / 2) * Box(W - 2 * w, D, H - pl - 2 * w)
    carcass -= Pos(0, -D / 2, pl / 2) * Box(W - 2 * w, 40, pl)  # toe kick recess
    cav_w = W - 2 * w - 2 * P["clear"] - 2 * 12  # leave room for the runners
    dh, ft, dd = P["drawer_h"], P["front_t"], D - w - 20
    z0 = pl + w + 5
    box = Pos(0, 0, dh / 2) * (Box(cav_w, dd, dh) - Pos(0, 0, 12) * Box(cav_w - 24, dd - 24, dh))
    front = Pos(0, -dd / 2 - ft / 2, dh / 2 + 8) * Box(W - 2 * w - 4, ft, dh + 30)
    bar = Pos(0, -dd / 2 - ft - 28, dh / 2 + 8) * Rot(0, 90, 0) * Cylinder(6, P["handle_len"])
    posts = [Pos(x, -dd / 2 - ft - 14, dh / 2 + 8) * Rot(90, 0, 0) * Cylinder(5, 28) for x in (-P["handle_len"] * 0.4, P["handle_len"] * 0.4)]
    handle = bar + posts
    # slide the whole drawer out along -Y and set it on its level
    out = Pos(0, w / 2 - P["open"], z0)
    runners = [Pos(sx * (cav_w / 2 + 6 + P["clear"]), w / 2 - P["open"] / 2, z0 + dh / 2) * Box(12, dd, 14) for sx in (-1, 1)]
    return [lab(carcass, "wood", 1), lab(out * box, "wood", 2), lab(out * front, "wood", 3),
            lab(out * handle, "metal", 1), lab(runners[0], "steel", 1), lab(runners[1], "steel", 2)]
