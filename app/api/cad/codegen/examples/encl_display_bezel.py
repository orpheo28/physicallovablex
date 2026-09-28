"""Display bezel with recessed glass.

Front housing with a raised bezel frame around a recessed cover glass, like a panel meter or smart display.
Shows a stepped pocket (two nested Box cuts: glass seat, then a deeper display window) and a separate thin glass
plate seated below the bezel face.
tags: display, screen, bezel, glass, recess, stepped pocket, boolean, panel, housing, cover glass, lcd, front panel
"""
import math

from build123d import *

P = {"width": 160.0, "height": 100.0, "depth": 30.0, "corner": 8.0, "screen_w": 120.0, "screen_h": 72.0,
     "recess": 1.5, "glass_t": 1.1, "border": 6.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    W, Hh, D = P["width"], P["height"], P["depth"]
    body = extrude(RectangleRounded(W, Hh, P["corner"]), amount=D)  # device lies face-up, front face at z = D
    try:
        body = fillet(body.edges().group_by(Axis.Z)[-1], radius=3.0)
    except Exception:
        pass
    ow, oh = P["screen_w"] + 2 * P["border"], P["screen_h"] + 2 * P["border"]
    # Step 1: glass pocket (outer), step 2: deeper display window behind it.
    body = body - Pos(0, 0, D) * Box(ow, oh, 2 * (P["recess"] + P["glass_t"]))
    glass_z = D - P["recess"] - P["glass_t"]
    body = body - Pos(0, 0, glass_z) * Box(P["screen_w"], P["screen_h"], 8)  # window for the panel behind the glass
    glass = Pos(0, 0, glass_z) * Box(ow - 0.4, oh - 0.4, P["glass_t"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    screen = Pos(0, 0, glass_z - 0.3) * Box(P["screen_w"], P["screen_h"], 0.3, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return [lab(body, "body", 1), lab(glass, "glass", 1), lab(screen, "led", 1)]
