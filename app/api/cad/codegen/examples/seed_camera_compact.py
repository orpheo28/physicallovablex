"""Camera (compact) — seed program of our parametric family.

Camera: rounded body, grip, lens barrel + glass, rear display, shutter, dial, viewfinder, flash, print slot. Full product: parameters dict P, geometry helpers, labelled parts.
tags: camera, lens, barrel, grip, display, shutter, dial, viewfinder, instant, flash, compact
"""
import math

from build123d import *

P = {
    'width': 124.0,
    'depth': 52.0,
    'height': 78.0,
    'corner_radius': 10.0,
    'grip_depth': 12.0,
    'lens_diameter': 46.0,
    'lens_length': 26.0,
    'display_width': 72.0,
    'instant': 0.0,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build_parts(P):
    parts = []
    W, D, H, r = P["width"], P["depth"], P["height"], P["corner_radius"]
    body = extrude(RectangleRounded(W, D, min(r, D / 2 - 1)), amount=H)
    try:
        body = fillet(body.edges().group_by(Axis.Z)[-1], radius=min(r, H * 0.15))
    except Exception:
        pass
    parts.append(lab(body, "body", 1))
    # leatherette band around the lower body
    band = Pos(0, 0, H * 0.18) * extrude(RectangleRounded(W + 0.8, D + 0.8, min(r, D / 2 - 1) + 0.4), amount=H * 0.5)
    parts.append(lab(band - Pos(0, 0, H * 0.18 - 1) * extrude(RectangleRounded(W - 2, D - 2, max(min(r, D / 2 - 1) - 1, 0.5)), amount=H * 0.5 + 2), "rubber", 1))
    # grip on the right front
    g = P["grip_depth"]
    if g > 0.5:
        grip = Pos(W * 0.36, -D / 2 - g / 2 + 2, H * 0.08) * Box(W * 0.2, g + 4, H * 0.84, align=(Align.CENTER, Align.CENTER, Align.MIN))
        try:
            grip = fillet(grip.edges().filter_by(Axis.Z), radius=min(g, W * 0.1) * 0.45)
        except Exception:
            pass
        parts.append(lab(grip, "rubber", 2))
    # lens barrel (front, -Y) + glass
    lr, ll = P["lens_diameter"] / 2, P["lens_length"]
    lx = -W * 0.1 if P["instant"] < 0.5 else 0.0
    lz = H * 0.5 if P["instant"] < 0.5 else H * 0.42
    barrel = Pos(lx, -D / 2 - ll / 2, lz) * (Rot(90, 0, 0) * Cylinder(lr, ll))
    parts.append(lab(barrel, "metal", 1))
    parts.append(lab(Pos(lx, -D / 2 - ll / 2, lz) * (Rot(90, 0, 0) * Cylinder(lr + 1.5, ll * 0.3)), "coat", 1))
    parts.append(lab(Pos(lx, -D / 2 - ll - 0.6, lz) * (Rot(90, 0, 0) * Cylinder(lr * 0.72, 1.2)), "glass", 1))
    # rear display
    if P["display_width"] > 1:
        dw = min(P["display_width"], W - 16)
        parts.append(lab(Pos(-W * 0.08, D / 2 + 0.6, H * 0.48) * Box(dw, 1.4, min(dw * 0.66, H - 16)), "glass", 2))
    # top plate: shutter button, mode dial
    parts.append(lab(Pos(W * 0.34, -D * 0.1, H) * Cylinder(5.5, 4, align=(Align.CENTER, Align.CENTER, Align.MIN)), "button", 1))
    parts.append(lab(Pos(W * 0.18, D * 0.1, H) * Cylinder(9, 6, align=(Align.CENTER, Align.CENTER, Align.MIN)), "metal", 2))
    # viewfinder + flash windows on the front
    parts.append(lab(Pos(W * 0.3, -D / 2 - 0.5, H * 0.8) * Box(16, 1.2, 11), "glass", 3))
    parts.append(lab(Pos(-W * 0.34, -D / 2 - 0.5, H * 0.8) * Box(22, 1.2, 10), "diffuser", 1))
    if P["instant"] >= 0.5:
        parts.append(lab(Pos(0, -D * 0.1, H - 1.5) * Box(W * 0.62, 4, 3), "coat", 2))  # print slot
    parts.append(lab(Pos(W * 0.4, D / 2 + 0.5, H * 0.2) * Box(3, 1, 3), "led", 1))
    return parts


def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro: bottom plate split off the body on its parting line and held by 4 countersunk M2 into
    heat-set inserts, 2 M2 pan screws per end cap, ISO 1222 1/4"-20 tripod socket insert under the lens axis."""
    from api.cad.stdparts import add_parts, named, parting_split, screw_joint, tripod_insert

    W, D, H = P["width"], P["depth"], P["height"]
    lx = -W * 0.1 if P["instant"] < 0.5 else 0.0
    body = next(q for q in parts if q.label == "body.1")
    zp = min(H * 0.1, 8.0)
    bottom_plate, upper_body = parting_split(body, zp)
    parts = [q for q in parts if q is not body]
    parts.append(lab(named(upper_body, "Camera body", role="shell_top"), "body", 1))
    parts.append(lab(named(bottom_plate, "Bottom plate", role="shell_bottom"), "body", 2))
    kit = [tripod_insert().along((lx, 0, 0), (0, 0, 1))]
    for sx in (1, -1):
        for sy in (1, -1):
            kit += screw_joint("M2", (sx * W * 0.38, sy * D * 0.25, 0), (0, 0, 1), grip=zp, head="countersunk")
        for sz in (0.62, 0.86):  # end caps
            kit += screw_joint("M2", (sx * W / 2, 0, H * sz), (-sx, 0, 0), grip=1.5, head="pan")
    return add_parts(parts, kit, "body")


def build():
    return pro_details(P, build_parts(P))
