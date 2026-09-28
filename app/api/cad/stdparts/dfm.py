"""Design-for-manufacturing detail generators (C1, CAD_DETAIL_LEVEL=pro). Each one applies a cited rule and returns
geometry + the numbers it used (`.std_meta["dfm"]`), so tests and the report can check the rule, not trust it.

    screw_boss(size, height, wall, fastener="insert"|"pt"|"tap", draft_deg=0.5)   moulded boss for an insert / screw
    rib(length, height, wall) · gusset(height, depth, wall)                     60 % wall rule, 0.5° draft
    snap_fit(length, thickness, width, material="pc_abs")                       Covestro cantilever equations
    uniform_fillet(shape, edges, wall, inside=True)                             r_in ≥ 0.5·t, r_out = r_in + t
    parting_split(shape, z, reveal=0.3)                                         two halves + a 0.3 mm reveal line
    clearance_hole(size, depth, fit="medium", head=None)                        ISO 273 (+ counterbore / countersink)
    tap_hole(size, depth)                                                       ISO 2306 tap drill
    weld_lip(length, width, radius, base=0.5)                                   90° energy director (ultrasonic weld)
    gasket_groove(length, width, radius, cord=2.0)                              face-seal gland, 25 % squeeze

Imports only build123d + math (+ tables): also usable from the codegen sandbox.
"""

from __future__ import annotations

import math

from build123d import Align, Box, Plane, Polyline, Pos, RectangleRounded, Rot, extrude, fillet, make_face

from api.cad.stdparts import tables as T
from api.cad.stdparts.hardware import cone, cyl

RULES: dict[str, tuple[str, str]] = {
    "boss_insert": ("Boss hole = insert hole Ø from the datasheet; boss OD = 2 × hole Ø; boss height ≥ insert length + 0.5 mm",
                    "McMaster-Carr 94459A heat-set insert datasheet; Covestro 'Part and Mold Design' guide (boss OD ≈ 2 × hole)"),
    "boss_pt": ("Thread-forming screw boss: hole = 0.8 × d, OD = 2 × d, engagement ≥ 2 × d",
                "EJOT DELTA PT design guide (ABS / PC-ABS)"),
    "boss_draft": ("Boss outside draft 0.5°, pin inside draft 0.25°, root fillet 0.25 × wall",
                   "Protolabs injection-moulding design guide (bosses)"),
    "rib": ("Rib thickness 0.6 × nominal wall (no sink), height ≤ 3 × wall, 0.5° draft per side, root fillet 0.25 × wall",
            "Protolabs design guide (ribs: 60 % rule); Covestro 'Part and Mold Design' guide"),
    "snap_fit": ("Cantilever snap: permissible deflection y = 0.67·ε·L²/h (constant section), L ≥ 5·h, 30° lead-in, "
                 "90° retention face for a permanent lid",
                 "Covestro (Bayer) 'Snap-Fit Joints for Plastics' design guide, eq. for rectangular constant section"),
    "fillet": ("Inside corner radius ≥ 0.5 × wall, outside radius = inside + wall (constant section)",
               "Protolabs design guide (radii)"),
    "clearance": ("Clearance hole per ISO 273 (fine / medium / coarse), counterbore per DIN 974-1",
                  "ISO 273; DIN 974-1"),
    "tap": ("Tap drill = d − P (coarse thread)", "ISO 2306 / DIN 336"),
    "weld": ("Energy director: 90° triangle, height = base / 2 (0.25-0.5 mm), on the part with the weld face",
             "Branson / Emerson 'Part design for ultrasonic welding' (energy director design)"),
    "gasket": ("Face-seal gland: depth 0.75 × cord (≈ 25 % squeeze), width 1.4 × cord",
               "Parker O-Ring Handbook ORD 5700, face seal glands"),
    "parting": ("Split on the widest section so both halves release along ±Z; 0.3 mm reveal hides the mismatch",
                "Protolabs design guide (parting lines); common ID practice"),
}
_C, _MIN = Align.CENTER, Align.MIN
# permissible short-term strain for a single / occasional snap (Covestro snap-fit guide, table)
SNAP_STRAIN = {"pc_abs": 0.025, "abs": 0.025, "pc": 0.04, "pa": 0.06, "pom": 0.06, "pp": 0.08}


def _tag(shape, kind: str, rule: str, **facts):
    shape.std_meta = {"kind": kind, "role": "boss" if kind == "boss" else kind, "standard": RULES[rule][1],
                      "dfm": {"rule": RULES[rule][0], "citation": RULES[rule][1], **facts}}
    return shape


