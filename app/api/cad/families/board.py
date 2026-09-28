"""Board family (W19): surfboard (thruster/quad) or twin-tip kiteboard.

Hull = loft of rounded-rectangle cross sections along X (tail at -X, nose at +X): outline half-width from a
Catmull-Rom spline through plan-shape control points, rocker (nose/tail lift) as power curves, foil (thickness
peaks mid-board), rails = the section corner radius. Fin boxes + fins under the tail (both tips on a twin tip),
traction pad (surf) or pads + foot straps (kite). Origin: board centre, bottom of the flattest point on z=0.
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp, with_detail

NAME = "board"
CATEGORY = "board"
DESCRIPTION = "Hydrodynamic board (surfboard or twin-tip kiteboard) with lofted hull, rocker, rails and fins."


@dataclass
class Params:
    twin_tip: float = 0.0          # 0 = surfboard (pointed nose, squash tail), 1 = kiteboard (symmetric twin tip)
    length: float = 1850.0         # mm
    width: float = 530.0           # max width
    thickness: float = 62.0        # max thickness (foil peak)
    nose_width: float = 300.0      # width 12" (305 mm) from the nose / tip
    tail_width: float = 370.0      # width 12" from the tail
    rocker_nose: float = 115.0     # nose lift above the flat spot
    rocker_tail: float = 40.0
    rail_radius_frac: float = 0.45  # rail radius as a fraction of the local thickness (0.2 hard, 0.5 full round)
    fin_count: float = 3.0          # 0-5 (twin tip: fins per tip, 0-2 each side → 0-4 total)
    fin_height: float = 115.0

    def clamped(self) -> "Params":
        kite = self.twin_tip >= 0.5
        L = clamp(self.length, 1100, 1700) if kite else clamp(self.length, 1400, 3200)
        W = clamp(self.width, 360, 480) if kite else clamp(self.width, 420, 620)
        T = clamp(self.thickness, 12, 40) if kite else clamp(self.thickness, 45, 90)
        return Params(
            twin_tip=1.0 if kite else 0.0, length=L, width=W, thickness=T,
            nose_width=clamp(self.nose_width, 0.45 * W, 0.95 * W),
            tail_width=clamp(self.tail_width, 0.45 * W, 0.95 * W),
            rocker_nose=clamp(self.rocker_nose, 10, 60) if kite else clamp(self.rocker_nose, 40, 180),
            rocker_tail=clamp(self.rocker_tail, 10, 60) if kite else clamp(self.rocker_tail, 10, 90),
            rail_radius_frac=clamp(self.rail_radius_frac, 0.2, 0.49),
            fin_count=float(int(clamp(round(self.fin_count), 0, 4 if kite else 5))),
            fin_height=clamp(self.fin_height, 30, 70) if kite else clamp(self.fin_height, 80, 160),
        )


PRESETS = {
    "surf": Params(),
    "kite": Params(twin_tip=1.0, length=1380.0, width=420.0, thickness=22.0, nose_width=330.0, tail_width=330.0,
                   rocker_nose=30.0, rocker_tail=30.0, rail_radius_frac=0.45, fin_count=4.0, fin_height=45.0),
}


def default_params(variant: str = "surf") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["surf"]).clamped())


# === GEOMETRY ===
def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def catmull(ts, vs, t):
    """Catmull-Rom spline through (ts, vs), clamped ends."""
    t = min(max(t, ts[0]), ts[-1])
    i = 0
    while i < len(ts) - 2 and t > ts[i + 1]:
        i += 1
    p0, p1 = vs[max(i - 1, 0)], vs[i]
    p2, p3 = vs[i + 1], vs[min(i + 2, len(vs) - 1)]
    u = (t - ts[i]) / (ts[i + 1] - ts[i])
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def board_stations(P):
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
        hw = max(catmull(ts, ws, t) / 2, 5.0)
        foil = math.sin(math.pi * min(max(t, 0.02), 0.98)) ** 0.55
        th = max(T * (0.32 + 0.68 * foil), 4.0)
        th = min(th, 2 * hw - 1.0)
        z = P["rocker_nose"] * max(0.0, (t - 0.5) / 0.5) ** 2.3 + P["rocker_tail"] * max(0.0, (0.5 - t) / 0.5) ** 2.3
        out.append(((t - 0.5) * L, hw, th, z))
    return out


def hull(P):
    secs = []
    for x, hw, th, z in board_stations(P):
        r = min(th * P["rail_radius_frac"], th / 2 - 0.05, hw - 0.05)
        pl = Plane(origin=(x, 0, z + th / 2), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        secs.append(pl * RectangleRounded(2 * hw, th, r))
    return loft(secs)


def surface_at(P, x):
    """(bottom z, deck z, half width) of the hull at station x (linear between stations)."""
    st = board_stations(P)
    for a, b in zip(st, st[1:]):
        if a[0] <= x <= b[0]:
            u = (x - a[0]) / (b[0] - a[0])
            hw = a[1] + (b[1] - a[1]) * u
            th = a[2] + (b[2] - a[2]) * u
            z = a[3] + (b[3] - a[3]) * u
            return z, z + th, hw
    return st[-1][3], st[-1][3] + st[-1][2], st[-1][1]


def fin(base, height, thick, rake):
    """Swept fin in the XZ plane pointing down from z=0, leading edge toward +X, extruded across Y."""
    pts = [(base / 2, 0, 0)]
    for i in range(1, 9):  # leading edge sweeps back to the tip
        u = i / 8
        pts.append((base / 2 - rake * u ** 1.6 - 0.12 * base * u, 0, -height * u))
    for i in range(1, 8):  # trailing edge curves back up to the base
        u = i / 8
        pts.append((base / 2 - rake - 0.12 * base - (base * 0.25) * math.sin(math.pi * u) * 0.4 + (base * 0.1) * u,
                    0, -height * (1 - u)))
    pts.append((-base / 2, 0, 0))
    face = make_face(Polyline(*pts, close=True))
    return Pos(0, thick / 2, 0) * extrude(face, amount=thick)


def build_parts(P):
    parts = [lab(hull(P), "body", 1)]
    L = P["length"]
    kite = P["twin_tip"] >= 0.5
    n = int(P["fin_count"])
    fins, boxes = [], []
    if kite:
        per_end = [(-0.46 * L, 1), (0.46 * L, -1)]
        for xe, sgn in per_end:
            zb, zd, hw = surface_at(P, xe)
            ys = [-(hw - 30), hw - 30] if n >= 2 else [0.0]
            for y in ys[: max(n // 2, 1 if n else 0)]:
                f = fin(90, P["fin_height"], 5, 25)
                if sgn < 0:
                    f = mirror(f, about=Plane.YZ)
                fins.append(Pos(xe, y, zb + 1.5) * f)
    else:
        zt, _, hwt = surface_at(P, -0.5 * L + 300)
        layout = {0: [], 1: [(-0.5 * L + 110, 0, 1.0)], 2: [(-0.5 * L + 300, 1, 0.9)],
                  3: [(-0.5 * L + 300, 1, 0.9), (-0.5 * L + 90, 0, 1.0)],
                  4: [(-0.5 * L + 310, 1, 0.9), (-0.5 * L + 180, 2, 0.8)],
                  5: [(-0.5 * L + 310, 1, 0.9), (-0.5 * L + 180, 2, 0.8), (-0.5 * L + 90, 0, 0.7)]}[n]
        for x, kind, s in layout:
            zb, zd, hw = surface_at(P, x)
            ys = [0.0] if kind == 0 else [-(hw - 30), hw - 30] if kind == 1 else [-(hw - 55), hw - 55]
            for y in ys:
                fins.append(Pos(x, y, zb + 1.5) * fin(110 * s, P["fin_height"] * s, 7, 45 * s))
    for i, f in enumerate(fins):
        parts.append(lab(f, "fin", i + 1))
        c = f.bounding_box().center()
        zb = f.bounding_box().max.Z
        boxes.append(lab(Pos(c.X + 5, c.Y, zb - 1.9) * Box(125 if not kite else 100, 14, 1.2), "rubber", i + 1))
    parts += boxes
    k = len(boxes)
    if kite:  # pads + foot straps at both stance positions
        for xs in (-0.25 * L, 0.25 * L):
            zb, zd, hw = surface_at(P, xs)
            k += 1
            pad = Pos(xs, 0, zd - 2.5) * extrude(RectangleRounded(200, min(170, 1.6 * hw), 60), amount=12)
            parts.append(lab(pad, "rubber", k))
            strap = (Rot(0, 90, 0) * Torus(78, 11)) & (Pos(0, 0, 60) * Box(40, 200, 120))
            parts.append(lab(Pos(xs, 0, zd + 4) * strap, "accent", 1 + k))
            k += 1
    else:  # tail traction pad, following the deck at the tail
        xs = -0.5 * L + 190
        zb, zd, hw = surface_at(P, xs)
        tilt = math.degrees(math.atan2(surface_at(P, xs + 100)[1] - surface_at(P, xs - 100)[1], 200))
        pad = Pos(xs, 0, zd - 3) * (Rot(0, -tilt, 0) * extrude(RectangleRounded(300, max(1.7 * hw - 40, 80), 40), amount=7))
        parts.append(lab(pad, "rubber", k + 1))
    return parts
# === END GEOMETRY ===


# === PRO DETAIL ===
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
        zb = surface_at(P, c.X)[0]
        kit.append(box.along((c.X + 5, c.Y, zb), (0, 0, 1)))
    if not kite:
        x = -0.5 * L + 45
        kit.append(leash_plug().along((x, 0, surface_at(P, x)[1]), (0, 0, -1)))
    return add_parts(parts, kit, "rubber")
# === END PRO DETAIL ===


def build(params: Params | dict | None = None):
    """Deterministic board assembly → (Compound, labelled parts)."""
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    P = asdict(p.clamped())
    parts = with_detail(pro_details, P, build_parts(P))  # C1: CAD_DETAIL_LEVEL=pro adds hardware
    return Compound(children=parts), parts
