"""Screenless kitesurf recovery band with a soft loop strap and optical sensor."""
import math
from build123d import *

P = {
    "pod_length": 44.0,
    "pod_width": 30.0,
    "pod_thickness": 8.0,
    "pod_bottom": 31.5,
    "shell_split": 4.2,
    "corner_radius": 8.0,
    "strap_width": 25.0,
    "loop_outer_x": 40.0,
    "loop_outer_z": 16.0,
    "strap_thickness": 2.4,
    "loop_center_z": 16.0,
    "strap_opening_half_length": 19.0,
    "sensor_radius": 7.3,
}


def lab(shape, role, number):
    shape.label = f"{role}.{number}"
    return shape


def build():
    parts = []
    bottom = P["pod_bottom"]
    split = bottom + P["shell_split"]
    top = bottom + P["pod_thickness"]

    # A continuous soft loop passes beneath the wrist. Its short opening at
    # the top leaves the sensor window exposed against the skin.
    loop_plane = Plane(
        origin=(0, P["strap_width"] / 2, P["loop_center_z"]),
        x_dir=(1, 0, 0),
        z_dir=(0, -1, 0),
    )
    outer = Ellipse(P["loop_outer_x"], P["loop_outer_z"])
    inner = Ellipse(
        P["loop_outer_x"] - P["strap_thickness"],
        P["loop_outer_z"] - P["strap_thickness"],
    )
    strap = extrude(loop_plane * (outer - inner), amount=P["strap_width"])
    opening = Pos(0, 0, 25) * Box(
        2 * P["strap_opening_half_length"],
        P["strap_width"] + 2,
        20,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    parts.append(lab(strap - opening, "fabric", 1))

    # Two gently drafted PC/ABS shells form the soft-block pod.
    lower = loft([
        Plane(origin=(0, 0, bottom)) *
        RectangleRounded(43.0, 29.0, P["corner_radius"]),
        Plane(origin=(0, 0, split)) *
        RectangleRounded(44.0, 30.0, P["corner_radius"]),
    ])
    upper = loft([
        Plane(origin=(0, 0, split)) *
        RectangleRounded(44.0, 30.0, P["corner_radius"]),
        Plane(origin=(0, 0, top)) *
        RectangleRounded(42.2, 28.2, P["corner_radius"] - 0.5),
    ])
    try:
        upper = fillet(upper.edges().group_by(Axis.Z)[-1], radius=1.2)
    except Exception:
        pass
    parts.append(lab(lower, "body", 1))
    parts.append(lab(upper, "body", 2))

    # Recessed-looking dark optical window and its two emitter apertures.
    sensor = Pos(0, 0, bottom - 0.65) * Cylinder(
        P["sensor_radius"], 0.75,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    parts.append(lab(sensor, "glass", 1))
    for number, x in enumerate((-2.8, 2.8), 1):
        emitter = Pos(x, 0, bottom - 0.78) * Cylinder(
            1.25, 0.18, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        parts.append(lab(emitter, "led", number))

    # A small, unobtrusive sync/status light: no screen or display.
    status = Pos(15.5, 0, top - 0.03) * Cylinder(
        0.85, 0.12, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    parts.append(lab(status, "diffuser", 1))
    return parts
