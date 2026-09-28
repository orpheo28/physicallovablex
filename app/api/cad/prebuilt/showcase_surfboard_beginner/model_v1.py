"""Classic 7'6" beginner surfboard. Units are millimetres; Z is up."""
import math
from build123d import *

P = {
    "length": 2286.0,
    "width": 560.0,
    "thickness": 82.0,
    "nose_width_12in": 380.0,
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


def _basic_build():
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


# === PRO DETAIL === (C5: the seed family 'board' CAD_DETAIL_LEVEL=pro block, appended deterministically, no LLM)
P_PRO = {**{'twin_tip': 0.0, 'length': 1850.0, 'width': 530.0, 'thickness': 62.0, 'nose_width': 300.0, 'tail_width': 370.0, 'rocker_nose': 115.0, 'rocker_tail': 40.0, 'rail_radius_frac': 0.45, 'fin_count': 3.0, 'fin_height': 115.0}, **P, **{}}


def _f_board_stations(P):
    """(x, half_width, thickness, bottom_z) along the board; t = 0 tail, 1 nose."""
    L, W, T = P["length"], P["width"], P["thickness"]
    kite = P["twin_tip"] >= 0.5
    f12 = min(305.0 / L, 0.3)  # 12" from each end
    if kite:
        ts = [0.0, 0.012, 0.04, f12, 0.5, 1 - f12, 0.96, 0.988, 1.0]
        ws = [0.30 * W, 0.62 * P["tail_width"], 0.86 * P["tail_width"], P["tail_width"], W,
              P["nose_width"], 0.86 * P["nose_width"], 0.62 * P["nose_width"], 0.30 * W]
    else:
        ts = [0.0, 0.04, f12, 0.42, 1 - f12, 0.95, 1.0]
        ws = [0.62 * P["tail_width"], 0.82 * P["tail_width"], P["tail_width"], W, P["nose_width"],
              0.45 * P["nose_width"], 14.0]
    out = []
    n = 26
    for i in range(n + 1):
        t = 0.5 - 0.5 * math.cos(math.pi * i / n)  # denser at both ends
        hw = max(_f_catmull(ts, ws, t) / 2, 5.0)
        foil = math.sin(math.pi * min(max(t, 0.02), 0.98)) ** 0.55
        th = max(T * (0.32 + 0.68 * foil), 4.0)
        th = min(th, 2 * hw - 1.0)
        z = P["rocker_nose"] * max(0.0, (t - 0.5) / 0.5) ** 2.3 + P["rocker_tail"] * max(0.0, (0.5 - t) / 0.5) ** 2.3
        out.append(((t - 0.5) * L, hw, th, z))
    return out


def _f_catmull(ts, vs, t):
    """Catmull-Rom spline through (ts, vs), clamped ends."""
    t = min(max(t, ts[0]), ts[-1])
    i = 0
    while i < len(ts) - 2 and t > ts[i + 1]:
        i += 1
    p0, p1 = vs[max(i - 1, 0)], vs[i]
    p2, p3 = vs[i + 1], vs[min(i + 2, len(vs) - 1)]
    u = (t - ts[i]) / (ts[i + 1] - ts[i])
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def _f_surface_at(P, x):
    """(bottom z, deck z, half width) of the hull at station x (linear between stations)."""
    st = _f_board_stations(P)
    for a, b in zip(st, st[1:]):
        if a[0] <= x <= b[0]:
            u = (x - a[0]) / (b[0] - a[0])
            hw = a[1] + (b[1] - a[1]) * u
            th = a[2] + (b[2] - a[2]) * u
            z = a[3] + (b[3] - a[3]) * u
            return z, z + th, hw
    return st[-1][3], st[-1][3] + st[-1][2], st[-1][1]


def pro_details(P, parts):
    """CAD_DETAIL_LEVEL=pro: real fin boxes (single-tab, glass-filled nylon) set flush into the bottom under each fin,
    and a leash plug in the deck at the tail (surfboard). Glassed in — no screws."""
    from api.cad.stdparts import add_parts, fin_box, leash_plug

    L = P["length"]
    kite = P["twin_tip"] >= 0.5
    fins = [q for q in parts if (q.label or "").startswith("fin.")]
    slabs = {f"rubber.{i + 1}" for i in range(len(fins))}  # the basic fin-box slabs
    parts = [q for q in parts if q.label not in slabs]
    box = fin_box()
    kit = []
    for f in fins:
        c = f.bounding_box().center()
        zb = _f_surface_at(P, c.X)[0]
        kit.append(box.along((c.X + 5, c.Y, zb), (0, 0, 1)))
    if not kite:
        x = -0.5 * L + 45
    return add_parts(parts, kit, "rubber")


def build():
    r = _basic_build()
    r = r[1] if isinstance(r, tuple) else r
    parts = pro_details(P_PRO, list(r) if isinstance(r, list) else list(r.children))
    return parts
