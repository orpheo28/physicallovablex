"""Ball-and-socket joint.

A flanged socket cup (Cylinder minus Sphere, opened at the top) holding a ball whose stem is tilted about the ball centre with shape.rotate(Axis(centre, dir), angle). Use for camera mounts, articulated arms, gear-lever or joystick style joints. Note: the variable is cup_body because "socket" is a reserved name in the sandbox.
tags: ball joint, socket, sphere, pivot, articulated, stem, tilt, rotate, flange, mount, joint, boolean
"""
import math

from build123d import *

P = {"ball_r": 12.0, "cup_r": 17.0, "cup_h": 20.0, "flange_r": 30.0, "flange_h": 5.0,
     "stem_r": 5.0, "stem_len": 55.0, "tilt": 25.0, "bolt_r": 2.2}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    br, fh = P["ball_r"], P["flange_h"]
    cz = fh + P["cup_h"] - br * 0.55  # ball centre: the cup rim sits above the equator to trap it
    flange = Pos(0, 0, fh / 2) * Cylinder(P["flange_r"], fh)
    cup = Pos(0, 0, fh + P["cup_h"] / 2) * Cylinder(P["cup_r"], P["cup_h"])
    cup_body = flange + cup - Pos(0, 0, cz) * Sphere(br + 0.3)
    cup_body -= Pos(0, 0, fh + P["cup_h"]) * Cylinder(br * 0.8, 6)  # throat for the stem to swing
    cup_body -= PolarLocations(P["flange_r"] - 7, 4, start_angle=45) * (Pos(0, 0, fh / 2) * Cylinder(P["bolt_r"], fh + 2))
    ball = Pos(0, 0, cz) * Sphere(br)
    stem = Pos(0, 0, cz) * Cylinder(P["stem_r"], P["stem_len"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    knob = Pos(0, 0, cz + P["stem_len"]) * Sphere(P["stem_r"] * 1.8)
    pivot = Axis((0, 0, cz), (1, 0, 0))
    stem = (stem + knob).rotate(pivot, P["tilt"])
    ball = ball.rotate(pivot, P["tilt"])
    return [lab(cup_body, "body", 1), lab(ball, "steel", 1), lab(stem, "metal", 1)]
