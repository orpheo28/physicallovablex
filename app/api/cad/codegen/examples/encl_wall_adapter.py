"""Wall plug power adapter.

Wall-wart charger: rounded cube body, a softened front face with a USB-A and USB-C port, and two flat blade prongs
on the back with through holes. Shows a Z-up layout of a device whose "back" is -Y: prongs placed with `Pos` and
oriented boxes, ports cut on the +Y face with `Plane.XZ`, `fillet` on all edges in try/except.
tags: charger, power adapter, wall plug, wall wart, prongs, usb, port, cube, fillet, plane, cutout, electronics
"""
import math

from build123d import *

P = {"size_x": 48.0, "size_y": 36.0, "size_z": 52.0, "corner": 5.0, "prong_l": 16.0, "prong_w": 6.3,
     "prong_t": 1.5, "prong_pitch": 12.7}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    X, Y, Z = P["size_x"], P["size_y"], P["size_z"]
    body = Pos(0, 0, Z / 2) * Box(X, Y, Z)
    try:
        body = fillet(body.edges(), radius=P["corner"])
    except Exception:
        pass
    front = Plane.XZ.offset(-Y / 2)  # normal -Y, offset(-Y/2) -> y = +Y/2: the front face
    usba = extrude(front * Pos(0, Z * 0.62) * Rectangle(12.5, 4.8), amount=10, both=True)
    usbc = extrude(front * Pos(0, Z * 0.38) * SlotOverall(8.4, 2.6), amount=10, both=True)
    body = body - usba - usbc
    led = Pos(0, Y / 2 - 0.3, Z * 0.85) * Cylinder(1.2, 1.0, rotation=(90, 0, 0))
    prongs = []
    for i, x in enumerate((-P["prong_pitch"] / 2, P["prong_pitch"] / 2)):
        # Blade sticks out of the back (-Y) face, its flat side vertical.
        blade = Pos(x, -Y / 2 - P["prong_l"] / 2 + 1, Z / 2) * Box(P["prong_t"], P["prong_l"], P["prong_w"])
        blade = blade - Pos(x, -Y / 2 - P["prong_l"] + 4, Z / 2) * Cylinder(1.5, 5, rotation=(0, 90, 0))
        prongs.append(lab(blade, "metal", i + 1))
    return [lab(body, "body", 1), lab(led, "led", 1)] + prongs
