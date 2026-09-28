"""Hose barb fitting.

A barbed hose connector: the sawtooth barbs are generated in a loop as (radius, height) points of one closed wall Polyline — outer contour up, bore down — revolved about Axis.Z, sitting on an extruded hex nut. Generating profile points programmatically is the clean way to make any repeated axisymmetric feature.
tags: hose barb, fitting, connector, barb, hose, plumbing, revolve, polyline, sawtooth, hex, bore, pneumatic
"""
import math

from build123d import *

P = {"hex_r": 11.0, "hex_h": 10.0, "stem_r": 5.0, "barb_r": 6.6, "barbs": 3, "barb_len": 6.0,
     "bore_r": 3.2, "thread_r": 7.0, "thread_h": 9.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    hh, sr, br, bl, b = P["hex_h"], P["stem_r"], P["barb_r"], P["barb_len"], P["bore_r"]
    z = P["thread_h"] + hh
    pts = [(b, 0), (P["thread_r"], 0), (P["thread_r"], z), (sr, z)]
    for i in range(P["barbs"]):
        z0 = z + i * bl
        pts += [(sr, z0 + 1.0), (br, z0 + bl * 0.8), (sr, z0 + bl * 0.8 + 0.01)]  # ramp out, drop back
    top = z + P["barbs"] * bl + 3
    pts += [(sr, top - 1), (sr - 0.8, top), (b, top)]
    body = revolve(make_face(Plane.XZ * Polyline(*pts, close=True)), Axis.Z)

    nut = Pos(0, 0, P["thread_h"]) * extrude(RegularPolygon(P["hex_r"], 6) - Circle(b), amount=hh)
    try:
        nut = chamfer(nut.edges().filter_by(Axis.Z, reverse=True).group_by(Axis.Z)[-1], length=0.8)
    except Exception:
        pass
    return [lab(body, "metal", 1), lab(nut, "metal", 2)]
