"""Standard purchased parts as low-poly build123d solids (C1, CAD_DETAIL_LEVEL=pro).

Every constructor returns a `StdPart`: `.part` (build123d Part in its own frame), `.meta` (PartMeta extras: kind,
role, standard, size…) and `.bom` (one BOM line spec: part text, standard, unit price Estimate). `.at(x, y, z, rx,
ry, rz)` places a copy (geometry is cached per spec, placement is a location only) and tags it with `std_meta`, which
survives `Pos * shape` and is read back by `api.cad.families.export_parts` (node names + GLB extras) and
`api.cad.stdparts.bom` (BOM lines).

Frames: screws / pins / inserts are axial along Z. A screw's head underside sits on z = 0 (countersunk: head top flush
at z = 0) and the shank points to -Z (driven downward into a part); `ry=180` drives it upward from underneath. Inserts: top face at z = 0, body to -Z.
Threads are not modelled (cosmetic in a concept model, 100× the triangles); the thread length is in the metadata.

Imports only build123d + math (+ tables): this module also runs inside the codegen sandbox.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from build123d import Box, Polyline, Pos, RegularPolygon, Rot, extrude, make_face

from api.cad.stdparts import tables as T

_CACHE: dict[tuple, object] = {}
SIDES = 16  # hardware is drawn as 16-sided prisms: 22.5° facets are below glb's 30° crease, so they shade round


def cyl(r: float, h: float, sides: int = SIDES):
    """Low-poly Cylinder(r, h) (centred): ~60 triangles instead of ~400 at the viewer tessellation."""
    return Pos(0, 0, -h / 2) * extrude(RegularPolygon(r, sides), amount=h)


def cone(r1: float, r2: float, h: float, sides: int = SIDES):
    """Low-poly Cone(r1 bottom, r2 top, h) (centred)."""
    r2 = max(r2, 0.05)
    if abs(r1 - r2) < 1e-6:
        return cyl(r1, h, sides)
    deg = math.degrees(math.atan((r1 - r2) / h))
    return Pos(0, 0, -h / 2) * extrude(RegularPolygon(r1, sides), amount=h, taper=deg)


@dataclass
class StdPart:
    part: object
    meta: dict = field(default_factory=dict)
    bom: dict = field(default_factory=dict)

    def at(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, rx: float = 0.0, ry: float = 0.0, rz: float = 0.0):
        """A placed copy (location only, shared geometry) tagged with `std_meta` = {meta, bom}."""
        s = Pos(x, y, z) * (Rot(rx, ry, rz) * self.part)
        s.std_meta = {**self.meta, "bom": dict(self.bom)}
        return s

    def along(self, origin, direction=(0.0, 0.0, -1.0), x_dir=None):
        """A placed copy whose local -Z (screw shank / insert body) points along `direction` from `origin`."""
        s = frame(origin, direction, x_dir) * self.part
        s.std_meta = {**self.meta, "bom": dict(self.bom)}
        return s


def frame(origin, direction=(0.0, 0.0, -1.0), x_dir=None):
    """Plane whose +Z is -direction (so a part's -Z axis points along `direction`)."""
    from build123d import Plane, Vector

    z = Vector(*direction).normalized() * -1
    if x_dir is None:
        x_dir = (1, 0, 0) if abs(z.X) < 0.9 else (0, 1, 0)
        xv = Vector(*x_dir)
        xv = (xv - z * xv.dot(z)).normalized()
    else:
        xv = Vector(*x_dir)
    return Plane(origin=tuple(origin), x_dir=xv, z_dir=z)


def _cached(key: tuple, make):
    if key not in _CACHE:
        _CACHE[key] = make()
    return _CACHE[key]


def _size(size: str) -> str:
    s = str(size).upper().split("-")[0].split("X")[0]
    s = s if s.startswith("M") else f"M{s}"
    if s not in T.PITCH:
        raise ValueError(f"size {size!r}: supported {', '.join(T.PITCH)}")
    return s


def _bom(kind: str, text: str, standard: str, price: float, material: str) -> dict:
    return {"part": text, "standard": standard, "kind": kind, "unit_price_usd": round(price, 3), "price_label": "estimate",
            "price_source": "Catalogue order of magnitude at ~2,000 pcs (Estimate, not a quote)", "material": material,
            "category": "mechanical"}


def _drive(depth: float, width: float, drive: str):
    """Recess tool (hex socket / hexalobular approximated as a 6-point star / slot / cross) opening at z = 0 to -depth."""
    if drive == "slot":
        return Box(width * 2.2, width * 0.28, depth * 2)
    if drive.startswith("PH"):
        return Box(width * 1.2, width * 0.32, depth * 2) + Box(width * 0.32, width * 1.2, depth * 2)
    if drive.startswith("T"):
        a = extrude(RegularPolygon(width / 2, 3), amount=depth, both=True)
        return a + Rot(0, 0, 60) * a
    return extrude(RegularPolygon(width / math.sqrt(3), 6), amount=depth, both=True)  # hex key: across flats = width


# --------------------------------------------------------------------------- screws, nuts, washers


def screw(size: str = "M3", length: float = 8.0, head: str = "pan") -> StdPart:
    """ISO metric machine screw. head: pan (ISO 14583) · countersunk (ISO 14581, 90°) · socket (ISO 4762)."""
    s = _size(size)
    d = T.NOMINAL[s]
    head = {"csk": "countersunk", "flat": "countersunk", "cap": "socket", "shcs": "socket"}.get(head, head)
    if head == "socket":
        dk, k, key = T.SOCKET_ISO4762[s]
        std, drive, dname = "ISO 4762", "hex", f"{key:g} mm hex"
    elif head == "countersunk":
        dk, k, drive = T.CSK_ISO14581[s]
        std, dname = ("ISO 14581" if s != "M1.6" else "ISO 7046"), drive
    else:
        head = "pan"
        dk, k, drive = T.PAN_ISO14583[s]
        std, dname = ("ISO 14583" if s != "M1.6" else "ISO 1580"), drive

    def make():
        shank = Pos(0, 0, -length / 2) * cyl(d / 2, length)
        if head == "countersunk":  # ISO length includes the head; seated flush: head top at z = 0
            body = Pos(0, 0, -k / 2) * cone(d / 2, dk / 2, k) + Pos(0, 0, -k - (length - k) / 2) * cyl(d / 2, length - k)
            top = 0.0
        else:
            body = Pos(0, 0, k / 2) * cyl(dk / 2, k) + shank
            top = k
        recess = Pos(0, 0, top) * _drive(k * 0.6, (key if head == "socket" else dk * 0.45), drive)
        try:
            return body - recess
        except Exception:  # noqa: BLE001
            return body
    part = _cached(("screw", s, round(length, 2), head), make)
    meta = {"kind": "screw", "role": "fastener", "standard": std, "size": s, "length_mm": length, "head": head,
            "drive": dname, "thread": f"{s}×{T.PITCH[s]}", "material": "A2 stainless steel"}
    text = f"Screw {s} × {length:g} {head} head, {dname} ({std}), A2 stainless"
    return StdPart(part, meta, _bom("screw", text, std, T.PRICE["screw"][s], "A2 stainless steel"))


def pt_screw(d: float = 2.5, length: float = 8.0) -> StdPart:
    """Thread-forming screw for plastics (EJOT DELTA PT type), pan head ≈ ISO 14583 of the nearest size."""
    s = min(T.PAN_ISO14583, key=lambda k: abs(T.NOMINAL[k] - d))
    base = screw(s, length, "pan")
    meta = {**base.meta, "kind": "pt_screw", "standard": "EJOT DELTA PT (thread-forming, plastics)", "size": f"PT {d:g}"}
    text = f"Thread-forming screw DELTA PT {d:g} × {length:g} pan head (plastics), zinc-plated steel"
    return StdPart(base.part, meta, _bom("pt_screw", text, "EJOT DELTA PT", T.PRICE["pt_screw"], "zinc-plated steel"))


def hex_nut(size: str = "M3") -> StdPart:
    s = _size(size)
    m, sw = T.NUT_ISO4032[s]
    part = _cached(("nut", s), lambda: extrude(RegularPolygon(sw / math.sqrt(3), 6) - RegularPolygon(T.NOMINAL[s] / 2, SIDES), amount=m))
    meta = {"kind": "nut", "role": "fastener", "standard": "ISO 4032", "size": s, "height_mm": m, "across_flats_mm": sw,
            "material": "A2 stainless steel"}
    return StdPart(part, meta, _bom("nut", f"Hex nut {s} (ISO 4032), A2 stainless", "ISO 4032", T.PRICE["nut"][s], "A2 stainless steel"))


def washer(size: str = "M3") -> StdPart:
    s = _size(size)
    d1, d2, h = T.WASHER_ISO7089[s]
    part = _cached(("washer", s), lambda: extrude(RegularPolygon(d2 / 2, SIDES) - RegularPolygon(d1 / 2, SIDES), amount=h))
    meta = {"kind": "washer", "role": "fastener", "standard": "ISO 7089", "size": s, "d1": d1, "d2": d2, "h": h,
            "material": "A2 stainless steel"}
    return StdPart(part, meta, _bom("washer", f"Plain washer {s} (ISO 7089), A2 stainless", "ISO 7089", T.PRICE["washer"][s],
                                    "A2 stainless steel"))


def heat_set_insert(size: str = "M3") -> StdPart:
    """Brass heat-set insert, top flush at z = 0, body to -Z (knurl drawn as 2 steps, not 20 knurls)."""
    s = _size(size)
    if s not in T.INSERT_HEATSET:
        s = "M2"
    od, m, hole, pn = T.INSERT_HEATSET[s]

    def make():
        body = Pos(0, 0, -m / 4) * cyl(od / 2, m / 2) + Pos(0, 0, -3 * m / 4) * cyl(od / 2 - 0.25, m / 2)
        return body - Pos(0, 0, -m / 2) * cyl(T.NOMINAL[s] / 2, m + 1)
    part = _cached(("insert", s), make)
    meta = {"kind": "insert", "role": "fastener", "standard": f"McMaster-Carr {pn}" if pn else "heat-set insert (catalogue class)",
            "size": s, "od_mm": od, "length_mm": m, "hole_mm": hole, "material": "brass"}
    text = f"Heat-set threaded insert {s} × {m:g} (OD {od:g} mm), brass" + (f" — ref. McMaster-Carr {pn}" if pn else "")
    return StdPart(part, meta, _bom("insert", text, meta["standard"], T.PRICE["insert"][s], "brass"))


# --------------------------------------------------------------------------- pins, magnets, bearings, gears


def dowel_pin(d: float = 3.0, length: float = 12.0) -> StdPart:
    d = min(T.DOWEL_ISO2338, key=lambda v: abs(v - d))
    c = min(0.3, d * 0.12)

    def make():
        body = cyl(d / 2, length - 2 * c) + Pos(0, 0, (length - c) / 2) * cone(d / 2, d / 2 - c, c) \
            + Pos(0, 0, -(length - c) / 2) * cone(d / 2 - c, d / 2, c)
        return body
    part = _cached(("dowel", d, length), make)
    meta = {"kind": "dowel_pin", "role": "fastener", "standard": "ISO 2338 m6", "size": f"Ø{d:g} × {length:g}",
            "material": "hardened steel"}
    return StdPart(part, meta, _bom("dowel_pin", f"Dowel pin Ø{d:g} m6 × {length:g} (ISO 2338), hardened steel", "ISO 2338",
                                    T.PRICE["dowel_pin"], "hardened steel"))


def wood_dowel(d: float = 8.0, length: float | None = None) -> StdPart:
    d = min(T.WOOD_DOWEL_DIN68150, key=lambda v: abs(v - d))
    length = length or T.WOOD_DOWEL_DIN68150[d]
    part = _cached(("wdowel", d, length), lambda: cyl(d / 2, length))
    meta = {"kind": "wood_dowel", "role": "fastener", "standard": "DIN 68150", "size": f"Ø{d:g} × {length:g}",
            "material": "fluted beech"}
    return StdPart(part, meta, _bom("wood_dowel", f"Fluted beech dowel Ø{d:g} × {length:g} (DIN 68150)", "DIN 68150",
                                    T.PRICE["wood_dowel"], "beech"))


def wood_screw(d: float = 4.0, length: float = 30.0) -> StdPart:
    """Chipboard / wood screw, countersunk, pozidriv (ISO 7046-type head on a wood thread)."""
    dk, k = 2 * d, 0.55 * d

    def make():
        return Pos(0, 0, -k / 2) * cone(d / 2, dk / 2, k) + Pos(0, 0, -k - (length - k) / 2) * cone(0.5, d / 2, length - k)
    part = _cached(("wscrew", d, length), lambda: Pos(0, 0, k) * make())
    meta = {"kind": "wood_screw", "role": "fastener", "standard": "Chipboard screw (EN 14592 class)", "size": f"{d:g} × {length:g}",
            "material": "zinc-plated steel"}
    return StdPart(part, meta, _bom("wood_screw", f"Wood screw {d:g} × {length:g} countersunk PZ2, zinc-plated", "EN 14592",
                                    T.PRICE["wood_screw"], "zinc-plated steel"))


def cam_lock() -> StdPart:
    """Minifix-type cam (Ø15 housing) + connecting bolt; the cam axis is Z (face at z = 0), the bolt along +X."""
    c = T.CAM_MINIFIX15

    def make():
        cam = Pos(0, 0, -c["cam_depth"] / 2) * cyl(c["cam_d"] / 2, c["cam_depth"])
        slot = Pos(0, 0, -0.5) * Box(c["cam_d"] * 0.7, 1.4, 1.2)
        bolt = Pos(c["edge"] / 2, 0, -c["cam_depth"] / 2) * (Rot(0, 90, 0) * cyl(c["bolt_d"] / 2, c["edge"]))
        return (cam - slot) + bolt
    part = _cached(("cam",), make)
    meta = {"kind": "cam_lock", "role": "fastener", "standard": "Häfele Minifix 15 (catalogue)", "size": "Ø15 cam + bolt",
            "material": "zinc die-cast + steel bolt"}
    return StdPart(part, meta, _bom("cam_lock", "Cam connector Minifix 15 + connecting bolt (flat-pack joinery)",
                                    "Häfele Minifix 15", T.PRICE["cam_lock"], "zinc die-cast"))


def magnet(d: float = 6.0, h: float = 2.0) -> StdPart:
    d, h = min(T.MAGNET_DISC, key=lambda v: abs(v[0] - d) + abs(v[1] - h))
    part = _cached(("magnet", d, h), lambda: Pos(0, 0, -h / 2) * cyl(d / 2, h))
    meta = {"kind": "magnet", "role": "fastener", "standard": "NdFeB N42 disc, NiCuNi (catalogue)", "size": f"Ø{d:g} × {h:g}",
            "material": "NdFeB N42"}
    return StdPart(part, meta, _bom("magnet", f"NdFeB disc magnet Ø{d:g} × {h:g} N42, NiCuNi plated", "catalogue",
                                    T.PRICE["magnet"], "NdFeB"))


def bearing(designation: str = "608") -> StdPart:
    """ISO 15 deep-groove ball bearing (2Z shields drawn as the side faces): axis Z, centred on the origin."""
    b = str(designation).upper().replace("-2Z", "").replace("ZZ", "").replace("2RS", "")
    if b not in T.BEARING_ISO15:
        raise ValueError(f"bearing {designation!r}: supported {', '.join(T.BEARING_ISO15)}")
    d, D, B = T.BEARING_ISO15[b]

    def make():
        ring = cyl(D / 2, B) - cyl(d / 2, B + 1)
        groove = cyl((D + d) / 4 + (D - d) * 0.12, 0.5) - cyl((D + d) / 4 - (D - d) * 0.12, 1)
        try:  # shield seam on both faces (reads as a bearing, costs a few faces)
            return ring - Pos(0, 0, B / 2) * groove - Pos(0, 0, -B / 2) * groove
        except Exception:  # noqa: BLE001
            return ring
    part = _cached(("bearing", b), make)
    meta = {"kind": "bearing", "role": "component", "standard": "ISO 15", "size": f"{b}-2Z ({d:g}×{D:g}×{B:g})",
            "bore_mm": d, "od_mm": D, "width_mm": B, "material": "chrome steel 52100"}
    return StdPart(part, meta, _bom("bearing", f"Deep-groove ball bearing {b}-2Z {d:g}×{D:g}×{B:g} (ISO 15)", "ISO 15",
                                    T.PRICE["bearing"][b], "52100 steel"))


def involute_points(module: float, teeth: int, pressure_deg: float = 20.0, per_flank: int = 4) -> list[tuple[float, float]]:
    """Closed outline of a standard spur gear (ISO 53 basic rack: addendum 1·m, dedendum 1.25·m)."""
    z = max(6, int(teeth))
    rp = module * z / 2
    rb = rp * math.cos(math.radians(pressure_deg))
    ra = rp + module
    rf = max(rp - 1.25 * module, 0.5)
    inv = lambda a: math.tan(a) - a  # noqa: E731
    ap = math.acos(rb / rp)
    half = math.pi / (2 * z) + inv(ap)  # half tooth angle at the base circle
    pts = []
    for i in range(z):
        c = 2 * math.pi * i / z
        flank = []
        for j in range(per_flank + 1):
            r = max(rb, rf) + (ra - max(rb, rf)) * j / per_flank
            a = math.acos(min(1.0, rb / r))
            flank.append((r, half - inv(a)))
        left = [(r, c - t) for r, t in flank]
        right = [(r, c + t) for r, t in reversed(flank)]
        pts.append((rf, c - half - 0.25 * math.pi / z))
        pts += left + right
        pts.append((rf, c + half + 0.25 * math.pi / z))
    return [(r * math.cos(a), r * math.sin(a)) for r, a in pts]


def spur_gear(module: float = 1.0, teeth: int = 20, thickness: float = 5.0, bore: float = 3.0) -> StdPart:
    def make():
        body = extrude(make_face(Polyline(*involute_points(module, teeth), close=True)), amount=thickness)
        return Pos(0, 0, -thickness / 2) * (body - cyl(bore / 2, thickness * 3))
    part = _cached(("gear", module, int(teeth), thickness, bore), make)
    meta = {"kind": "gear", "role": "component", "standard": "ISO 53 profile, 20° pressure angle",
            "size": f"m{module:g} z{int(teeth)}", "pitch_d_mm": round(module * teeth, 2), "material": "POM (acetal)"}
    return StdPart(part, meta, _bom("gear", f"Spur gear m{module:g} z{int(teeth)} × {thickness:g}, POM", "ISO 53",
                                    T.PRICE["gear"], "POM"))


def tripod_insert() -> StdPart:
    t = T.TRIPOD_ISO1222

    def make():
        return Pos(0, 0, -t["insert_len"] / 2) * (cyl(t["insert_od"] / 2, t["insert_len"]) - cyl(t["d"] / 2, t["insert_len"] + 1))
    part = _cached(("tripod",), make)
    meta = {"kind": "tripod_insert", "role": "fastener", "standard": "ISO 1222 (1/4\"-20 UNC)", "size": "1/4\"-20",
            "material": "brass"}
    return StdPart(part, meta, _bom("tripod_insert", "Tripod socket insert 1/4\"-20 UNC (ISO 1222), brass", "ISO 1222",
                                    T.PRICE["tripod_insert"], "brass"))


def fin_box() -> StdPart:
    """Single-tab fin box, top (open) face at z = 0, body to -Z, long axis X."""
    f = T.FIN_BOX
    part = _cached(("finbox",), lambda: Pos(0, 0, -f["depth"] / 2) * (
        Box(f["length"], f["width"], f["depth"]) - Pos(0, 0, 2) * Box(f["length"] - 8, 7.2, f["depth"])))
    meta = {"kind": "fin_box", "role": "fastener", "standard": "Futures-type single-tab box (catalogue)",
            "size": f"{f['length']:g} × {f['width']:g}", "material": "glass-filled nylon"}
    return StdPart(part, meta, _bom("fin_box", "Fin box, single tab (Futures-type), glass-filled nylon", "catalogue",
                                    T.PRICE["fin_box"], "PA-GF"))


def leash_plug() -> StdPart:
    lp = T.LEASH_PLUG

    def make():
        cup = Pos(0, 0, -lp["depth"] / 2) * (cyl(lp["cup_d"] / 2, lp["depth"]) - Pos(0, 0, 1.5) * cyl(lp["cup_d"] / 2 - 1.5, lp["depth"]))
        flange = Pos(0, 0, -0.5) * (cyl(lp["flange_d"] / 2, 1.0) - cyl(lp["cup_d"] / 2 - 1.5, 2))
        bar = Pos(0, 0, -5) * (Rot(90, 0, 0) * cyl(lp["bar_d"] / 2, lp["cup_d"] - 2))
        return cup + flange + bar
    part = _cached(("leash",), make)
    meta = {"kind": "leash_plug", "role": "fastener", "standard": "Leash cup (catalogue)", "size": f"Ø{lp['cup_d']:g}",
            "material": "ABS + stainless bar"}
    return StdPart(part, meta, _bom("leash_plug", "Leash plug cup with bar, ABS", "catalogue", T.PRICE["leash_plug"], "ABS"))


def gasket(length: float, width: float, radius: float, cord: float = 2.0) -> StdPart:
    """Cut-to-length / moulded perimeter gasket of square section `cord`, bottom at z = 0."""
    from build123d import RectangleRounded

    r = max(radius, cord + 0.2)
    part = _cached(("gasket", round(length, 1), round(width, 1), round(r, 1), cord), lambda: extrude(
        RectangleRounded(length, width, r) - RectangleRounded(length - 2 * cord, width - 2 * cord, r - cord), amount=cord))
    meta = {"kind": "gasket", "role": "other", "standard": "Parker O-Ring Handbook ORD 5700 (face seal, 25 % squeeze)",
            "size": f"{length:.0f} × {width:.0f}, cord {cord:g}", "material": "EPDM 70 Shore A"}
    return StdPart(part, meta, _bom("gasket", f"Perimeter gasket EPDM 70A, cord {cord:g} mm, {length:.0f} × {width:.0f}",
                                    "Parker ORD 5700", T.PRICE["gasket"], "EPDM"))


__all__ = ["StdPart", "frame", "screw", "pt_screw", "hex_nut", "washer", "heat_set_insert", "dowel_pin", "wood_dowel", "wood_screw",
           "cam_lock", "magnet", "bearing", "spur_gear", "involute_points", "tripod_insert", "fin_box", "leash_plug", "gasket"]
