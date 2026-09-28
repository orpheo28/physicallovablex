"""USB-C port cutout on a device edge.

Rounded device edge with a stadium-shaped USB-C opening (8.4 x 2.6 mm), a slight chamfered lead-in, and the
receptacle shell inside. The cutout is a `SlotOverall` sketch on a side plane (`Plane.XZ` offset to the wall) extruded
into the body — the pattern for any connector/port opening on a side face.
tags: usb-c, usb, port, cutout, connector, charging, side face, plane, slot, extrude, boolean, receptacle
"""
import math

from build123d import *

P = {"length": 80.0, "width": 50.0, "height": 14.0, "corner": 8.0, "port_w": 8.4, "port_h": 2.6,
     "lead_in": 0.5, "depth": 7.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    L, W, H = P["length"], P["width"], P["height"]
    body = extrude(RectangleRounded(L, W, P["corner"]), amount=H)
    try:
        body = fillet(body.edges().group_by(Axis.Z)[-1], radius=2.5)
        body = fillet(body.edges().group_by(Axis.Z)[0], radius=2.5)
    except Exception:
        pass
    # Plane.XZ has normal -Y; offset(W/2) moves it to y = -W/2 (front edge). Sketch coords: x along X, y along Z.
    edge = Plane.XZ.offset(W / 2) * Pos(0, H / 2)
    pw, ph, li = P["port_w"], P["port_h"], P["lead_in"]
    port = extrude(edge * SlotOverall(pw, ph), amount=-P["depth"])  # negative amount = into the body (+Y)
    lead = extrude(edge * SlotOverall(pw + 2 * li, ph + 2 * li), amount=-li, taper=45)
    body = body - port - lead
    # Receptacle shell and tongue inside the opening.
    shell = extrude(Plane.XZ.offset(W / 2 - 1.0) * Pos(0, H / 2) * (SlotOverall(pw - 0.2, ph - 0.2) - SlotOverall(pw - 0.8, ph - 0.8)),
                    amount=-(P["depth"] - 1.0))
    tongue = Pos(0, -W / 2 + 1.0 + (P["depth"] - 1.0) / 2 + 1.0, H / 2) * Box(pw - 2.4, P["depth"] - 3.0, 0.7)
    return [lab(body, "body", 1), lab(shell, "metal", 1), lab(tongue, "accent", 1)]
