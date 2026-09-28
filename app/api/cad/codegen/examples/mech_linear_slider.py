"""Linear slider carriage on a rail.

A profiled rail (extruded 2D cross-section) with a row of mounting holes from Locations, a carriage block whose channel is cut with an offset copy of the rail profile, end stops and top mounting holes on a GridLocations pattern. Use for linear guides, 3D-printer axes, drawer slides.
tags: linear, slider, rail, carriage, guide, extrude, profile, pattern, grid, holes, mechanism, cnc
"""
import math

from build123d import *

P = {"rail_len": 300.0, "rail_w": 20.0, "rail_h": 15.0, "neck_w": 10.0, "car_len": 60.0,
     "car_w": 44.0, "car_h": 26.0, "car_x": 40.0, "hole_pitch": 60.0, "clear": 0.5}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rail_profile(w, h, neck, grow=0.0):
    # T-ish profile in the YZ plane: a narrow neck under a wider head
    neck_part = Pos(0, h * 0.35) * Rectangle(neck + 2 * grow, h * 0.7 + 2 * grow)
    head = Pos(0, h * 0.8) * Rectangle(w + 2 * grow, h * 0.4 + 2 * grow)
    return Plane.YZ * (Pos(0, h * 0.1) * Rectangle(w, h * 0.2) + neck_part + head)


def build():
    L, w, h = P["rail_len"], P["rail_w"], P["rail_h"]
    rail = extrude(rail_profile(w, h, P["neck_w"]), amount=L / 2, both=True)
    n_holes = int(L // P["hole_pitch"])
    xs = [(-(n_holes - 1) / 2 + i) * P["hole_pitch"] for i in range(n_holes)]
    rail -= [Pos(x, 0, h) * Cylinder(2.7, 2 * h) for x in xs]
    rail -= [Pos(x, 0, h) * Cylinder(4.5, 6) for x in xs]  # counterbores from the top
    cl, cw, ch, x0 = P["car_len"], P["car_w"], P["car_h"], P["car_x"]
    car = Pos(x0, 0, h * 0.35 + ch / 2) * Box(cl, cw, ch)
    car -= Pos(x0, 0, 0) * extrude(rail_profile(w, h, P["neck_w"], P["clear"]), amount=cl, both=True)
    car -= Pos(x0, 0, h * 0.35 + ch) * (GridLocations(cl * 0.6, cw * 0.6, 2, 2) * Cylinder(2.5, 16))
    try:
        car = fillet(car.edges().group_by(Axis.Z)[-1], radius=2)
    except Exception:
        pass
    stops = [Pos(sx * (L / 2 - 4), 0, h * 0.6) * Box(8, w + 6, h * 1.2) for sx in (-1, 1)]
    wipers = [Pos(x0 + sx * (cl / 2 + 1.5), 0, h * 0.35 + ch / 2) * Box(3, cw - 4, ch - 4) for sx in (-1, 1)]
    return [lab(rail, "steel", 1), lab(car, "metal", 1), lab(stops[0], "rubber", 1), lab(stops[1], "rubber", 2),
            lab(wipers[0], "accent", 1), lab(wipers[1], "accent", 2)]
