"""Pebble-shaped speaker.

A smooth portable speaker: a Sphere squashed with scale(by=(x, y, z)) into a pebble, split flat at the bottom so it rests on z=0, then split again horizontally into a fabric grille top and a body bottom. Buttons and an LED sit on the crown. scale() is the easiest way to get organic ellipsoids.
tags: speaker, bluetooth speaker, pebble, organic, ellipsoid, sphere, scale, split, grille, fabric, button, led
"""
import math

from build123d import *

P = {"length": 150.0, "width": 120.0, "height": 70.0, "flat": 8.0, "seam": 0.45, "button_r": 7.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H = P["length"], P["width"], P["height"]
    flat = P["flat"]
    # ellipsoid with total height H + flat, then cut the bottom `flat` mm off and drop it to z=0
    ez = H + flat
    pebble = scale(Sphere(1.0), by=(L / 2, W / 2, ez / 2))
    pebble = split(pebble, bisect_by=Plane.XY.offset(-ez / 2 + flat), keep=Keep.TOP)
    pebble = Pos(0, 0, ez / 2 - flat) * pebble

    seam = Plane.XY.offset(H * P["seam"])
    grille = split(pebble, bisect_by=seam, keep=Keep.TOP)
    body = split(pebble, bisect_by=seam, keep=Keep.BOTTOM)

    btns = [Pos(x, 0, H - 1.5) * Cylinder(P["button_r"], 3) for x in (-18, 0, 18)]
    led = Pos(0, W * 0.3, H * 0.93) * Sphere(2.0)
    parts = [lab(grille, "fabric", 1), lab(body, "body", 1), lab(led, "led", 1)]
    return parts + [lab(b, "button", i + 1) for i, b in enumerate(btns)]
