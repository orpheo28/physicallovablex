"""Smart ring (revolved comfort-fit band).

A wearable ring: a RectangleRounded cross-section positioned on Plane.XZ at the band radius and revolved about Axis.Z (comfort-fit band), a Torus inlay groove cut and filled as an accent, and a sensor bump on the inside. Revolve a placed 2-D section for any ring, bangle, gasket or O-ring.
tags: ring, smart ring, wearable, jewelry, band, bangle, revolve, torus, cross-section, comfort fit, sensor, inlay
"""
import math

from build123d import *

P = {"inner_r": 9.0, "thickness": 2.6, "width": 8.0, "corner": 1.1, "inlay_r": 0.6, "sensor_r": 1.6}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    ri, t, w = P["inner_r"], P["thickness"], P["width"]
    rm = ri + t / 2
    # Plane.XZ * Pos(radius, height) places the section at the band's mid-radius, centred on z = w/2
    section = Plane.XZ * Pos(rm, w / 2) * RectangleRounded(t, w, P["corner"])
    band = revolve(section, Axis.Z)

    # decorative inlay: a thin torus sunk into the outer face at mid-height
    inlay = Pos(0, 0, w / 2) * Torus(ri + t, P["inlay_r"])
    band = band - inlay
    sensor = Pos(ri, 0, w / 2) * Rot(0, 90, 0) * Cylinder(P["sensor_r"], 1.2)
    return [lab(band, "metal", 1), lab(inlay, "accent", 1), lab(sensor, "led", 1)]
