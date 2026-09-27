"""Flush-mounted rooftop solar system for a 35 m² roof in Biarritz. Units: mm."""
import math
from build123d import *

P = {
    "rows": 2,
    "cols": 7,
    "module_length": 1722.0,
    "module_width": 1134.0,
    "module_thickness": 30.0,
    "module_gap": 20.0,
    "frame_width": 35.0,
    "roof_pitch_deg": 28.0,
    "roof_margin_x": 100.0,
    "roof_margin_slope": 20.0,
    "roof_thickness": 20.0,
    "roof_eave_height": 20.0,
    "rail_height": 48.0,
    "rail_width": 38.0,
    "rail_end_extension": 55.0,
    "mounting_foot_width": 72.0,
    "mounting_foot_length": 115.0,
    "mounting_foot_height": 18.0,
    "inverter_width": 460.0,
    "inverter_depth": 130.0,
    "inverter_height": 310.0,
}


def lab(shape, role, number):
    shape.label = f"{role}.{number}"
    return shape


def pv_module(length, width, thickness):
    """Black perimeter frame and a continuous monocrystalline cell surface."""
    frame_width = P["frame_width"]
    frame = Box(width, length, thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))
    opening = Pos(0, 0, 4) * Box(
        width - 2 * frame_width,
        length - 2 * frame_width,
        thickness,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    frame = frame - opening
    cells = Pos(0, 0, thickness - 5) * Box(
        width - 2 * frame_width + 1,
        length - 2 * frame_width + 1,
        4,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return frame, cells


def build():
    rows, cols = P["rows"], P["cols"]
    ml, mw = P["module_length"], P["module_width"]
    gap = P["module_gap"]
    array_width = cols * mw + (cols - 1) * gap
    array_slope_length = rows * ml + (rows - 1) * gap
    roof_width = array_width + 2 * P["roof_margin_x"]
    roof_slope_length = array_slope_length + 2 * P["roof_margin_slope"]

    pitch = math.radians(P["roof_pitch_deg"])
    slope_rise = roof_slope_length * math.sin(pitch)
    roof_center_z = P["roof_eave_height"] + slope_rise / 2
    roof_plane = Plane(
        origin=(0, 0, roof_center_z),
        x_dir=(1, 0, 0),
        z_dir=(0, -math.sin(pitch), math.cos(pitch)),
    )

    parts = []

    # A thin, single-pitch roof substrate keeps the modules nearly flush to
    # the roofline rather than presenting them as a free-standing tilted rack.
    substrate = Pos(0, 0, -P["roof_thickness"]) * Box(
        roof_width,
        roof_slope_length,
        P["roof_thickness"],
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    parts.append(lab(roof_plane * substrate, "roof", 1))

    rail_number = 0
    foot_number = 0
    for row in range(rows):
        row_y = -array_slope_length / 2 + ml / 2 + row * (ml + gap)

        for rail_offset in (-ml * 0.30, ml * 0.30):
            rail_y = row_y + rail_offset
            rail = Pos(0, rail_y, 0) * Box(
                array_width + 2 * P["rail_end_extension"],
                P["rail_width"],
                P["rail_height"],
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            rail_number += 1
            parts.append(lab(roof_plane * rail, "metal", rail_number))

            # Anodised-aluminium mounting feet at the ends of each rail.
            for side in (-1, 1):
                foot_x = side * (array_width / 2 - 75)
                foot = Pos(foot_x, rail_y, 0) * Box(
                    P["mounting_foot_width"],
                    P["mounting_foot_length"],
                    P["mounting_foot_height"],
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                )
                foot_number += 1
                parts.append(lab(roof_plane * foot, "steel", foot_number))

        for col in range(cols):
            x = -array_width / 2 + mw / 2 + col * (mw + gap)
            module_y = row_y
            frame, cells = pv_module(ml, mw, P["module_thickness"])
            mount = Pos(x, module_y, P["rail_height"])
            number = row * cols + col + 1
            parts.append(lab(roof_plane * (mount * frame), "coat", number))
            parts.append(lab(roof_plane * (mount * cells), "cell", number))

    # Compact household grid-tie inverter beneath the downhill roof edge.
    inverter_y = -roof_slope_length / 2 - P["inverter_depth"] / 2 - 25
    inverter_z = 185
    inverter = Pos(0, inverter_y, inverter_z) * Box(
        P["inverter_width"],
        P["inverter_depth"],
        P["inverter_height"],
    )
    parts.append(lab(inverter, "coat", 100))
    display = Pos(0, inverter_y - P["inverter_depth"] / 2 - 2, inverter_z + 65) * Box(
        180, 5, 72
    )
    parts.append(lab(display, "glass", 1))
    indicator = Pos(145, inverter_y - P["inverter_depth"] / 2 - 4, inverter_z - 60) * Box(
        14, 7, 14
    )
    parts.append(lab(indicator, "led", 1))

    return parts
