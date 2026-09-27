"""Solar array family (W19): rooftop PV array — rows × cols modules on a pitched roof, with tilt and azimuth.

House = wall block + gable roof (ridge along X). Modules (aluminium frame + glass/cell laminate, portrait) sit on
mounting rails on the front roof slope, optionally tilted on racks relative to the roof; the whole house is turned
by the azimuth (180° = array faces -Y, "south"). Origin: house footprint centre on the ground, +Z up.
Module default = 1722 × 1134 × 30 mm (common 400 W half-cut format).
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp

NAME = "solar_array"
CATEGORY = "solar_roof"
DESCRIPTION = "Rooftop solar array: N PV modules (frame + cells) on rails over a pitched roof, tilt and azimuth."


@dataclass
class Params:
    rows: float = 2.0
    cols: float = 5.0
    module_length: float = 1722.0    # along the slope (portrait)
    module_width: float = 1134.0
    module_thickness: float = 30.0
    gap: float = 20.0
    roof_pitch_deg: float = 30.0
    module_tilt_deg: float = 0.0     # extra tilt on racks relative to the roof (0 = flush mount)
    azimuth_deg: float = 180.0       # compass direction the array faces
    standoff: float = 110.0          # roof surface to module underside
    margin: float = 450.0            # roof edge margin around the array
    wall_height: float = 2800.0

    def clamped(self) -> "Params":
        return Params(
            rows=float(int(clamp(round(self.rows), 1, 4))), cols=float(int(clamp(round(self.cols), 1, 10))),
            module_length=clamp(self.module_length, 1000, 2400), module_width=clamp(self.module_width, 600, 1400),
            module_thickness=clamp(self.module_thickness, 25, 45), gap=clamp(self.gap, 10, 60),
            roof_pitch_deg=clamp(self.roof_pitch_deg, 5, 50), module_tilt_deg=clamp(self.module_tilt_deg, 0, 30),
            azimuth_deg=float(self.azimuth_deg) % 360.0, standoff=clamp(self.standoff, 60, 250),
            margin=clamp(self.margin, 200, 1200), wall_height=clamp(self.wall_height, 2000, 6000),
        )


PRESETS = {"roof": Params()}


def default_params(variant: str = "roof") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["roof"]).clamped())


# === GEOMETRY ===
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
# === END GEOMETRY ===


def build(params: Params | dict | None = None):
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    parts = build_parts(asdict(p.clamped()))
    return Compound(children=parts), parts
