"""Quiet compact travel hair dryer. Units: mm; Z is up."""
import math
from build123d import *

P = {
    "barrel_length": 142.0,
    "barrel_diameter": 62.0,
    "barrel_axis_height": 143.0,
    "barrel_back_x": -70.0,
    "nozzle_length": 40.0,
    "nozzle_inlet_radius": 26.0,
    "nozzle_outlet_width": 48.0,
    "nozzle_outlet_height": 22.0,
    "filter_diameter": 64.0,
    "filter_depth": 18.0,
    "handle_length": 126.0,
    "handle_width": 34.0,
    "handle_depth": 29.0,
    "handle_angle_deg": 12.0,
    "handle_base_x": -7.0,
}

def lab(shape, role, number):
    shape.label = f"{role}.{number}"
    return shape

def xcyl(x0, length, radius, z):
    return Pos(x0 + length / 2, 0, z) * Rot(0, 90, 0) * Cylinder(radius, length)

def cross_plane(x, z):
    return Plane(origin=(x, 0, z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))

def build_parts(P):
    parts = []
    z = P["barrel_axis_height"]
    back = P["barrel_back_x"]
    front = back + P["barrel_length"]
    radius = P["barrel_diameter"] / 2

    # Soft-touch PC barrel, with a visible recessed air outlet.
    barrel = xcyl(back, P["barrel_length"], radius, z)
    try:
        barrel = fillet(barrel.edges(), radius=5)
    except Exception:
        pass
    barrel = barrel - xcyl(front - 8, 10, 21, z)
    parts.append(lab(barrel, "body", 1))

    # Short travel concentrator transitions into a flattened oval mouth.
    tip = front + P["nozzle_length"]
    outer = loft([
        cross_plane(front, z) * Circle(P["nozzle_inlet_radius"]),
        cross_plane(tip, z) * Ellipse(
            P["nozzle_outlet_width"] / 2,
            P["nozzle_outlet_height"] / 2,
        ),
    ])
    inner = loft([
        cross_plane(front - 1, z) * Circle(20),
        cross_plane(tip + 1, z) * Ellipse(
            P["nozzle_outlet_width"] / 2 - 3,
            P["nozzle_outlet_height"] / 2 - 3,
        ),
    ])
    parts.append(lab(outer - inner, "accent", 1))

    # Removable rear intake: dark recessed screen and a contrasting retaining rim.
    filter_back = back - P["filter_depth"]
    screen = xcyl(filter_back, 3, P["filter_diameter"] / 2 - 3, z)
    parts.append(lab(screen, "coat", 1))
    rim = xcyl(filter_back + 2, P["filter_depth"] - 2,
                P["filter_diameter"] / 2, z)
    rim = rim - xcyl(filter_back + 1, P["filter_depth"] + 1, 27, z)
    parts.append(lab(rim, "accent", 2))

    grille = None
    for offset in (-20, -12, -4, 4, 12, 20):
        half_width = math.sqrt(max(0, 26 * 26 - offset * offset))
        slat = Pos(filter_back - 0.8, 0, z + offset) * Box(
            2, half_width * 2, 2.2
        )
        grille = slat if grille is None else grille + slat
    parts.append(lab(grille, "coat", 2))

    # Short raked handle; its rounded section blends visually into the barrel.
    angle = P["handle_angle_deg"]
    handle = Box(
        P["handle_depth"], P["handle_width"], P["handle_length"],
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    try:
        handle = fillet(handle.edges().filter_by(Axis.Z), radius=11)
    except Exception:
        pass
    handle = Pos(P["handle_base_x"], 0, 4) * Rot(0, -angle, 0) * handle
    parts.append(lab(handle, "body", 2))

    # Soft grip at the base and a low-profile cord strain relief.
    grip = Box(30, 35, 34, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        grip = fillet(grip.edges().filter_by(Axis.Z), radius=11)
    except Exception:
        pass
    grip = Pos(P["handle_base_x"], 0, 5) * Rot(0, -angle, 0) * grip
    parts.append(lab(grip, "rubber", 1))
    parts.append(lab(Pos(P["handle_base_x"], 0, 0) *
                     Cylinder(7, 9, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                     "rubber", 2))

    # Separate tactile controls for airflow, heat, and cold shot.
    parts.append(lab(Pos(-3, 0, 76) * Box(5, 17, 26), "button", 1))
    parts.append(lab(Pos(-8, 0, 104) * Box(5, 17, 17), "button", 2))
    parts.append(lab(Pos(-1, 0, 56) * Box(5, 12, 8), "button", 3))
    parts.append(lab(Pos(-1.5, 11, 55) * Sphere(1.8), "led", 1))
    return parts

def build():
    return build_parts(P)
