"""Hair Dryer (compact) — seed program of our parametric family.

Hair dryer: barrel with heater/fan duct, concentrator nozzle, intake filter cap, angled handle, switches. Full product: parameters dict P, geometry helpers, labelled parts.
tags: hair dryer, barrel, nozzle, handle, fan, duct, appliance, pistol grip, compact
"""
import math

from build123d import *

P = {
    'barrel_length': 150.0,
    'barrel_diameter': 62.0,
    'nozzle_length': 45.0,
    'nozzle_outlet': 38.0,
    'filter_diameter': 64.0,
    'handle_length': 120.0,
    'handle_width': 34.0,
    'handle_depth': 28.0,
    'handle_angle_deg': 12.0,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def xcyl(x0, length, r, z):
    """Cylinder along +X starting at x0, axis at height z."""
    return Pos(x0 + length / 2, 0, z) * (Rot(0, 90, 0) * Cylinder(r, length))


def build_parts(P):
    parts = []
    hl, hw, hd = P["handle_length"], P["handle_width"], P["handle_depth"]
    br, bl = P["barrel_diameter"] / 2, P["barrel_length"]
    z = hl + br * 0.7  # barrel axis height
    x_back = -bl * 0.42
    barrel = xcyl(x_back, bl, br, z)
    try:
        barrel = fillet(barrel.edges(), radius=br * 0.25)
    except Exception:
        pass
    parts.append(lab(barrel, "body", 1))
    # concentrator nozzle (cone) at the front
    nl, no = P["nozzle_length"], P["nozzle_outlet"] / 2
    nozzle = Pos(x_back + bl + nl / 2, 0, z) * (Rot(0, 90, 0) * Cone(br * 0.82, no, nl))
    parts.append(lab(nozzle, "accent", 1))
    parts.append(lab(Pos(x_back + bl + nl, 0, z) * (Rot(0, 90, 0) * Cylinder(no * 0.8, 1.2)), "coat", 1))
    # intake filter cap at the back (mesh = coat), a rim ring
    fr = P["filter_diameter"] / 2
    parts.append(lab(xcyl(x_back - 14, 16, fr, z), "coat", 2))
    parts.append(lab(xcyl(x_back - 3, 4, fr + 2, z), "accent", 2))
    # handle: raked box with rounded edges, from the barrel down to the floor
    a = P["handle_angle_deg"]
    handle = Pos(-hl * math.sin(math.radians(a)) * 0.5, 0, 0) * Rot(0, -a, 0) * Box(
        hd, hw, hl + br * 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        handle = fillet(handle.edges().filter_by(Axis.Z), radius=min(hw, hd) * 0.42)
    except Exception:
        pass
    parts.append(lab(handle, "body", 2))
    # speed / heat slide switch and cold-shot button on the front face of the handle
    fx = hd / 2 - hl * math.sin(math.radians(a)) * 0.3
    parts.append(lab(Pos(fx + 1, 0, hl * 0.62) * Box(5, hw * 0.45, 26), "button", 1))
    parts.append(lab(Pos(fx + 1, 0, hl * 0.85) * Box(6, hw * 0.4, 12), "button", 2))
    parts.append(lab(Pos(fx - 2, 0, hl * 0.4) * Box(3, hw * 0.3, 5), "led", 1))
    # cord strain relief under the handle
    parts.append(lab(Pos(-hl * math.sin(math.radians(a)) * 0.5, 0, 6) * Cylinder(7, 12), "rubber", 1))
    return parts


def build():
    return build_parts(P)
