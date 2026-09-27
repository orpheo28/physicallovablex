"""Pocket kitesurf follow-me drone. Units mm; Z is up."""
import math
from build123d import *

P = {
    "body_length": 94.0,
    "body_width": 54.0,
    "body_height": 35.0,
    "body_base_z": 24.0,
    "arm_length": 68.0,
    "arm_diameter": 9.0,
    "arm_angle_deg": 53.0,
    "arm_reach": 83.0,
    "motor_diameter": 18.0,
    "motor_height": 27.0,
    "prop_diameter": 127.0,
    "battery_length": 69.0,
    "battery_width": 38.0,
    "battery_height": 19.0,
    "gimbal_diameter": 26.0,
    "skid_height": 24.0,
}

def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape

def rod(p1, p2, radius):
    a, b = Vector(*p1), Vector(*p2)
    direction = b - a
    return Plane(origin=(a + b) * 0.5, z_dir=direction) * Cylinder(radius, direction.length)

def soft(shape, radius):
    try:
        return fillet(shape.edges(), radius=radius)
    except Exception:
        return shape

def build_parts(P):
    parts = []
    L, W, H = P["body_length"], P["body_width"], P["body_height"]
    base = P["body_base_z"]

    # Compact, sealed PA12-GF fuselage; +X is the camera-facing nose.
    shell = Pos(0, 0, base) * extrude(
        RectangleRounded(L, W, 15), amount=H, taper=5
    )
    parts.append(lab(soft(shell, 4), "body", 1))

    # Recess-like dark nose panel and paired visual-tracking windows.
    parts.append(lab(
        Pos(L / 2 - 1, 0, base + 23) * Box(2.5, 35, 10),
        "coat", 1
    ))
    for i, y in enumerate((-12, 12), 1):
        parts.append(lab(
            Pos(L / 2 + 0.5, y, base + 24) *
            Rot(0, 90, 0) * Cylinder(3.3, 1.8),
            "glass", 10 + i
        ))

    angle = math.radians(P["arm_angle_deg"])
    reach = P["arm_reach"]
    arm_z = base + H * 0.54
    arm_radius = P["arm_diameter"] / 2
    rotor_z = arm_z + P["motor_height"]

    for sx in (1, -1):
        for sy in (1, -1):
            n = (0 if sx == 1 else 2) + (0 if sy == 1 else 1) + 1
            hinge_x, hinge_y = sx * 25, sy * 17
            mx = sx * reach * math.cos(angle)
            my = sy * reach * math.sin(angle)

            # Exposed vertical folding pivot and carbon-fibre tube.
            parts.append(lab(
                Pos(hinge_x, hinge_y, arm_z - 5) *
                Cylinder(8, 10, align=(Align.CENTER, Align.CENTER, Align.MIN)),
                "metal", n
            ))
            parts.append(lab(
                rod((hinge_x, hinge_y, arm_z), (mx, my, arm_z), arm_radius),
                "coat", n + 10
            ))
            parts.append(lab(
                Pos(mx, my, arm_z) *
                Cylinder(P["motor_diameter"] / 2, P["motor_height"],
                         align=(Align.CENTER, Align.CENTER, Align.MIN)),
                "metal", n + 20
            ))
            parts.append(lab(
                Pos(mx, my, rotor_z) * Cylinder(5, 5),
                "coat", n + 30
            ))

            # Two tapered blades form each five-inch folding propeller.
            half = P["prop_diameter"] / 2
            blade_profile = Polygon(
                (4, -4), (15, -6), (half - 8, -4),
                (half, -1), (half - 5, 3), (17, 5), (4, 3),
                align=None
            )
            blade = extrude(blade_profile, amount=2)
            orientation = 0 if sx == 1 else 90
            for side in (0, 180):
                parts.append(lab(
                    Pos(mx, my, rotor_z + 3) *
                    Rot(0, 0, orientation + side) * blade,
                    "coat", 40 + n * 2 + side // 180
                ))

            # Short resilient feet leave the underslung gimbal clear.
            foot_x, foot_y = mx * 0.76, my * 0.76
            parts.append(lab(
                rod((foot_x, foot_y, arm_z - 2),
                    (foot_x, foot_y, 4), 2.6),
                "rubber", n
            ))
            parts.append(lab(
                Pos(foot_x, foot_y, 3) *
                Sphere(3.4),
                "rubber", n + 10
            ))

    # Removable top-mounted recording battery and its status light.
    battery = Pos(-6, 0, base + H - 1) * Box(
        P["battery_length"], P["battery_width"], P["battery_height"],
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    parts.append(lab(soft(battery, 3), "accent", 1))
    parts.append(lab(
        Pos(19, 0, base + H + P["battery_height"]) * Box(11, 15, 1.5),
        "led", 1
    ))

    # Two-axis gimbal: transverse yoke, camera sphere and forward lens.
    gx = L * 0.34
    gd = P["gimbal_diameter"]
    parts.append(lab(
        Pos(gx, 0, base - 3) * Box(12, gd + 7, 7),
        "metal", 40
    ))
    for i, y in enumerate((-(gd / 2 + 2), gd / 2 + 2), 1):
        parts.append(lab(
            Pos(gx, y, 14) * Box(5, 3, 17),
            "coat", 50 + i
        ))
    parts.append(lab(Pos(gx, 0, 13) * Sphere(gd / 2), "coat", 60))
    parts.append(lab(
        Pos(gx + gd / 2, 0, 13) *
        Rot(0, 90, 0) * Cylinder(8, 4),
        "metal", 61
    ))
    parts.append(lab(
        Pos(gx + gd / 2 + 2.3, 0, 13) *
        Rot(0, 90, 0) * Cylinder(6, 1.5),
        "glass", 1
    ))
    return parts

def build():
    return build_parts(P)
