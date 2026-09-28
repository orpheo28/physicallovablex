"""Battery door with latch tab.

Housing with a rectangular recess in its underside and a flush sliding door carrying a finger latch tab.
Shows cutting a pocket from a face (`Pos * Box` subtract), a separate door part seated in it, and a small grip ridge.
tags: battery door, battery compartment, cover, latch, tab, recess, pocket, housing, boolean, remote, enclosure
"""
import math

from build123d import *

P = {"length": 140.0, "width": 45.0, "height": 22.0, "corner": 10.0, "door_l": 60.0, "door_w": 34.0,
     "door_t": 1.6, "pocket_d": 12.0, "gap": 0.3, "tab_w": 12.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H = P["length"], P["width"], P["height"]
    housing = extrude(RectangleRounded(L, W, P["corner"]), amount=H)
    try:
        housing = fillet(housing.edges().group_by(Axis.Z)[-1], radius=5.0)
    except Exception:
        pass
    cx = -L * 0.2
    # Battery cavity opened from the bottom, plus a shallow seat for the door.
    housing = housing - Pos(cx, 0, 0) * Box(P["door_l"] - 6, P["door_w"] - 6, P["pocket_d"] * 2)
    housing = housing - Pos(cx, 0, 0) * Box(P["door_l"], P["door_w"], P["door_t"] * 2)
    dl, dw = P["door_l"] - 2 * P["gap"], P["door_w"] - 2 * P["gap"]
    door = Pos(cx, 0, P["door_t"] / 2) * Box(dl, dw, P["door_t"])
    # Latch tab: tongue at one end that hooks under the housing, plus a finger ridge on the outside.
    tongue = Pos(cx + dl / 2 + 1.5, 0, P["door_t"] + 0.5) * Box(3.0, P["tab_w"], 1.0)
    grip = Pos(cx + dl / 2 - 6, 0, 0) * Box(1.2, P["tab_w"], 1.0)  # finger groove on the outer face
    door = door + tongue - grip
    return [lab(housing, "body", 1), lab(door, "accent", 1)]
