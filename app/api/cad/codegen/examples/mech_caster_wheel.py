"""Swivel caster wheel with fork.

A top mounting plate with four holes, a swivel bearing disc, a fork made as one side plate plus its mirror, an axle and a wheel (metal hub + rubber tyre from a revolved profile). Shows mirror(about=Plane.YZ) for symmetric fork legs and Rot(0,90,0) to lay a revolved wheel on the X axis.
tags: caster, wheel, fork, swivel, axle, tyre, rubber, mirror, revolve, furniture, trolley, hub
"""
import math

from build123d import *

P = {"wheel_r": 40.0, "wheel_w": 28.0, "hub_r": 16.0, "plate": 70.0, "plate_t": 4.0,
     "fork_gap": 34.0, "fork_t": 4.0, "offset": 22.0, "axle_r": 4.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    R, ww, g, ft = P["wheel_r"], P["wheel_w"], P["fork_gap"], P["fork_t"]
    az = R  # axle height: the tyre touches z=0
    top = az + R + 16  # underside of the swivel bearing
    ay = -P["offset"]  # trailing offset of the axle behind the swivel axis
    # wheel: revolve an (radius, width) profile drawn on XZ around Z, then lay the axis along X
    tyre_prof = Plane.XZ * Pos((P["hub_r"] + R) / 2 + 3, 0) * Rectangle(R - P["hub_r"] - 6, ww)
    tyre = revolve(tyre_prof, axis=Axis.Z)
    try:
        tyre = fillet(tyre.edges().filter_by(GeomType.CIRCLE).group_by(SortBy.RADIUS)[-1], radius=8)
    except Exception:
        pass
    hub = Cylinder(P["hub_r"] + 3, ww * 0.9) - Cylinder(P["axle_r"] + 0.2, ww + 2)
    place = Pos(0, ay, az) * Rot(0, 90, 0)
    tyre, hub = place * tyre, place * hub
    axle = Pos(0, ay, az) * Rot(0, 90, 0) * Cylinder(P["axle_r"], g + 2 * ft + 6)
    # one fork leg from the axle up to the crown, then its mirror copy
    leg = Pos(g / 2 + ft / 2, ay / 2, (az + top) / 2) * Box(ft, abs(ay) + 22, top - az + 12)
    leg -= Pos(0, ay, az) * Rot(0, 90, 0) * Cylinder(P["axle_r"] + 0.2, g + 20)
    crown = Pos(0, 0, top - ft / 2) * Box(g + 2 * ft, 44, ft)
    fork = leg + mirror(leg, about=Plane.YZ) + crown
    bearing = Pos(0, 0, top + 4) * Cylinder(24, 8)
    pt = P["plate_t"]
    plate = Pos(0, 0, top + 8 + pt / 2) * Box(P["plate"], P["plate"], pt)
    plate -= Pos(0, 0, top + 8 + pt / 2) * (GridLocations(P["plate"] - 14, P["plate"] - 14, 2, 2) * Cylinder(3.5, pt + 2))
    return [lab(tyre, "rubber", 1), lab(hub, "body", 1), lab(axle, "steel", 1), lab(fork, "metal", 1),
            lab(bearing, "steel", 2), lab(plate, "metal", 2)]
