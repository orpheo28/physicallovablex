"""Pro detail for W2's two-shell enclosures (C1, CAD_DETAIL_LEVEL=pro): desk lamp / generic boxes (families 0-1),
tracker card (family 2 slab), wearable pod (family 3). In-process only (reads W2 / W17 geometry helpers); the files
that build these products (api/cad/build.py, look.py, wearables.py) are not C1's — C5 wires the calls:

    enclosure_details(params, joint=None) -> [placed standard parts / DFM features]   # add to the viewer parts
    pro_viewer_parts(params, features=()) -> labelled parts (shells + look details + pro details)
    joint_for(params) -> "screws" | "weld" | "none"

Joints: screws = W2 floor bosses in the bottom shell + matching insert bosses in the top shell, M2 / M2.5 / M3 by
footprint, screws driven up through the floor (lamp base, boxes, wearable pod: 2 × M2); weld = 90° energy director
on the bottom-shell rim for an ultrasonically welded, screwless card (tracker); ring: none (one-piece band).
"""

from __future__ import annotations

import math
from typing import Any

from api.cad.stdparts import dfm, joints


def joint_for(params: dict[str, Any]) -> str:
    from api.cad.build import normalize

    p = normalize(params)
    fam = int(p["family"])
    if fam == 4:
        return "none"
    if fam == 2 and min(p["length"], p["width"]) <= 90 and p["height"] <= 14:
        return "weld"
    return "screws"


def _size_for(short: float) -> str:
    return "M2" if short < 50 else ("M2.5" if short < 120 else "M3")


def enclosure_details(params: dict[str, Any], joint: str | None = None) -> list:
    from api.cad.build import _boss_points, normalize

    p = normalize(params)
    fam = int(p["family"])
    joint = joint or joint_for(p)
    L, W, H, wall, d = p["length"], p["width"], p["height"], p["wall"], p["draft_deg"]
    out: list = []
    if joint == "none":
        return out
    z_base = 0.0
    if fam == 3:
        from api.cad.wearables import WINDOW_H

        z_base, H = WINDOW_H, H - WINDOW_H
    hb = round(H * p["split_ratio"], 3)
    if joint == "weld":  # energy director on the bottom-shell rim (mid-wall line)
        lip = dfm.weld_lip(L - wall, W - wall, max(p["fillet"] - wall / 2, 0.5), base=min(0.6, wall * 0.4))
        placed = lip.moved(_loc(0, 0, z_base + hb))
        placed.std_meta = dict(lip.std_meta, name="Ultrasonic weld energy director", group="weld_lip")
        out.append(placed)
        return out
    size = _size_for(min(L, W))
    if fam == 3:  # wearable pod: 2 × M2 on the long axis, into inserts in top-shell bosses
        b = dfm.boss_dims("M2", "insert")
        x = L / 2 - wall - b["od"] / 2 - 0.6
        for sx in (1, -1):
            out += joints.screw_joint("M2", (sx * x, 0, z_base), (0, 0, 1), grip=wall, head="pan",
                                      boss_len=H - 2 * wall, wall=wall)
        return out
    # desk products / boxes: through the W2 bottom bosses (drafted, M2.5 pilot today) into top-shell insert bosses
    t = math.tan(math.radians(d))
    shrink = 2 * hb * t
    fl, fw, fr = L - shrink, W - shrink, max(p["fillet"] - hb * t, 0.0)
    inset = wall / math.cos(math.radians(d)) - wall * t
    il, iw, ir = fl - 2 * inset, fw - 2 * inset, max(fr - inset, 0.0)
    m = wall + 2.5 + 1.0
    pts = _boss_points(fam, il + 2 * wall, iw + 2 * wall, ir + wall, m, int(p["boss_count"]) or 4)
    boss_h = min(hb - wall - 1.0, 20.0)
    grip = wall + max(boss_h, 0.0)
    for x, y in pts:
        out += joints.screw_joint(size, (x, y, 0.0), (0, 0, 1), grip=grip, head="pan", boss_len=H - wall - grip,
                                  wall=wall)
    return out


def _loc(x: float, y: float, z: float):
    from build123d import Location

    return Location((x, y, z))


def pro_viewer_parts(params: dict[str, Any], features: set[str] | tuple = ()) -> list:
    """The labelled viewer parts of look.build_assembly (shells + details, or the wearable assembly) + pro details."""
    from api.cad.build import normalize
    from api.cad.look import details, shells_labelled

    p = normalize(params)
    if int(p["family"]) >= 3:
        from api.cad.wearables import assembly_parts

        parts = assembly_parts(p)
    else:
        parts = shells_labelled(p)
        try:
            parts += details(p, set(features))
        except Exception:  # noqa: BLE001 — cosmetic details never drop the shells
            pass
    return joints.add_parts(parts, enclosure_details(p), "body")


__all__ = ["enclosure_details", "pro_viewer_parts", "joint_for"]
