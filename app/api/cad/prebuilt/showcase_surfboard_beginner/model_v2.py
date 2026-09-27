"""Classic 7'6" beginner surfboard. Units are millimetres; Z is up."""
import math
from build123d import *

P = {
    "length": 2286.0,
    "width": 560.0,
    "thickness": 82.0,
    "nose_width_12in": 430.0,
    "tail_width_12in": 390.0,
    "nose_rocker": 100.0,
    "tail_rocker": 42.0,
    "rail_radius_fraction": 0.46,
    "side_fin_height": 88.0,
    "centre_fin_height": 102.0,
}


def catmull(ts, values, t):
    t = min(max(t, ts[0]), ts[-1])
    i = 0
    while i < len(ts) - 2 and t > ts[i + 1]:
        i += 1
    a, b = values[max(i - 1, 0)], values[i]
    c, d = values[i + 1], values[min(i + 2, len(values) - 1)]
    u = (t - ts[i]) / (ts[i + 1] - ts[i])
    return 0.5 * (
        2 * b + (-a + c) * u
        + (2 * a - 5 * b + 4 * c - d) * u * u
        + (-a + 3 * b - 3 * c + d) * u * u * u
    )


def stations():
    L = P["length"]
    q = 305.0 / L
    ts = [0.0, 0.035, q, 0.40, 0.62, 1 - q, 0.95, 1.0]
    widths = [
        245.0, 318.0, P["tail_width_12in"], 550.0,
        P["width"], P["nose_width_12in"], 185.0, 14.0,
    ]
    result = []
    for i in range(31):
        t = 0.5 - 0.5 * math.cos(math.pi * i / 30)
        half_width = max(5.0, catmull(ts, widths, t) / 2)
        foil = math.sin(math.pi * min(max(t, 0.02), 0.98)) ** 0.55
        thick = min(P["thickness"] * (0.32 + 0.68 * foil), 2 * half_width - 1)
        rocker = (
            P["nose_rocker"] * max(0, 2 * t - 1) ** 2.3
            + P["tail_rocker"] * max(0, 1 - 2 * t) ** 2.3
        )
        result.append(((t - 0.5) * L, half_width, thick, rocker))
    return result


def surface_at(x):
    sections = stations()
    for a, b in zip(sections, sections[1:]):
        if a[0] <= x <= b[0]:
            u = (x - a[0]) / (b[0] - a[0])
            return tuple(a[j] + u * (b[j] - a[j]) for j in (1, 2, 3))
    return sections[-1][1:]


def make_hull():
    profiles = []
    for x, half_width, thick, bottom in stations():
        radius = min(
            thick * P["rail_radius_fraction"],
            thick / 2 - 0.05,
            half_width - 0.05,
        )
        plane = Plane(
            origin=(x, 0, bottom + thick / 2),
            x_dir=(0, 1, 0),
            z_dir=(1, 0, 0),
        )
        profiles.append(plane * RectangleRounded(2 * half_width, thick, radius))
    return loft(profiles)


def make_fin(base, height, thickness, rake):
    """A swept-back fin, with its root at local z=0."""
    points = [(base / 2, 0, 0)]
    for i in range(1, 9):
        u = i / 8
        points.append(
            (base / 2 - rake * u ** 1.6 - 0.12 * base * u, 0, -height * u)
        )
    for i in range(1, 8):
        u = i / 8
        points.append(
            (
                base / 2 - rake - 0.12 * base
                - 0.1 * base * math.sin(math.pi * u)
                + 0.1 * base * u,
                0,
                -height * (1 - u),
            )
        )
    points.append((-base / 2, 0, 0))
    return Pos(0, thickness / 2, 0) * extrude(
        make_face(Polyline(*points, close=True)), amount=thickness
    )


def build():
    parts = []
    hull = make_hull()
    hull.label = "body.1"
    parts.append(hull)

    L = P["length"]
    fin_positions = [
        (-L / 2 + 315, -137, P["side_fin_height"], 1),
        (-L / 2 + 315, 137, P["side_fin_height"], 2),
        (-L / 2 + 130, 0, P["centre_fin_height"], 3),
    ]
    for x, y, height, number in fin_positions:
        half_width, thick, bottom = surface_at(x)
        scale = height / P["centre_fin_height"]
        blade = Pos(x, y, bottom + 1.5) * make_fin(
            112 * scale, height, 7, 44 * scale
        )
        blade.label = f"fin.{number}"
        parts.append(blade)

        # Flush, dark fin-box detail at each root.
        box = Pos(x + 5, y, bottom + 1) * Box(108 * scale, 13, 2)
        box.label = f"rubber.{number}"
        parts.append(box)

    # Move the complete assembly together so its lowest fin tip rests on z=0.
    lowest = min(part.bounding_box().min.Z for part in parts)
    return [Pos(0, 0, -lowest) * part for part in parts]
