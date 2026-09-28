"""V-groove pulley.

A belt pulley made in one revolve: the half cross-section (bore, flanges, V-groove, hub) is a Polyline on Plane.XZ revolved about Axis.Z, followed by a set-screw hole. Use revolve whenever a part is fully axisymmetric — it is simpler and more robust than stacking cylinders and cutting grooves.
tags: pulley, sheave, v-groove, belt, wheel, revolve, polyline, profile, groove, hub, bore, mechanical
"""
import math

from build123d import *

P = {"outer_r": 30.0, "width": 16.0, "groove_depth": 7.0, "groove_open": 10.0, "groove_floor": 4.0,
     "bore_r": 4.0, "hub_r": 11.0, "hub_h": 8.0, "setscrew_r": 1.5}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, W, b = P["outer_r"], P["width"], P["bore_r"]
    mid = W / 2
    o, f = P["groove_open"] / 2, P["groove_floor"] / 2
    rg = R - P["groove_depth"]
    top = W + P["hub_h"]
    profile = Polyline((b, 0), (R, 0), (R, mid - o), (rg, mid - f), (rg, mid + f), (R, mid + o), (R, W),
                       (P["hub_r"], W), (P["hub_r"], top), (b, top), close=True)
    pulley = revolve(make_face(Plane.XZ * profile), Axis.Z)

    # radial set-screw hole through the hub
    screw = Pos(0, 0, W + P["hub_h"] / 2) * Rot(0, 90, 0) * Cylinder(P["setscrew_r"], P["hub_r"] * 2.2)
    pulley = pulley - screw
    return [lab(pulley, "metal", 1)]