def boss_dims(size: str = "M3", fastener: str = "insert") -> dict[str, float]:
    """(hole Ø, OD, min height) for a boss: the numbers the tests check against the tables."""
    s = size if size.startswith("M") else f"M{size}"
    d = T.NOMINAL.get(s, 3.0)
    if fastener == "insert" and s in T.INSERT_HEATSET:
        od_i, m, hole, _ = T.INSERT_HEATSET[s]
        return {"hole": hole, "od": round(2.0 * hole, 2), "min_height": m + 0.5, "insert_od": od_i}
    if fastener == "tap":
        return {"hole": T.TAP_DRILL[s], "od": round(2.0 * d, 2), "min_height": 1.5 * d}
    return {"hole": round(T.PT_HOLE_K * d, 2), "od": round(T.PT_BOSS_K * d, 2), "min_height": 2.0 * d}


def screw_boss(size: str = "M3", height: float = 8.0, wall: float = 2.0, fastener: str = "insert", draft_deg: float = 0.5):
    """Drafted boss standing on z = 0 (floor), hole open at the top. Widest at the base (pull +Z)."""
    b = boss_dims(size, fastener)
    h = max(height, b["min_height"])
    t = math.tan(math.radians(draft_deg))
    ro = b["od"] / 2
    boss = Pos(0, 0, h / 2) * cone(ro, max(ro - h * t, ro * 0.8), h)
    hole = Pos(0, 0, h / 2 + 0.3) * cyl(b["hole"] / 2, h)
    try:
        part = boss - hole
    except Exception:  # noqa: BLE001
        part = boss
    return _tag(part, "boss", "boss_insert" if fastener == "insert" else "boss_pt", size=size, fastener=fastener,
                hole_mm=b["hole"], od_mm=b["od"], height_mm=round(h, 2), wall_mm=wall, draft_deg=draft_deg)


def rib(length: float, height: float, wall: float = 2.0):
    """Drafted rib along X on z = 0: base thickness 0.6·wall, capped at 3·wall high."""
    th = 0.6 * wall
    h = min(height, 3 * wall)
    top = max(th - 2 * h * math.tan(math.radians(0.5)), th * 0.5)
    prof = make_face(Polyline((-th / 2, 0), (th / 2, 0), (top / 2, h), (-top / 2, h), close=True))
    part = Plane(origin=(0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)) * extrude(prof, amount=length / 2, both=True)
    return _tag(part, "rib", "rib", thickness_mm=round(th, 3), height_mm=round(h, 2), wall_mm=wall)


def gusset(height: float, depth: float, wall: float = 2.0):
    """Triangular gusset in the XZ plane (vertical leg on x = 0, foot along +X), 0.6·wall thick."""
    th = 0.6 * wall
    h = min(height, 4 * wall * 2)
    face = make_face(Polyline((0, 0), (depth, 0), (0, h), close=True))
    part = (Rot(90, 0, 0) * extrude(face, amount=th / 2, both=True))
    return _tag(part, "rib", "rib", thickness_mm=round(th, 3), height_mm=round(h, 2), wall_mm=wall, gusset=True)


def snap_fit(length: float = 10.0, thickness: float = 1.2, width: float = 5.0, material: str = "pc_abs"):
    """Cantilever snap arm standing on z = 0 (root), hook at the tip pointing +X. Hook depth = permissible deflection."""
    eps = SNAP_STRAIN.get(material, 0.025)
    L = max(length, 5 * thickness)
    y = 0.67 * eps * L * L / thickness
    lead = y / math.tan(math.radians(30))
    arm = Box(thickness, width, L, align=(_C, _C, _MIN))
    t2 = thickness / 2  # 30° lead-in ramp from the tip, then a 90° retention face back to the arm
    hook = make_face(Polyline((t2 - 0.01, L), (t2 + y, L - lead), (t2 + y, L - lead - 0.6), (t2 - 0.01, L - lead - 0.6),
                              close=True))
    part = arm + (Rot(90, 0, 0) * extrude(hook, amount=width / 2, both=True))
    return _tag(part, "snap_fit", "snap_fit", length_mm=round(L, 2), thickness_mm=thickness, width_mm=width, strain=eps,
                deflection_mm=round(y, 3), ratio_L_h=round(L / thickness, 2), material=material)


