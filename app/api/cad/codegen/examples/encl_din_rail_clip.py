"""DIN-rail clip on a U-channel.

A 35 mm top-hat DIN rail section with a module foot that hooks over its upper lip and snaps with a spring latch
underneath. Rail and clip are 2D `Polyline` profiles on `Plane.YZ` extruded along X — the idiom for any constant
cross-section part (channels, extrusions, rails).
tags: din rail, rail, u-channel, channel, clip, profile, cross-section, extrude, polyline, latch, mounting, steel
"""
import math

from build123d import *

P = {"rail_w": 35.0, "rail_h": 7.5, "rail_t": 1.0, "flange": 5.0, "length": 60.0, "clip_w": 18.0,
     "clip_t": 2.0, "gap": 0.3}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    Wr, Hr, t, f = P["rail_w"], P["rail_h"], P["rail_t"], P["flange"]
    c = Wr / 2 - f  # half-width of the hat's crown
    # Top-hat rail outline (y, z), traced as a closed constant-thickness polygon.
    rail_pts = [(-Wr / 2, Hr - t), (-c, Hr - t), (-c, 0), (c, 0), (c, Hr - t), (Wr / 2, Hr - t),
                (Wr / 2, Hr), (c - t, Hr), (c - t, t), (-c + t, t), (-c + t, Hr), (-Wr / 2, Hr)]
    rail = extrude(Plane.YZ * Polygon(*rail_pts, align=None), amount=P["length"] / 2, both=True)
    # Clip foot: a block above the rail with a hooked leg each side; the lips tuck under the flange edges.
    # Keep Polygon points a simple (non self-intersecting) loop, or the extruded solid is invalid.
    ct, g, top = P["clip_t"], P["gap"], Hr + P["gap"]
    yo, yi, yl = Wr / 2 + g + ct, Wr / 2 + g, Wr / 2 - 1.5
    zu, zl = Hr - t - g, Hr - t - g - ct
    clip_pts = [(-yo, zl), (-yl, zl), (-yl, zu), (-yi, zu), (-yi, top), (yi, top), (yi, zu), (yl, zu),
                (yl, zl), (yo, zl), (yo, top + 10), (-yo, top + 10)]
    clip = extrude(Plane.YZ * Polygon(*clip_pts, align=None), amount=P["clip_w"] / 2, both=True)
    clip = clip - Pos(0, 0, top + ct + 5) * Box(P["clip_w"] - 4, Wr - 6, 10)  # pocket for the module body
    return [lab(rail, "steel", 1), lab(clip, "body", 1)]
