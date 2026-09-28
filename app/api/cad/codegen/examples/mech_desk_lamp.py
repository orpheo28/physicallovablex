"""Articulated desk lamp.

A weighted base, two arm segments set at chosen angles and a conical shade, with joint positions computed by trigonometry and each segment placed with a rod(p0, p1) helper (Plane(origin, z_dir) * Cylinder). The shade is a hollow Cone oriented along its aim vector. Use for any jointed arm or linkage posed at angles.
tags: desk lamp, lamp, arm, joint, articulated, angle, trigonometry, rod, plane, cone, shade, weighted base
"""
import math

from build123d import *

P = {"base_r": 80.0, "base_h": 22.0, "arm1": 320.0, "arm2": 300.0, "a1": 70.0, "a2": -25.0,
     "arm_r": 7.0, "joint_r": 13.0, "shade_r": 70.0, "shade_len": 110.0, "aim": -60.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rod(p0, p1, r):
    d = Vector(p1) - Vector(p0)
    return Plane(origin=p0, z_dir=d) * Cylinder(r, d.length, align=(Align.CENTER, Align.CENTER, Align.MIN))


def joint(p, r):
    # joint barrel with its axis along Y (the arms swing in the XZ plane)
    return Pos(*p) * Rot(90, 0, 0) * Cylinder(r, 2.4 * r)


def build():
    bh = P["base_h"]
    base = Pos(0, 0, bh / 2) * Cylinder(P["base_r"], bh)
    try:
        base = fillet(base.edges().group_by(Axis.Z)[-1], radius=8)
    except Exception:
        pass
    j0 = Vector(-P["base_r"] * 0.4, 0, bh + 1.5 * P["joint_r"])
    a1, a2 = math.radians(P["a1"]), math.radians(P["a2"])
    j1 = j0 + Vector(P["arm1"] * math.cos(a1), 0, P["arm1"] * math.sin(a1))
    j2 = j1 + Vector(P["arm2"] * math.cos(a2), 0, P["arm2"] * math.sin(a2))
    arms = rod(j0, j1, P["arm_r"]) + rod(j1, j2, P["arm_r"])
    # post ends at the joint centre: a post tangent to the barrel would fuse into an invalid solid
    post = Pos(j0.X, 0, bh) * Cylinder(P["joint_r"] * 0.8, 1.5 * P["joint_r"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    # shade: hollow cone whose axis follows the aim direction from the last joint
    aim = math.radians(P["aim"])
    d = Vector(math.cos(aim), 0, math.sin(aim))
    sr, sl = P["shade_r"], P["shade_len"]
    frame = Plane(origin=j2 + d * 12, z_dir=d)
    shade = frame * (Cone(18, sr, sl, align=(Align.CENTER, Align.CENTER, Align.MIN))
                     - Pos(0, 0, 2) * Cone(16, sr - 2, sl, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    bulb = (frame * Pos(0, 0, sl * 0.55)) * Sphere(26)
    return [lab(base, "metal", 1), lab(arms, "body", 1), lab(joint(j0, P["joint_r"]) + post, "metal", 2),
            lab(joint(j1, P["joint_r"]), "metal", 3), lab(joint(j2, P["joint_r"] * 0.8), "metal", 4),
            lab(shade, "body", 2), lab(bulb, "diffuser", 1)]
