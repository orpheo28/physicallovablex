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
    "arm_reach": 110.0,  # C5: corrected (C2 motion study)
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

def _basic_build():
    return build_parts(P)


# === PRO DETAIL === (C5: the seed family 'drone' CAD_DETAIL_LEVEL=pro block, appended deterministically, no LLM)
P_PRO = {**{'body_length': 110.0, 'body_width': 62.0, 'body_height': 38.0, 'arm_length': 78.0, 'arm_diameter': 10.0, 'arm_angle_deg': 45.0, 'motor_diameter': 18.0, 'motor_height': 34.0, 'prop_diameter': 127.0, 'battery_length': 70.0, 'battery_width': 36.0, 'battery_height': 20.0, 'gimbal_diameter': 28.0, 'skid_height': 24.0}, **P, **{'arm_length': 91.1, 'motor_height': 26.65}}


def _f_lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro: clamshell body split on the parting line and screwed into heat-set inserts, arms clamped
    by M3 socket screws + nuts, motors on their M3 16 × 19 (≥ 22 mm stators) or M2 12 × 12 pattern, M5 prop nuts."""
    from api.cad.stdparts import add_parts, hex_nut, named, parting_split, screw_joint

    L, W, H = P["body_length"], P["body_width"], P["body_height"]
    z0 = P["skid_height"]
    body = next(q for q in parts if q.label == "body.1")
    lower_shell, upper_shell = parting_split(body, z0 + H * 0.4)
    parts = [q for q in parts if q is not body]
    parts.append(_f_lab(named(lower_shell, "Lower body shell", role="shell_bottom"), "body", 1))
    parts.append(_f_lab(named(upper_shell, "Upper body shell", role="shell_top"), "body", 2))
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
    r = _basic_build()
    r = r[1] if isinstance(r, tuple) else r
    parts = pro_details(P_PRO, list(r) if isinstance(r, list) else list(r.children))
    return parts