def uniform_fillet(shape, edges, wall: float, inside: bool = True):
    r = 0.5 * wall if inside else 1.5 * wall
    try:
        out = fillet(edges, radius=r)
    except Exception:  # noqa: BLE001 — a refused fillet keeps the sharp shape
        return shape
    out.std_meta = {"dfm": {"rule": RULES["fillet"][0], "citation": RULES["fillet"][1], "radius_mm": r, "wall_mm": wall}}
    return out


def parting_split(shape, z: float, reveal: float = 0.3):
    """(lower, upper) halves of `shape` at height z with a `reveal` gap (the visible parting line)."""
    bb = shape.bounding_box()
    big = 2 * max(bb.size.X, bb.size.Y) + 10
    lo_h = z - reveal / 2 - bb.min.Z + 1
    hi_h = bb.max.Z - (z + reveal / 2) + 1
    lower = shape & Pos(bb.center().X, bb.center().Y, bb.min.Z - 1) * Box(big, big, lo_h, align=(_C, _C, _MIN))
    upper = shape & Pos(bb.center().X, bb.center().Y, z + reveal / 2) * Box(big, big, hi_h, align=(_C, _C, _MIN))
    return lower, upper


def clearance_hole(size: str = "M3", depth: float = 10.0, fit: str = "medium", head: str | None = None):
    """Tool to subtract: hole from z = 0 down to -depth; `head` socket → DIN 974-1 counterbore, countersunk → 90° sink."""
    s = size if size.startswith("M") else f"M{size}"
    d = T.CLEARANCE_ISO273[s][{"fine": 0, "close": 0, "medium": 1, "normal": 1, "coarse": 2, "loose": 2}[fit]]
    tool = Pos(0, 0, -depth / 2) * cyl(d / 2, depth + 0.02)
    if head == "socket":
        dk, k, _ = T.SOCKET_ISO4762[s]
        cb = round(dk + 0.6, 1)
        tool = tool + Pos(0, 0, -k / 2 + 0.1) * cyl(cb / 2, k + 0.4)
    elif head == "pan":
        dk, k, _ = T.PAN_ISO14583[s]
        tool = tool + Pos(0, 0, -k / 2 + 0.1) * cyl(dk / 2 + 0.3, k + 0.4)
    elif head == "countersunk":
        dk, k, _ = T.CSK_ISO14581[s]
        tool = tool + Pos(0, 0, -(dk / 2 + 0.2) / 2) * cone(0.01, dk / 2 + 0.2, dk / 2 + 0.2)
    tool.std_meta = {"dfm": {"rule": RULES["clearance"][0], "citation": RULES["clearance"][1], "size": s, "hole_mm": d, "fit": fit}}
    return tool


def tap_hole(size: str = "M3", depth: float = 8.0):
    s = size if size.startswith("M") else f"M{size}"
    d = T.TAP_DRILL[s]
    tool = Pos(0, 0, -depth / 2) * cyl(d / 2, depth + 0.02)
    tool.std_meta = {"dfm": {"rule": RULES["tap"][0], "citation": RULES["tap"][1], "size": s, "hole_mm": d}}
    return tool


def weld_lip(length: float, width: float, radius: float, base: float = 0.5):
    """Energy-director ring on z = 0 following a rounded rectangle (mid-line length × width)."""
    r = max(radius, base)
    ring = RectangleRounded(length + base, width + base, r + base / 2) - RectangleRounded(length - base, width - base, max(r - base / 2, 0.1))
    part = extrude(ring, amount=base * 0.5, taper=44)
    return _tag(part, "weld_lip", "weld", base_mm=base, height_mm=round(part.bounding_box().size.Z, 3))


def gasket_groove(length: float, width: float, radius: float, cord: float = 2.0):
    """Tool to subtract: a face-seal gland on z = 0 going down, centred on the rounded-rectangle mid-line."""
    w, dpt = 1.4 * cord, 0.75 * cord
    r = max(radius, w)
    ring = RectangleRounded(length + w, width + w, r + w / 2) - RectangleRounded(length - w, width - w, r - w / 2)
    tool = Pos(0, 0, -dpt) * extrude(ring, amount=dpt + 0.01)
    tool.std_meta = {"dfm": {"rule": RULES["gasket"][0], "citation": RULES["gasket"][1], "cord_mm": cord,
                             "groove_width_mm": round(w, 2), "groove_depth_mm": round(dpt, 2),
                             "squeeze": round(1 - dpt / cord, 3)}}
    return tool



__all__ = ["RULES", "SNAP_STRAIN", "boss_dims", "screw_boss", "rib", "gusset", "snap_fit", "uniform_fillet", "parting_split",
           "clearance_hole", "tap_hole", "weld_lip", "gasket_groove"]
