"""Desk hub with a row of ports.

Low wedge-profile USB/desk hub: side profile drawn as a `Polyline` in XZ and extruded to depth, a row of ports cut
along the vertical front lip with a `Locations` list, rubber strip underneath and a status light bar. Shows extruding a
side profile, placing cutters on a side face via an explicit `Plane(origin, x_dir, z_dir)`.
tags: hub, usb hub, dock, desk, ports, row, wedge, profile, extrude, plane, locations, cutout, rubber, led
"""
import math

from build123d import *

P = {"length": 130.0, "depth": 60.0, "h_back": 22.0, "h_front": 12.0, "ports": 5, "port_pitch": 20.0,
     "port_w": 12.5, "port_h": 4.8, "foot_t": 1.5}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, D, hb, hf, ft = P["length"], P["depth"], P["h_back"], P["h_front"], P["foot_t"]
    # Side profile in the YZ plane (front at -Y); extrude along X.
    prof = Polyline((-D / 2, ft), (D / 2, ft), (D / 2, hb), (-D / 2 + 8, hb), (-D / 2, hf), close=True)
    body = extrude(Plane.YZ * make_face(prof), amount=L / 2, both=True)
    try:
        body = fillet(body.edges().filter_by(Axis.X), radius=2.0)
    except Exception:
        pass
    # Front face plane: origin on the front face, z_dir pointing out of it (-Y), x_dir along the length.
    face_c = Vector(0, -D / 2, (ft + hf) / 2)
    front = Plane(origin=face_c, x_dir=(1, 0, 0), z_dir=(0, -1, 0))
    n = P["ports"]
    cutters = [front * Pos((i - (n - 1) / 2) * P["port_pitch"], 0) * Rectangle(P["port_w"], P["port_h"]) for i in range(n)]
    for c in cutters:
        body = body - extrude(c, amount=12, both=True)
    light = Pos(0, -D / 2 + 4.5, (hb + hf) / 2 + 0.2) * Rot(-math.degrees(math.atan2(hb - hf, 8)), 0, 0) * Box(L * 0.4, 1.5, 1.0)
    foot = Pos(0, 0, ft / 2) * Box(L - 10, D - 10, ft)
    return [lab(body, "body", 1), lab(foot, "rubber", 1), lab(light, "led", 1)]
