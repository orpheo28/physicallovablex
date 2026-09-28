"""Solar Array (roof) — seed program of our parametric family.

Rooftop solar array: N PV modules (frame + cells) on rails over a pitched roof, tilt and azimuth. Full product: parameters dict P, geometry helpers, labelled parts.
tags: solar, panel, pv, roof, array, rails, frame, cells, roof
"""
import math

from build123d import *

P = {
    'rows': 2.0,
    'cols': 5.0,
    'module_length': 1722.0,
    'module_width': 1134.0,
    'module_thickness': 30.0,
    'gap': 20.0,
    'roof_pitch_deg': 30.0,
    'module_tilt_deg': 0.0,
    'azimuth_deg': 180.0,
    'standoff': 110.0,
    'margin': 450.0,
    'wall_height': 2800.0,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def pv_module(ml, mw, mt):
    """Portrait module in its own frame: X = width, Y = length, underside on z=0."""
    fw = 35.0
    frame = Box(mw, ml, mt, align=(Align.CENTER, Align.CENTER, Align.MIN))
    frame = frame - Pos(0, 0, 4) * Box(mw - 2 * fw, ml - 2 * fw, mt, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cells = Pos(0, 0, mt - 5) * Box(mw - 2 * fw + 1, ml - 2 * fw + 1, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return frame, cells


def build_parts(P):
    rows, cols = int(P["rows"]), int(P["cols"])
    ml, mw, mt, g = P["module_length"], P["module_width"], P["module_thickness"], P["gap"]
    pitch = math.radians(P["roof_pitch_deg"])
    tilt = P["module_tilt_deg"]
    arr_w = cols * mw + (cols - 1) * g
    arr_l = rows * ml + (rows - 1) * g
    slope_len = arr_l * math.cos(math.radians(tilt)) + 2 * P["margin"]
    house_l = arr_w + 2 * P["margin"]
    run = slope_len * math.cos(pitch)          # horizontal depth of one roof side
    rise = slope_len * math.sin(pitch)
    wh = P["wall_height"]
    over = 250.0                               # eave overhang
    rot = Rot(0, 0, 180 - P["azimuth_deg"])
    parts = []

    walls = Box(house_l - 2 * over, 2 * run - 2 * over, wh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(rot * walls, "wall", 1))
    tri = make_face(Polyline((0, -run, 0), (0, run, 0), (0, 0, rise), close=True))
    roof = Pos(-house_l / 2, 0, wh) * extrude(tri, amount=house_l, dir=(1, 0, 0))
    parts.append(lab(rot * roof, "roof", 1))

    # roof-surface frame: origin mid front slope, local X along the eave, local Y up the slope, local Z = normal
    origin = (0, -run / 2, wh + rise / 2)
    plane = Plane(origin=origin, x_dir=(1, 0, 0), z_dir=(0, -math.sin(pitch), math.cos(pitch)))
    n = 0
    for r in range(rows):
        y0 = -arr_l / 2 + ml / 2 + r * (ml + g)
        yl = y0 * math.cos(math.radians(tilt))
        for off in (-ml * 0.3, ml * 0.3):  # two mounting rails under each row, along the eave
            rail = Pos(0, yl + off * math.cos(math.radians(tilt)), 0) * Box(arr_w + 200, 40, P["standoff"],
                                                                            align=(Align.CENTER, Align.CENTER, Align.MIN))
            n += 1
            parts.append(lab(rot * (plane * rail), "metal", n))
        for c in range(cols):
            x = -arr_w / 2 + mw / 2 + c * (mw + g)
            frame, cells = pv_module(ml, mw, mt)
            loc = Pos(x, yl, P["standoff"] + (ml / 2) * math.sin(math.radians(tilt))) * Rot(tilt, 0, 0)
            k = r * cols + c + 1
            parts.append(lab(rot * (plane * (loc * frame)), "metal", 100 + k))
            parts.append(lab(rot * (plane * (loc * cells)), "cell", k))
    return parts


def build():
    return build_parts(P)
