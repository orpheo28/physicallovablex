"""Sheet-metal wall-mount bracket.

L-shaped bent sheet bracket with an inside bend radius, countersunk wall screw holes and a slotted device flange.
The L section with a true bend is a 2D profile (`Polyline` + `offset` of a wire -> constant-thickness strip with
arcs) extruded to width; holes and slots cut with `Plane.XZ`/`Plane.XY` placed cylinders and SlotOverall.
tags: bracket, wall mount, sheet metal, bend radius, l bracket, holes, slots, countersink, offset, extrude, steel
"""
import math

from build123d import *

P = {"leg_wall": 70.0, "leg_shelf": 50.0, "width": 40.0, "t": 2.0, "bend_r": 3.0, "hole_d": 5.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    t, w, R = P["t"], P["width"], P["bend_r"]
    # Centre-line of the sheet in the XZ plane: up the wall (x=0), bend, out along the shelf (z=0).
    path = FilletPolyline((0, P["leg_wall"]), (0, 0), (P["leg_shelf"], 0), radius=R + t / 2)
    strip = offset(path, amount=t / 2, side=Side.BOTH)  # closed wire around the centre-line
    bracket = extrude(Plane.XZ * make_face(strip), amount=w / 2, both=True)
    bracket = Pos(0, 0, t / 2) * bracket  # shelf underside on z = 0
    # Wall holes (through X) with countersink cones, device slots in the shelf (through Z).
    for z in (P["leg_wall"] * 0.45, P["leg_wall"] * 0.85):
        axis = Plane.YZ.offset(-t) * Pos(0, z)
        bracket = bracket - axis * Cylinder(P["hole_d"] / 2, 4 * t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        bracket = bracket - axis * Cone(P["hole_d"] / 2, P["hole_d"], t * 1.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x in (P["leg_shelf"] * 0.45, P["leg_shelf"] * 0.8):
        bracket = bracket - Pos(x, 0, 0) * extrude(Rot(0, 0, 90) * SlotOverall(w * 0.5, P["hole_d"]), amount=3 * t, both=True)
    return [lab(Pos(-P["leg_shelf"] / 2, 0, 0) * bracket, "steel", 1)]
