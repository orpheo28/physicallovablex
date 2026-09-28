"""Wall shelf bracket with shelf board.

Two wall brackets, each a wall plate, a horizontal arm and a diagonal brace between two points (rod helper using Plane(origin, z_dir)), countersunk screw holes in the plate and the arm, and a wooden shelf resting on both arms. The brace is fused into the plate/arm so the bracket is one solid. Use for wall shelves, console supports, cantilever arms.
tags: shelf, bracket, wall, cantilever, brace, diagonal, rod, countersunk, screws, wood, plank, storage
"""
import math

from build123d import *

P = {"plate_h": 200.0, "arm_len": 220.0, "w": 30.0, "t": 5.0, "brace_r": 6.0, "hole_r": 2.5,
     "csk_r": 5.0, "shelf_len": 600.0, "shelf_d": 250.0, "shelf_t": 22.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rod(p0, p1, r):
    d = Vector(p1) - Vector(p0)
    return Plane(origin=p0, z_dir=d) * Cylinder(r, d.length, align=(Align.CENTER, Align.CENTER, Align.MIN))


def csk(loc_plane, top):
    # countersunk screw cutter in the local frame of a face: Z is the face normal, face at z=top
    h = P["csk_r"] - P["hole_r"]
    return loc_plane * (Pos(0, 0, top - 30) * Cylinder(P["hole_r"], 60)
                        + Pos(0, 0, top - h) * Cone(P["hole_r"], P["csk_r"], h + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN)))


def build():
    ph, al, w, t = P["plate_h"], P["arm_len"], P["w"], P["t"]
    # wall is the XZ plane at y=0; the arm sticks out along +Y at the top of the plate
    plate = Pos(0, t / 2, ph / 2) * Box(w, t, ph)
    arm = Pos(0, al / 2, ph - t / 2) * Box(w, al, t)
    brace = rod((0, t, ph * 0.3), (0, al * 0.75, ph - t), P["brace_r"])
    bracket = plate + arm + brace
    wall_face = Plane(origin=(0, t, 0), z_dir=(0, 1, 0))  # screw from the front of the plate into the wall
    cuts = [Pos(0, 0, z) * csk(wall_face, 0) for z in (ph * 0.15, ph * 0.6)]
    cuts += [csk(Plane(origin=(0, y, ph), z_dir=(0, 0, 1)), 0) for y in (al * 0.4, al * 0.85)]
    bracket = bracket - cuts
    st = P["shelf_t"]
    # two identical brackets under the shelf, the shelf's back edge against the wall (y=0)
    xs = (-P["shelf_len"] / 2 + 100, P["shelf_len"] / 2 - 100)
    shelf = Pos(0, P["shelf_d"] / 2, ph + st / 2) * Box(P["shelf_len"], P["shelf_d"], st)
    centre = Pos(0, -P["shelf_d"] / 2, 0)  # re-centre the assembly on the origin
    return [lab(centre * Pos(x, 0, 0) * bracket, "metal", i + 1) for i, x in enumerate(xs)] + [lab(centre * shelf, "wood", 1)]
