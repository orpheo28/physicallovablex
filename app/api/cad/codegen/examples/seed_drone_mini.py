"""Drone (mini) — seed program of our parametric family.

Quadcopter: centre body, 4 foldable arms with motors + props, top battery, camera gimbal pod, skids. Full product: parameters dict P, geometry helpers, labelled parts.
tags: drone, quadcopter, arms, propellers, motors, gimbal, camera, battery, skids, uav, mini
"""
import math

from build123d import *

P = {
    'body_length': 110.0,
    'body_width': 62.0,
    'body_height': 38.0,
    'arm_length': 78.0,
    'arm_diameter': 10.0,
    'arm_angle_deg': 45.0,
    'motor_diameter': 18.0,
    'motor_height': 34.0,
    'prop_diameter': 127.0,
    'battery_length': 70.0,
    'battery_width': 36.0,
    'battery_height': 20.0,
    'gimbal_diameter': 28.0,
    'skid_height': 24.0,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def rod(p1, p2, r):
    """Cylinder of radius r from point p1 to point p2."""
    a, b = Vector(*p1), Vector(*p2)
    d = b - a
    return Plane(origin=(a + b) * 0.5, z_dir=d) * Cylinder(r, d.length)


def soft(shape, radius):
    try:
        return fillet(shape.edges(), radius=radius)
    except Exception:
        return shape


def build_parts(P):
    parts = []
    L, W, H = P["body_length"], P["body_width"], P["body_height"]
    z0 = P["skid_height"]
    # centre body: rounded plan, slightly tapered to the top, nose forward (+X)
    body = Pos(0, 0, z0) * extrude(RectangleRounded(L, W, min(L, W) * 0.3), amount=H, taper=6)
    parts.append(lab(soft(body, min(H, W) * 0.18), "body", 1))
    # arms at ±angle, front and back, motors + props at the tips
    a = math.radians(P["arm_angle_deg"])
    ar = P["arm_diameter"] / 2
    zc = z0 + H * 0.55
    reach = P["arm_length"] + min(L, W) * 0.35
    md, mh = P["motor_diameter"], P["motor_height"]
    n = 0
    for sx in (1, -1):
        for sy in (1, -1):
            n += 1
            x0, y0 = sx * L * 0.25, sy * W * 0.3
            x1, y1 = sx * reach * math.cos(a), sy * reach * math.sin(a)
            parts.append(lab(rod((x0, y0, zc), (x1, y1, zc), ar), "coat", n))
            parts.append(lab(Pos(x1, y1, zc) * Cylinder(md / 2, mh, align=(Align.CENTER, Align.CENTER, Align.MIN)), "metal", n))
            hub_z = zc + mh
            parts.append(lab(Pos(x1, y1, hub_z) * Cylinder(md * 0.22, 5, align=(Align.CENTER, Align.CENTER, Align.MIN)), "accent", n))
            blade = Pos(x1, y1, hub_z + 2) * Rot(0, 0, 30 * n) * Box(P["prop_diameter"], P["prop_diameter"] * 0.075, 2.2)
            parts.append(lab(blade, "accent", 10 + n))
            # skid leg under each motor
            parts.append(lab(rod((x1 * 0.8, y1 * 0.8, zc), (x1 * 0.8, y1 * 0.8, 2), ar * 0.55), "rubber", n))
            parts.append(lab(Pos(x1 * 0.8, y1 * 0.8, 2) * Sphere(ar * 0.9), "rubber", 10 + n))
    # battery on top
    bl, bw, bh = P["battery_length"], P["battery_width"], P["battery_height"]
    batt = Pos(-L * 0.05, 0, z0 + H - 2) * Box(bl, bw, bh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    parts.append(lab(soft(batt, min(bh, bw) * 0.2), "accent", 30))
    parts.append(lab(Pos(-L * 0.05 + bl / 2 - 6, 0, z0 + H - 2 + bh) * Box(8, bw * 0.5, 3), "led", 1))
    # gimbal pod under the nose: yoke + camera ball + lens
    gd = P["gimbal_diameter"]
    gx = L * 0.36
    parts.append(lab(Pos(gx, 0, z0 - 4) * Box(gd * 0.5, gd * 1.1, 8), "coat", 20))
    ball = Pos(gx, 0, z0 - 6 - gd / 2) * Sphere(gd / 2)
    parts.append(lab(ball, "coat", 21))
    parts.append(lab(Pos(gx + gd * 0.42, 0, z0 - 6 - gd / 2) * (Rot(0, 90, 0) * Cylinder(gd * 0.26, gd * 0.25)), "glass", 1))
    return parts


def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro: clamshell body split on the parting line and screwed into heat-set inserts, arms clamped
    by M3 socket screws + nuts, motors on their M3 16 × 19 (≥ 22 mm stators) or M2 12 × 12 pattern, M5 prop nuts."""
    from api.cad.stdparts import add_parts, hex_nut, named, parting_split, screw_joint

    L, W, H = P["body_length"], P["body_width"], P["body_height"]
    z0 = P["skid_height"]
    body = next(q for q in parts if q.label == "body.1")
    lower_shell, upper_shell = parting_split(body, z0 + H * 0.4)
    parts = [q for q in parts if q is not body]
    parts.append(lab(named(lower_shell, "Lower body shell", role="shell_bottom"), "body", 1))
    parts.append(lab(named(upper_shell, "Upper body shell", role="shell_top"), "body", 2))
    kit = []
    for sx in (1, -1):  # 4 body screws from underneath into inserts in the upper shell
        for sy in (1, -1):
            kit += screw_joint("M2", (sx * L * 0.3, sy * W * 0.26, z0 + 0.4), (0, 0, 1), grip=H * 0.4 - 0.4, head="pan")
    a = math.radians(P["arm_angle_deg"])
    ar = P["arm_diameter"] / 2
    zc = z0 + H * 0.55
    reach = P["arm_length"] + min(L, W) * 0.35
    md, mh = P["motor_diameter"], P["motor_height"]
    size, pat = ("M3", ((8.0, 0.0), (-8.0, 0.0), (0.0, 9.5), (0.0, -9.5))) if md >= 22 else \
        ("M2", ((6.0, 0.0), (-6.0, 0.0), (0.0, 6.0), (0.0, -6.0)))
    for sx in (1, -1):
        for sy in (1, -1):
            x0, y0 = sx * L * 0.25, sy * W * 0.3
            x1, y1 = sx * reach * math.cos(a), sy * reach * math.sin(a)
            dx, dy = x1 - x0, y1 - y0
            n = math.hypot(dx, dy)
            ux, uy = dx / n, dy / n
            for t in (0.36, 0.44):  # arm clamp: two M3 through the arm root, nut on top
                kit += screw_joint("M3", (x0 + dx * t, y0 + dy * t, zc - ar), (0, 0, 1), grip=2 * ar, head="socket", into="nut")
            ang = math.atan2(uy, ux)
            for px, py in pat:  # motor mount: screws up through the arm tip into the stator base
                rx = px * math.cos(ang) - py * math.sin(ang)
                ry = px * math.sin(ang) + py * math.cos(ang)
                kit += screw_joint(size, (x1 + rx, y1 + ry, zc - ar), (0, 0, 1), grip=ar, head="socket", into="tap")
            kit.append(hex_nut("M5").at(x1, y1, zc + mh + 5))  # prop nut on the 5 mm shaft
    return add_parts(parts, kit, "body")


def build():
    return pro_details(P, build_parts(P))
