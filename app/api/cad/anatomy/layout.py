"""Illustrative internal layout (W29): exterior parts + BOM → internal bodies, layers, storyboard. Deterministic.

    plan(facts) -> Plan        # facts: Facts (exterior parts, BOM lines with packages / prices, engineering values)

Rules per family (all in mm, GLB axes, +Y up; the product bbox is the exterior GLB's):
- shell products: cavity = measured housing bbox minus the wall; PCB (FR-4, 1.0-1.6 mm, rounded corners) sized to
  the cavity footprint; every electronic BOM line a body with its package dimensions (api.cad.anatomy.packages) packed
  on the board top (rows; quantities > 1 → rows of parts; passives as one 0402 cluster); battery sized from its
  capacity and chemistry; connectors at the opening edge, antenna at the opposite edge, switches under the buttons.
- wearable: PPG + temperature sensors under the board, over the optical window; battery on top; strap drops away.
- drone: flight controller + ESC stack in the body, cables to the four motors, cells inside the battery pack.
- stick vacuum: BLDC motor + impeller in the motor pod, 18650 cells in the battery pack, control PCB and trigger
  switch in the grip; housings open sideways (+Z).
- solid products (board, furniture): construction layers, no PCB.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np

from api.cad.anatomy import mesh as M
from api.cad.anatomy.packages import LIPO_WH_PER_L, Body, body_for

# --------------------------------------------------------------------------- materials


def _mat(role: str, name: str, hex_: str, metallic=0.0, rough=0.5, ext=None, emissive=None) -> dict:
    from api.cad.look import hex_to_linear

    return {"name": name, "role": role, "baseColorFactor": [*hex_to_linear(hex_), 1.0], "metallicFactor": metallic,
            "roughnessFactor": rough, "emissiveFactor": emissive or [0.0, 0.0, 0.0], "alphaMode": "OPAQUE", "doubleSided": True,
            "extensions": ext or {}}


CLEAR = {"KHR_materials_clearcoat": {"clearcoatFactor": 0.6, "clearcoatRoughnessFactor": 0.15}}
MATS = {
    "pcb_green": _mat("pcb", "FR-4, green solder mask", "#1E5B3A", 0.0, 0.42, CLEAR),
    "pcb_black": _mat("pcb", "FR-4, matte black solder mask", "#17191C", 0.0, 0.5, CLEAR),
    "chip": _mat("chip", "IC package (epoxy mould)", "#1B1C1E", 0.0, 0.55),
    "sensor": _mat("sensor", "Optical sensor module", "#2A2C30", 0.0, 0.3, {"KHR_materials_clearcoat": {"clearcoatFactor": 1.0, "clearcoatRoughnessFactor": 0.03}}),
    "passive": _mat("passive", "Ceramic passives", "#9C8B6E", 0.0, 0.5),
    "module": _mat("module", "Module (shield can)", "#B9BDC2", 1.0, 0.32),
    "battery": _mat("battery", "Li-po pouch (aluminium laminate)", "#C3C7CC", 0.7, 0.3),
    "cell": _mat("cell", "18650 Li-ion cell (PVC wrap)", "#2E5DA8", 0.0, 0.35, CLEAR),
    "motor": _mat("motor", "Motor (steel can, copper windings)", "#B87333", 1.0, 0.38),
    "impeller": _mat("impeller", "Impeller (glass-filled PA)", "#3A3D42", 0.0, 0.4),
    "connector": _mat("connector", "Connector (stainless shell)", "#C9CBCE", 1.0, 0.25),
    "antenna": _mat("antenna", "Antenna (copper on flex)", "#C58B3F", 1.0, 0.3),
    "cable_red": _mat("cable", "Cable (silicone, red)", "#B3302A", 0.0, 0.6),
    "cable_black": _mat("cable", "Cable (silicone, black)", "#1D1D1F", 0.0, 0.6),
    "coil": _mat("coil", "Solenoid coil (copper, varnished)", "#B06A2C", 1.0, 0.35),
    "lens": _mat("lens", "Lens module (glass + barrel)", "#101215", 0.0, 0.08,
                 {"KHR_materials_clearcoat": {"clearcoatFactor": 1.0, "clearcoatRoughnessFactor": 0.02}, "KHR_materials_ior": {"ior": 1.52}}),
    "switch": _mat("switch", "Switch (steel + POM)", "#8D9095", 1.0, 0.35),
    "display": _mat("display", "Display panel (OLED)", "#0A0B0D", 0.0, 0.12, CLEAR),
    "foam": _mat("foam", "PU foam core", "#F2EEE3", 0.0, 0.92),
    "stringer": _mat("wood", "Wood stringer (basswood)", "#C9A36B", 0.0, 0.6),
    "laminate": _mat("laminate", "Fibreglass + resin laminate", "#DDEBE4", 0.0, 0.08,
                     {"KHR_materials_transmission": {"transmissionFactor": 0.6}, "KHR_materials_ior": {"ior": 1.55},
                      "KHR_materials_clearcoat": {"clearcoatFactor": 1.0, "clearcoatRoughnessFactor": 0.03}}),
    "finbox": _mat("finbox", "Fin box (glass-filled nylon)", "#1F2124", 0.0, 0.45),
    "pad": _mat("pad", "EVA traction pad", "#222325", 0.0, 0.85, {"KHR_materials_sheen": {"sheenColorFactor": [0.2, 0.2, 0.2], "sheenRoughnessFactor": 0.8}}),
    "plug": _mat("plug", "Leash plug (ABS + steel bar)", "#6B6F75", 0.3, 0.4),
    "fastener": _mat("fastener", "Steel fastener (zinc plated)", "#B8BBBF", 1.0, 0.3),
    "filter": _mat("filter", "HEPA filter media", "#E8E4D8", 0.0, 0.95),
    "solar": _mat("cell", "Monocrystalline PV cell", "#0E1A33", 0.3, 0.12, CLEAR),
}

LABEL_NOTE = "Illustrative internal layout — not a routed PCB"


# --------------------------------------------------------------------------- inputs


@dataclass
class Line:
    id: str
    part: str
    qty: float
    category: str
    lcsc_pn: str | None
    package: str | None
    price: dict | None  # LabeledValue dict
    body: Body | None


@dataclass
class Facts:
    family: str  # wearable_band | drone | stick_vacuum | home_robot | camera | smartphone | irrigation | lamp | tracker | board | furniture | generic …
    product: str
    parts: list[dict]  # exterior PartMeta (mm, GLB axes)
    lines: list[Line]
    dims: tuple[float, float, float] | None = None  # measured overall L × W × H (spec)
    wall: float = 1.8
    battery_life: dict | None = None
    average_current: dict | None = None
    flight_time: dict | None = None
    unit_cost: dict | None = None  # {value, quantity, label}
    weight: dict | None = None
    finish: str = ""
    material: str = ""
    total_mass: dict | None = None  # W29b: whole product (all parts), LabeledValue dict


@dataclass
class Plan:
    items: list[dict] = field(default_factory=list)
    layer_of: dict[str, str] = field(default_factory=dict)  # exterior part id → layer id
    layers: list[dict] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)
    kind: str = "electronics"
    replace: dict[str, dict] = field(default_factory=dict)


# --------------------------------------------------------------------------- geometry helpers


def _bb(p: dict) -> tuple[np.ndarray, np.ndarray]:
    c, s = np.array(p["centroid_mm"], float), np.array(p["measured_bbox_mm"], float)
    return c - s / 2, c + s / 2


def union_bb(parts: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    los, his = zip(*[_bb(p) for p in parts]) if parts else ((np.zeros(3),), (np.ones(3),))
    return np.min(los, axis=0), np.max(his, axis=0)


def _role(parts, *roles):
    return [p for p in parts if p["role"] in roles]


def _named(parts, rx: str):
    r = re.compile(rx, re.I)
    return [p for p in parts if r.search(p["name"]) or r.search(p["part_id"])]


def _fmt_price(pr: dict | None) -> str:
    if not pr:
        return ""
    lab = {"sourced": "Sourced", "estimate": "Estimate", "measured": "Measured", "fictional": "Fictional"}.get(pr.get("label"), "Estimate")
    return f"${pr['value']:.2f} ({lab})"


def _lv(v: dict | None, nd: int = 0) -> str:
    if not v:
        return ""
    lab = {"sourced": "Sourced", "estimate": "Estimate", "measured": "Measured"}.get(v.get("label"), "Estimate")
    val = v["value"]
    unit = v.get("unit", "")
    if unit == "h" and val >= 48:
        return f"{val / 24:.1f} days ({lab})"
    if unit == "h" and val < 1:
        return f"{val * 60:.0f} min ({lab})"
    return f"{val:.{nd}f} {unit} ({lab})".replace(" .", ".")


class Builder:
    def __init__(self, facts: Facts, pcb_colour: str = "pcb_green"):
        self.f = facts
        self.items: list[dict] = []
        self.pcb_mat = pcb_colour
        self._ids: dict[str, int] = {}

    def pid(self, base: str) -> str:
        from api.cad.parts import slug

        s = slug(base)
        self._ids[s] = self._ids.get(s, 0) + 1
        return s if self._ids[s] == 1 else f"{s}_{self._ids[s]}"

    def add(self, name: str, role: str, layer: str, mat: str, mesh_, line: Line | None = None, source: str = "",
            part_id: str | None = None) -> dict:
        m = MATS[mat]
        ex = {"part_id": part_id or self.pid(name), "name": name, "role": role, "layer_id": layer, "material": m["name"],
              "finish": None, "colour_hex": _hex_of(m), "measured_bbox_mm": [0, 0, 0], "centroid_mm": [0, 0, 0], "label": "estimate",
              "bom_item_id": line.id if line else None, "lcsc_pn": line.lcsc_pn if line else None,
              "package": (line.package or (line.body.package if line.body else None)) if line else None,
              "unit_price": line.price if line else None, "editable": [], "colour_editable": False, "material_options": []}
        it = {"extras": ex, "material": m, "mesh": mesh_, "source": source}
        self.items.append(it)
        return it

    # -- board + components -------------------------------------------------

    def board(self, lo, hi, y: float, t: float = 1.2, name: str = "Main PCB", layer: str = "pcb", k: float = 0.9) -> dict:
        size = hi - lo
        c = (lo + hi) / 2
        L, W = size[0] * k, size[2] * k
        r = min(3.0, min(L, W) * 0.15)
        line = self.line(r"\bpcb\b|mainboard|main pcb|pcb assembly|controller pcb|control pcb") if "PCB" in name else None
        it = self.add(name, "pcb", layer, self.pcb_mat, M.rounded_slab((L, t, W), (c[0], y + t / 2, c[2]), r), line,
                      f"FR-4 {t:.1f} mm, {L:.0f} × {W:.0f} mm = cavity footprint × {k:.2f} (estimate)")
        it["board"] = {"lo": np.array([c[0] - L / 2, y, c[2] - W / 2]), "hi": np.array([c[0] + L / 2, y + t, c[2] + W / 2])}
        return it

    def line(self, rx: str) -> Line | None:
        r = re.compile(rx, re.I)
        return next((ln for ln in self.f.lines if r.search(ln.part)), None)

    def populate(self, board: dict, bodies: list[tuple[Line, Body]], layer: str = "pcb", bottom: bool = False) -> list[dict]:
        """Pack bodies on the board surface in rows (largest first); returns the items placed."""
        blo, bhi = board["board"]["lo"], board["board"]["hi"]
        y0 = blo[1] if bottom else bhi[1]
        sgn = -1 if bottom else 1
        x, z, row = blo[0] + 1.0, blo[2] + 1.0, 0.0
        out = []
        entries = []
        for ln, b in bodies:
            n = 1 if b.kind == "passive" else min(b.qty, 12)
            entries += [(ln, b, i, n) for i in range(n)]
        entries.sort(key=lambda e: -(e[1].size[0] * e[1].size[1]))
        for ln, b, i, n in entries:
            if b.kind == "passive":
                out.append(self._cluster(ln, b, board, layer, bottom, (x, z)))
                cl = out[-1]["cluster"]
                x += cl[0] + 0.8
                row = max(row, cl[1])
                continue
            L, W, H = b.size
            if x + L > bhi[0] - 0.8 and x > blo[0] + 1.0:
                x, z = blo[0] + 1.0, z + row + 0.8
                row = 0.0
            cx, cz = x + L / 2, z + W / 2
            if z + W > bhi[2] - 0.5:  # board full: centre overflow parts (still inside the footprint)
                cz = min(max(cz, blo[2] + W / 2), bhi[2] - W / 2)
            name = _short(ln.part) + (f" {i + 1}" if n > 1 else "")
            mat = {"sensor": "sensor", "connector": "connector", "antenna": "antenna", "switch": "switch", "module": "module",
                   "lens": "lens", "board": "module", "coil": "coil"}.get(b.kind, "chip")
            role = {"connector": "connector", "antenna": "antenna"}.get(b.kind, "component")
            out.append(self.add(name, role, layer, mat, M.box((L, H, W), (cx, y0 + sgn * H / 2, cz)), ln, b.source))
            x += L + 0.8
            row = max(row, W)
        return out

    def _cluster(self, ln: Line, b: Body, board: dict, layer: str, bottom: bool, at) -> dict:
        n = min(b.qty, 24)
        cols = 6
        L, W, H = b.size
        blo, bhi = board["board"]["lo"], board["board"]["hi"]
        y0 = blo[1] - H / 2 if bottom else bhi[1] + H / 2
        x0, z0 = at
        meshes = [M.box((L, H, W), (x0 + (i % cols) * (L + 0.5) + L / 2, y0, z0 + (i // cols) * (W + 0.6) + W / 2)) for i in range(n)]
        it = self.add("Passives cluster", "component", layer, "passive", M.merge(*meshes), ln, b.source + f", {n} shown")
        it["cluster"] = (cols * (L + 0.5), math.ceil(n / cols) * (W + 0.6))
        return it

    def pouch(self, ln: Line, lo, hi, y: float, layer: str = "battery", max_h: float | None = None) -> dict:
        b = ln.body
        vol = b.extras["volume_cm3"] * 1000  # mm³
        size = hi - lo
        c = (lo + hi) / 2
        L, W = size[0] * 0.82, size[2] * 0.82
        h = vol / (L * W)
        tight = ""
        if max_h is not None and h > max_h:
            h = max(max_h, 1.2)
            k = math.sqrt(vol / (h * L * W))
            L, W = min(L * k, size[0] * 0.95), min(W * k, size[2] * 0.95)
            if L * W * h < vol * 0.97:
                tight = f"; tight: the cell needs {vol / 1000:.2f} cm³, the cavity above the board leaves {L * W * h / 1000:.2f} cm³"
        if h > size[1] * 0.6 and max_h is None:
            h = size[1] * 0.6
        src = f"{b.source} → {L:.0f} × {W:.0f} × {h:.1f} mm pouch{tight}"
        return self.add(f"Li-po battery {_cap(ln)}", "battery", layer, "battery", M.rounded_slab((L, h, W), (c[0], y + h / 2, c[2]), 1.5),
                        ln, src)

    def cells(self, ln: Line, lo, hi, layer: str = "battery") -> list[dict]:
        """18650 cells packed along the longest axis of the battery-pack bbox."""
        b = ln.body
        n = int(b.extras.get("cells") or b.qty or 1)
        size = hi - lo
        c = (lo + hi) / 2
        ax = int(np.argmax(size))
        others = [i for i in range(3) if i != ax]
        L = min(65.0, size[ax] * 0.95)
        r = min(9.0, min(size[others[0]], size[others[1]]) / 4.4)
        per_row = max(1, int(size[others[0]] // (2 * r + 0.5)))
        out = []
        for i in range(n):
            row, col = divmod(i, per_row)
            off = np.zeros(3)
            off[others[0]] = (col - (min(per_row, n) - 1) / 2) * (2 * r + 0.4)
            off[others[1]] = (row - (math.ceil(n / per_row) - 1) / 2) * (2 * r + 0.4)
            a, bb = c + off, c + off
            a = a.copy()
            bb = bb.copy()
            a[ax] -= L / 2
            bb[ax] += L / 2
            out.append(self.add(f"18650 cell {i + 1}", "battery", layer, "cell", M.cylinder(a, bb, r), ln, b.source))
        return out

    def cable(self, a, b, name: str, layer: str, red: bool = False, r: float = 0.6) -> dict:
        return self.add(name, "cable", layer, "cable_red" if red else "cable_black", M.cylinder(a, b, r, seg=10), None,
                        "cable run between modules (illustrative)")


def _hex_of(m: dict) -> str:
    from api.cad.glb import linear_to_hex

    return linear_to_hex(m["baseColorFactor"])


def _short(part: str) -> str:
    p = re.sub(r"\s*\(.*?\)", "", part)
    p = re.split(r",\s| with | and ", p)[0]
    m = re.search(r"\b([A-Z]{2,}[0-9][A-Z0-9-]{2,})\b", part)
    if m and m.group(1).rstrip("-") not in p:
        p = f"{m.group(1).rstrip('-')} {p}"
    return p.strip()[:48]


def _cap(ln: Line) -> str:
    b = ln.body
    mah = (b.extras or {}).get("mah") if b else None
    return f"{mah:.0f} mAh" if mah else ""


def _lines(facts: Facts, rx: str) -> list[Line]:
    r = re.compile(rx, re.I)
    return [ln for ln in facts.lines if r.search(ln.part) and ln.category != "packaging"]


# --------------------------------------------------------------------------- cameras + layers


def camera(lo, hi, view=(1.0, 0.62, 1.35), fov: float = 30.0, zoom: float = 1.0) -> dict:
    c = (np.array(lo) + np.array(hi)) / 2
    R = max(float(np.linalg.norm(np.array(hi) - np.array(lo))) / 2, 8.0)
    d = np.array(view, float)
    d /= np.linalg.norm(d)
    dist = R / math.sin(math.radians(fov) / 2) * 1.08 / zoom
    return {"position_mm": [round(float(v), 1) for v in c + d * dist], "target_mm": [round(float(v), 1) for v in c], "fov_deg": fov}


def layer(id_: str, name: str, order: int, parts: list[str], vec, dist: float, caption: str) -> dict:
    v = np.array(vec, float)
    v = v / (np.linalg.norm(v) or 1)
    return {"id": id_, "name": name, "order": order, "parts": parts, "explode_vector": [round(float(x), 4) for x in v],
            "explode_distance_mm": round(float(dist), 1), "caption": caption}


def exploded_bb(parts_by_id: dict[str, dict], layers: list[dict], exploded: list[str]):
    los, his = [], []
    off = {}
    for L in layers:
        if L["id"] in exploded:
            for pid in L["parts"]:
                off[pid] = np.array(L["explode_vector"]) * L["explode_distance_mm"]
    for pid, p in parts_by_id.items():
        lo, hi = _bb(p)
        o = off.get(pid, 0)
        los.append(lo + o)
        his.append(hi + o)
    return np.min(los, axis=0), np.max(his, axis=0)


def step(i: int, title: str, caption: str, cam: dict, exploded: list[str], focus: list[str]) -> dict:
    return {"id": f"s{i}", "title": title, "kicker": f"{i:02d} · {title}", "caption": caption, "camera": cam,
            "layers_exploded": exploded, "focus_parts": focus}


def _metas(items: list[dict]) -> dict[str, dict]:
    out = {}
    for it in items:
        pos = it["mesh"][0]
        lo, hi = pos.min(axis=0), pos.max(axis=0)
        out[it["extras"]["part_id"]] = {"centroid_mm": list((lo + hi) / 2), "measured_bbox_mm": list(hi - lo)}
    return out


# --------------------------------------------------------------------------- shared shell-product layout


def split_shells(parts: list[dict], split_y: float) -> dict[str, str]:
    """Exterior parts → shell_top / shell_bottom layer by the side of the split plane their centroid is on."""
    out = {}
    for p in parts:
        if p["role"] == "strap":
            out[p["part_id"]] = "strap"
        elif p["role"] == "shell_bottom" or (p["role"] != "shell_top" and p["centroid_mm"][1] < split_y):
            out[p["part_id"]] = "shell_bottom"
        else:
            out[p["part_id"]] = "shell_top"
    return out


def housing(parts: list[dict]) -> list[dict]:
    h = _role(parts, "shell_top", "shell_bottom")
    if not h:
        h = sorted(parts, key=lambda p: -np.prod(p["measured_bbox_mm"]))[:1]
    big = max(np.prod(p["measured_bbox_mm"]) for p in h)
    return [p for p in h if np.prod(p["measured_bbox_mm"]) > big * 0.05]


def cavity_of(parts: list[dict], wall: float):
    lo, hi = union_bb(parts)
    return lo + wall, hi - wall


def electronic_bodies(facts: Facts, exclude: str | None = None) -> list[tuple[Line, Body]]:
    out = []
    for ln in facts.lines:
        if ln.body is None or ln.body.kind in ("battery", "board") or ln.category != "electronic":
            continue
        if exclude and re.search(exclude, ln.part, re.I):
            continue
        if ln.body.size[0] <= 0:  # size given by the cavity (display, ejector) → family rule
            continue
        out.append((ln, ln.body))
    return out


def fit_bodies(bodies: list[tuple[Line, Body]], lo, hi, max_h: float) -> list[tuple[Line, Body]]:
    """Scale down module bodies that cannot fit the board (a stated estimate anyway)."""
    size = hi - lo
    out = []
    for ln, b in bodies:
        L, W, H = b.size
        k = min(1.0, size[0] * 0.45 / max(L, 0.1), size[2] * 0.45 / max(W, 0.1))
        h = min(H, max_h)
        if k < 1 or h < H:
            b = Body(b.kind, (L * k, W * k, h), b.package, b.source + (" (scaled to fit the cavity)" if k < 1 or h < H else ""), b.qty,
                     b.shape, b.extras)
        out.append((ln, b))
    return out


def shell_product(facts: Facts, pcb_mat: str = "pcb_green", sensors_down: bool = False, battery_on_top: bool = True):
    """Generic shell product: PCB on the cavity floor, components on top, battery above them (or beside)."""
    B = Builder(facts, pcb_mat)
    h = housing(facts.parts)
    lo, hi = cavity_of(h, facts.wall)
    size = hi - lo
    t = 1.0 if size[1] < 12 else 1.6
    sensors = [(ln, b) for ln, b in electronic_bodies(facts) if sensors_down and b.kind == "sensor" or
               (sensors_down and re.search(r"ppg|optical|heart|temperature|spo2", ln.part, re.I))]
    others = [(ln, b) for ln, b in electronic_bodies(facts) if (ln, b) not in sensors]
    y_pcb = lo[1] + (max((b.size[2] for _, b in sensors), default=0.0) + 0.2 if sensors_down else 0.4)
    board = B.board(lo, hi, y_pcb, t)
    free_h = max(hi[1] - (y_pcb + t) - 0.4, 0.6)
    placed = B.populate(board, fit_bodies(others, lo, hi, free_h * 0.45), "pcb")
    down = B.populate(board, sensors, "sensors", bottom=True) if sensors else []
    for it in down:
        it["extras"]["layer_id"] = "sensors"
    top_y = max((float(it["mesh"][0][:, 1].max()) for it in placed), default=y_pcb + t) + 0.3
    batt = None
    bl = next((ln for ln in facts.lines if ln.body is not None and ln.body.kind == "battery"), None)
    if bl is not None:
        if bl.body.shape == "pouch":
            batt = B.pouch(bl, lo, hi, top_y, max_h=max(hi[1] - top_y - 0.2, 0.8))
        else:
            batt = B.cells(bl, lo + [0, (top_y - lo[1]), 0], hi)
    return B, board, placed, down, batt, (lo, hi)


# --------------------------------------------------------------------------- plans per family


def _explode_dist(facts: Facts, axis: int = 1, k: float = 1.0) -> float:
    lo, hi = union_bb(housing(facts.parts))
    return max(float(hi[axis] - lo[axis]), 4.0) * k


def plan_shell(facts: Facts, title_housing: str = "housing", pcb_mat: str = "pcb_green", sensors_down: bool = False) -> Plan:
    B, board, placed, down, batt, (lo, hi) = shell_product(facts, pcb_mat, sensors_down)
    h = housing(facts.parts)
    hlo, hhi = union_bb(h)
    split = float(next((p["centroid_mm"][1] - p["measured_bbox_mm"][1] / 2 for p in _role(facts.parts, "shell_top")), (hlo[1] + hhi[1]) / 2))
    layer_of = split_shells(facts.parts, split)
    H = _explode_dist(facts)
    ids = lambda lay: [p for p, l_ in layer_of.items() if l_ == lay]  # noqa: E731
    internal = lambda lay: [it["extras"]["part_id"] for it in B.items if it["extras"]["layer_id"] == lay]  # noqa: E731
    extra_edges(B, facts, board, (lo, hi))
    Ls = []
    order = 0
    if ids("strap"):
        Ls.append(layer("strap", "Strap", order, ids("strap"), (0, -1, 0), H * 3.2, "The strap drops away"))
        order += 1
    Ls.append(layer("shell_top", "Top shell", order, ids("shell_top"), (0, 1, 0), H * 2.6, _shell_caption(facts, "shell_top")))
    order += 1
    if internal("battery"):
        Ls.append(layer("battery", "Battery", order, internal("battery"), (0, 1, 0), H * 1.7, _battery_caption(facts)))
        order += 1
    Ls.append(layer("pcb", "Main board", order, internal("pcb"), (0, 1, 0), H * 0.9, _pcb_caption(facts, B)))
    order += 1
    if internal("sensors"):
        Ls.append(layer("sensors", "Sensor stack", order, internal("sensors"), (0, -1, 0), H * 0.9, _sensor_caption(facts)))
        order += 1
    Ls.append(layer("shell_bottom", "Bottom shell", order, ids("shell_bottom"), (0, -1, 0), H * 1.8 if internal("sensors") else H * 1.2,
                    _shell_caption(facts, "shell_bottom")))
    return Plan(items=B.items, layer_of=layer_of, layers=[x for x in Ls if x["parts"]])


def extra_edges(B: Builder, facts: Facts, board: dict, cav) -> None:
    """Connectors / antenna / switches the packer left out go to the cavity edges (opening side = +X)."""
    lo, hi = cav
    for ln, b in [(ln, ln.body) for ln in facts.lines if ln.body is not None]:
        if b.kind == "battery":
            continue
    for btn in _role(facts.parts, "button"):
        c = np.array(btn["centroid_mm"])
        sw = B.line(r"switch|button|trigger")
        B.add("Switch under " + btn["name"].lower(), "component", "pcb", "switch",
              M.box((4.0, 2.5, 4.0), (c[0], min(c[1] - btn["measured_bbox_mm"][1] / 2 - 1.3, hi[1] - 1.3), c[2])), sw,
              "tactile switch 4 × 4 × 2.5 mm under the button cap (estimate)")


def _caption_parts(lines: list[Line], k: int = 2) -> str:
    bits = []
    for ln in lines[:k]:
        s = _short(ln.part)
        extra = [x for x in (ln.lcsc_pn and f"LCSC {ln.lcsc_pn}", ln.package, _fmt_price(ln.price)) if x]
        bits.append(s + (f" ({', '.join(extra)})" if extra else ""))
    return " + ".join(bits)


def _shell_caption(facts: Facts, which: str) -> str:
    d = facts.dims
    base = facts.material.split(" (")[0] if facts.material else "moulded plastic"
    if which == "shell_top" and d:
        return f"{base} shell, product {d[0]:.1f} × {d[1]:.1f} × {d[2]:.1f} mm (Measured), {facts.wall:.1f} mm wall (Estimate)"
    return f"{base} shell, {facts.wall:.1f} mm wall (Estimate)"


def _battery_line(facts: Facts) -> Line | None:
    return next((ln for ln in facts.lines if ln.body is not None and ln.body.kind == "battery"), None)


def _battery_caption(facts: Facts) -> str:
    bl = _battery_line(facts)
    if bl is None:
        return "No battery in the BOM"
    b = bl.body
    life = _lv(facts.battery_life, 1) if facts.battery_life and not facts.flight_time else ""
    wh = b.extras.get("wh")
    if b.shape == "cyl":
        s = (f"{b.extras.get('cells')} × 18650 Li-ion in series, {b.extras.get('voltage'):g} V pack"
             + (f" × {b.extras['mah']:.0f} mAh = {wh:.0f} Wh" if wh and b.extras.get("mah") else (f", {wh:.0f} Wh" if wh else "")))
    else:
        s = f"{_cap(bl) or f'{wh:.2f} Wh'} Li-po at {b.extras.get('voltage'):g} V (sized at {LIPO_WH_PER_L:.0f} Wh/L, Estimate)"
    if life:
        s += f" — {'runtime' if b.shape == 'cyl' else 'battery life'} {life}"
    if facts.flight_time:
        s += f" — flight time {_lv(facts.flight_time, 0)}"
    return s


def _pcb_caption(facts: Facts, B: Builder) -> str:
    mcu = [ln for ln in facts.lines if ln.body is not None and re.search(r"mcu|microcontroller|soc|compute|flight controller|mainboard|main pcb", ln.part, re.I)]
    return "Main board: " + (_caption_parts(mcu, 1) if mcu else "controller") + " — FR-4 board sized to the cavity (Estimate)"


def _sensor_caption(facts: Facts) -> str:
    s = [ln for ln in facts.lines if ln.category == "electronic" and re.search(r"ppg|optical|heart|temperature|spo2|imu", ln.part, re.I)]
    return "Sensors: " + _caption_parts(s, 3)


def storyboard_shell(facts: Facts, plan: Plan, title: str, *, housing_word: str = "product", sensor_title: str | None = None) -> list[dict]:
    parts = {p["part_id"]: p for p in facts.parts}
    parts.update(_metas(plan.items))
    L = {x["id"]: x for x in plan.layers}
    lo, hi = union_bb(list(parts.values()))
    steps = []
    i = 1
    first = [x for x in ("strap",) if x in L]
    steps.append(step(i, f"The {title}", _intro(facts), camera(lo, hi), [], []))
    i += 1
    ex = first + ["shell_top"]
    top = [p for p in L.get("shell_top", {}).get("parts", [])]
    steps.append(step(i, "Top shell lifts", L["shell_top"]["caption"], camera(*exploded_bb(parts, plan.layers, ex)), ex, top[:3]))
    i += 1
    ex2 = ex + [x for x in ("battery",) if x in L]
    pcb = L.get("pcb", {}).get("parts", [])
    steps.append(step(i, f"Inside the {housing_word}", L["pcb"]["caption"] if "pcb" in L else "Inside", camera(*exploded_bb(parts, plan.layers, ex2), zoom=1.2),
                      ex2, pcb[:4]))
    i += 1
    if "sensors" not in L and pcb:
        items = {it["extras"]["part_id"]: it for it in plan.items}
        priced = sorted([p for p in pcb if p in items and items[p]["extras"].get("unit_price")],
                        key=lambda p: -items[p]["extras"]["unit_price"]["value"])[:3]
        if priced:
            flo, fhi = union_bb([parts[p] for p in priced])
            ids = list(dict.fromkeys(items[p]["extras"]["bom_item_id"] for p in priced))
            lines = [ln for bid in ids for ln in facts.lines if ln.id == bid]
            steps.append(step(i, "Key components", "Key components: " + _caption_parts(lines, 3),
                              camera(flo, fhi, zoom=0.5), ex2, priced))
            i += 1
    if "sensors" in L:
        ex3 = ex2 + ["pcb", "sensors", "shell_bottom"]
        sp = L["sensors"]["parts"]
        slo, shi = union_bb([parts[p] for p in sp])
        steps.append(step(i, sensor_title or "The sensor stack", L["sensors"]["caption"],
                          camera(slo, shi, view=(0.7, -0.9, 1.0), zoom=0.35), ex3, sp))
        i += 1
    if "battery" in L:
        bp = L["battery"]["parts"]
        blo, bhi = union_bb([parts[p] for p in bp])
        bl = _battery_line(facts)
        t = f"Power — {_cap(bl) or 'battery'}" + (" Li-po" if bl and bl.body.shape == "pouch" else "")
        steps.append(step(i, t.strip(), L["battery"]["caption"], camera(blo, bhi, zoom=0.45), ex2, bp))
        i += 1
    steps.append(step(i, "Back together", _outro(facts), camera(lo, hi, view=(-1.0, 0.55, 1.3)), [], []))
    return steps


def _intro(facts: Facts) -> str:
    d = facts.dims
    n = len([ln for ln in facts.lines if ln.category == "electronic"])
    s = f"{facts.product}"
    if d:
        s += f" — {d[0]:.1f} × {d[1]:.1f} × {d[2]:.1f} mm (Measured)"
    if n == 0:
        m = len([ln for ln in facts.lines if ln.category == "mechanical"])
        return s + f", {m} mechanical BOM lines as construction layers (illustrative)"
    return s + f", {n} electronic BOM lines laid out inside (illustrative internal layout, not a routed PCB)"


def _outro(facts: Facts) -> str:
    uc = facts.unit_cost
    m = facts.total_mass or facts.weight
    what = "product mass" if facts.total_mass else "weight"
    mass = ""
    if m:
        mass = (f"{what} {m['value'] / 1000:.2f} kg (Estimate)" if m["value"] >= 1000 else f"{what} {_lv(m, 1)}")
    if uc:
        return f"Unit cost ${uc['value']:.2f} at {uc['quantity']:,} units (Estimate)" + (f", {mass}" if mass else "")
    return "Back together" + (f" — {mass}" if mass else "")


# ---- wearable -------------------------------------------------------------


def plan_wearable(facts: Facts) -> Plan:
    p = plan_shell(facts, pcb_mat="pcb_black", sensors_down=True)
    ppg = [ln for ln in facts.lines if re.search(r"ppg|optical|heart", ln.part, re.I)]
    tmp = [ln for ln in facts.lines if re.search(r"temperature", ln.part, re.I)]
    names = " + ".join(_short(ln.part).split(",")[0] for ln in (ppg[:1] + tmp[:1])) or "optical sensor"
    p.steps = storyboard_shell(facts, p, "band", housing_word="pod", sensor_title=f"The sensor stack — {names}")
    return p


# ---- drone ----------------------------------------------------------------


def plan_drone(facts: Facts) -> Plan:
    B = Builder(facts, "pcb_black")
    h = [p for p in housing(facts.parts)]
    lo, hi = cavity_of(h, facts.wall)
    size = hi - lo
    c = (lo + hi) / 2
    fc_line = B.line(r"flight controller")
    esc_line = B.line(r"\besc\b")
    k = 0.8
    fc = B.add("Flight controller" if not fc_line else _short(fc_line.part), "pcb", "avionics", "pcb_black",
               M.rounded_slab((min(36, size[0] * k), 1.6, min(36, size[2] * k)), (c[0], lo[1] + size[1] * 0.55, c[2]), 2), fc_line,
               "flight controller 36 × 36 mm class board (estimate)")
    esc = B.add("4-in-1 ESC" if not esc_line else _short(esc_line.part), "pcb", "avionics", "pcb_green",
                M.rounded_slab((min(36, size[0] * k), 1.6, min(36, size[2] * k)), (c[0], lo[1] + size[1] * 0.3, c[2]), 2), esc_line,
                "4-in-1 ESC 36 × 36 mm class, stacked under the flight controller (estimate)")
    fcb = {"board": {"lo": np.array([c[0] - 16, lo[1] + size[1] * 0.55 - 0.8, c[2] - 16]), "hi": np.array([c[0] + 16, lo[1] + size[1] * 0.55 + 0.8, c[2] + 16])}}
    chips = [(ln, b) for ln, b in electronic_bodies(facts, exclude=r"flight controller|\besc\b|motor|propell|gimbal|camera|compute|vision")]
    placed = B.populate(fcb, fit_bodies(chips, lo, hi, 3.0), "avionics")
    comp = B.line(r"compute|vision")
    if comp is not None:
        B.add(_short(comp.part), "component", "avionics", "module", M.box((min(40, size[0] * 0.7), 5, min(30, size[2] * 0.7)),
                                                                            (c[0], lo[1] + size[1] * 0.82, c[2])), comp, comp.body.source)
    # cables ESC → motors (motors sit under the props)
    props = _role(facts.parts, "prop")
    tips = []
    for pr in props:
        pc = np.array(pr["centroid_mm"])
        if not any(np.linalg.norm(pc[[0, 2]] - t[[0, 2]]) < 20 for t in tips):
            tips.append(pc)
    for i, t in enumerate(tips[:4]):
        a = np.array([c[0], lo[1] + size[1] * 0.3, c[2]])
        b = np.array([t[0], a[1], t[2]])
        B.cable(a, b, f"Motor lead {i + 1}", "avionics", red=bool(i % 2))
    # cells inside the battery pack part
    bp = _role(facts.parts, "battery")
    bl = _battery_line(facts)
    if bp and bl is not None:
        blo, bhi = _bb(bp[0])
        n = 4 if re.search(r"4\s*S", bl.part) else int(bl.body.extras.get("cells") or 3)
        size_b = bhi - blo
        for i in range(n):
            w = size_b[2] * 0.9 / n
            cz = blo[2] + size_b[2] * 0.05 + w * (i + 0.5)
            B.add(f"Li-po cell {i + 1}", "battery", "battery_pack", "battery",
                  M.rounded_slab((size_b[0] * 0.9, size_b[1] * 0.8, w * 0.92), ((blo[0] + bhi[0]) / 2, (blo[1] + bhi[1]) / 2 - size_b[1] * 0.4, cz), 1.0),
                  bl, f"{n}S pack: {n} pouch cells in series, filling the pack housing (estimate)")
    layer_of = {}
    for p in facts.parts:
        r = p["role"]
        layer_of[p["part_id"]] = {"prop": "props", "arm": "arms", "motor": "arms", "frame": "arms", "battery": "battery_pack",
                                  "component": "gimbal", "shell_bottom": "shell_bottom"}.get(r, "shell_top")
    Hh = _explode_dist(facts)
    internal = lambda lay: [it["extras"]["part_id"] for it in B.items if it["extras"]["layer_id"] == lay]  # noqa: E731
    ids = lambda lay: [p for p, l_ in layer_of.items() if l_ == lay]  # noqa: E731
    Ls = [layer("props", "Propellers", 0, ids("props"), (0, 1, 0), Hh * 2.5, _caption_parts(_lines(facts, r"propell"), 1) or "Propellers"),
          layer("battery_pack", "Battery pack", 1, ids("battery_pack") + internal("battery_pack"), (0, 1, 0), Hh * 3.5, _battery_caption(facts)),
          layer("shell_top", "Top shell", 2, ids("shell_top"), (0, 1, 0), Hh * 2.0, _shell_caption(facts, "shell_top")),
          layer("avionics", "Avionics stack", 3, internal("avionics"), (0, 1, 0), Hh * 0.8,
                "Avionics: " + _caption_parts(_lines(facts, r"flight controller|\besc\b|compute|vision"), 3)),
          layer("gimbal", "Gimbal camera", 4, ids("gimbal"), (1, -0.3, 0), Hh * 1.4, _caption_parts(_lines(facts, r"gimbal|camera"), 1) or "Gimbal"),
          layer("arms", "Arms + motors", 5, ids("arms"), (0, -1, 0), Hh * 0.4, _caption_parts(_lines(facts, r"motor|arm"), 2)),
          layer("shell_bottom", "Bottom shell", 6, ids("shell_bottom"), (0, -1, 0), Hh * 1.4, _shell_caption(facts, "shell_bottom"))]
    plan = Plan(items=B.items, layer_of=layer_of, layers=[x for x in Ls if x["parts"]])
    parts = {p["part_id"]: p for p in facts.parts}
    parts.update(_metas(plan.items))
    Lx = {x["id"]: x for x in plan.layers}
    lo_all, hi_all = union_bb(list(parts.values()))
    st = [step(1, "The drone", _intro(facts), camera(lo_all, hi_all), [], [])]
    ex = [x for x in ("props",) if x in Lx]
    st.append(step(2, "Props off", Lx.get("props", {}).get("caption", ""), camera(*exploded_bb(parts, plan.layers, ex)), ex, Lx.get("props", {}).get("parts", [])[:4]))
    ex += [x for x in ("battery_pack", "shell_top") if x in Lx]
    st.append(step(3, "Battery out, lid up", Lx.get("battery_pack", {}).get("caption", ""), camera(*exploded_bb(parts, plan.layers, ex)), ex,
                   Lx.get("battery_pack", {}).get("parts", [])[:6]))
    av = Lx.get("avionics", {}).get("parts", [])
    if av:
        alo, ahi = union_bb([parts[p] for p in av])
        st.append(step(4, "The avionics stack", Lx["avionics"]["caption"], camera(alo, ahi, zoom=0.8), ex, av[:6]))
    if "gimbal" in Lx:
        st.append(step(len(st) + 1, "The eye", Lx["gimbal"]["caption"], camera(*union_bb([parts[p] for p in Lx["gimbal"]["parts"]]), view=(1.3, 0.1, 0.6), zoom=0.7),
                       ex + ["gimbal"], Lx["gimbal"]["parts"][:3]))
    st.append(step(len(st) + 1, "Back together", _outro(facts), camera(lo_all, hi_all, view=(-1, 0.6, 1.2)), [], []))
    plan.steps = st
    return plan


# ---- stick vacuum -----------------------------------------------------------


def plan_vacuum(facts: Facts) -> Plan:
    B = Builder(facts, "pcb_green")
    parts = facts.parts
    motors = sorted(_role(parts, "motor"), key=lambda p: -np.prod(p["measured_bbox_mm"]))
    halves = [p for p in parts if re.search(r"motor", p["name"], re.I) and p["role"] in ("shell_top", "shell_bottom")]
    pod = motors[0] if motors else (halves[0] if halves else sorted(parts, key=lambda p: -np.prod(p["measured_bbox_mm"]))[0])
    if motors:
        plo, phi = _bb(motors[0])
    elif halves:  # C5 pro: the motor pod is split on its parting line into two housing halves
        plo, phi = union_bb(halves)
    else:
        plo, phi = _bb(pod)
    pc = (plo + phi) / 2
    ax = int(np.argmax(phi - plo))
    r = float(min(np.delete(phi - plo, ax))) / 2 * 0.72
    a, b = pc.copy(), pc.copy()
    span = float((phi - plo)[ax])
    a[ax] -= span * 0.32
    b[ax] += span * 0.05
    ml = B.line(r"bldc|vacuum motor|motor assembly")
    B.add(_short(ml.part) if ml else "BLDC motor", "motor", "motor", "motor", M.cylinder(a, b, r), ml,
          "BLDC vacuum motor sized to the motor pod (estimate)")
    c2 = b.copy()
    c2[ax] += span * 0.12
    B.add("Impeller", "component", "motor", "impeller", M.cylinder(b, c2, r * 0.9), ml, "mixed-flow impeller on the motor shaft (estimate)")
    bat = _role(parts, "battery")
    bl = _battery_line(facts)
    if bat and bl is not None:
        blo, bhi = _bb(bat[0])
        B.cells(bl, blo + 3, bhi - 3, layer="battery")
    grips = sorted(_named(parts, r"top_shell|body|handle|grip"), key=lambda p: p["centroid_mm"][1])
    g = grips[len(grips) // 2] if grips else pod
    glo, ghi = _bb(g)
    gc = (glo + ghi) / 2
    pl = B.line(r"control pcb|pcb|mosfet")
    gs = ghi - glo
    B.add(_short(pl.part) if pl else "Motor control PCB", "pcb", "electronics", "pcb_green",
          M.rounded_slab((max(gs[0] * 0.5, 18), 1.6, max(min(gs[2] * 0.5, 40), 18)), (gc[0], gc[1], gc[2]), 2), pl,
          "motor control board in the grip (estimate)")
    sw = B.line(r"trigger|switch")
    btns = _role(parts, "button")
    if btns:
        bc = np.array(sorted(btns, key=lambda p: p["centroid_mm"][1])[len(btns) // 2]["centroid_mm"])
        B.add(_short(sw.part) if sw else "Trigger switch", "component", "electronics", "switch", M.box((10, 12, 8), bc + [6, 0, 0]), sw,
              "microswitch behind the trigger (estimate)")
    cl = B.line(r"charging|connector|dc ")
    if bat:
        blo, bhi = _bb(bat[0])
        B.add(_short(cl.part) if cl else "DC charging jack", "connector", "battery", "connector",
              M.cylinder([blo[0] + 4, (blo[1] + bhi[1]) / 2, bhi[2] - 2], [blo[0] + 4, (blo[1] + bhi[1]) / 2, bhi[2] + 1], 4), cl,
              cl.body.source if cl and cl.body else "DC jack Ø8 mm (estimate)")
        B.cable(np.array([(blo[0] + bhi[0]) / 2, bhi[1], 0.0]), np.array([gc[0], gc[1], 0.0]), "Battery lead +", "electronics", red=True, r=1.6)
        B.cable(np.array([(blo[0] + bhi[0]) / 2 + 4, bhi[1], 0.0]), np.array([gc[0] + 4, gc[1], 0.0]), "Battery lead −", "electronics", r=1.6)
        B.cable(np.array([gc[0], gc[1], 0.0]), pc, "Motor phase leads", "electronics", r=2.0)
    layer_of = {}
    hand_lo = min(plo[1], *(p["centroid_mm"][1] for p in bat)) if bat else plo[1]
    for p in parts:
        nm = f"{p['name']} {p['part_id']}".lower()
        y = p["centroid_mm"][1]
        if y < hand_lo - 120:
            layer_of[p["part_id"]] = "wand_head"
        elif re.search(r"bin|clear|cyclone|window|filter|cone", nm) or p["role"] == "window":
            layer_of[p["part_id"]] = "bin"
        elif p["role"] == "battery":
            layer_of[p["part_id"]] = "battery"
        else:
            layer_of[p["part_id"]] = "housing"
    D = max(float(phi[2] - plo[2]), 60.0)
    internal = lambda lay: [it["extras"]["part_id"] for it in B.items if it["extras"]["layer_id"] == lay]  # noqa: E731
    ids = lambda lay: [p for p, l_ in layer_of.items() if l_ == lay]  # noqa: E731
    Ls = [layer("housing", "Motor pod + grip housing", 0, ids("housing"), (0, 0, 1), D * 2.2, _shell_caption(facts, "shell_top")),
          layer("bin", "Cyclone + clear bin", 1, ids("bin"), (1, 0.15, 0), D * 1.6,
                _caption_parts(_lines(facts, r"cyclone|bin|filter"), 2) or "Cyclone and bin"),
          layer("battery", "Battery pack", 2, ids("battery") + internal("battery"), (0, -0.3, 1), D * 1.4, _battery_caption(facts)),
          layer("motor", "Motor", 3, internal("motor"), (0, 0, 1), D * 0.9, _caption_parts(_lines(facts, r"bldc|motor"), 1)),
          layer("electronics", "Control electronics", 4, internal("electronics"), (0, 0, 1), D * 0.5,
                _caption_parts(_lines(facts, r"pcb|switch|trigger"), 2)),
          layer("wand_head", "Wand + floor head", 5, ids("wand_head"), (0, -1, 0), 0.0, _caption_parts(_lines(facts, r"wand|floor head"), 2))]
    plan = Plan(items=B.items, layer_of=layer_of, layers=[x for x in Ls if x["parts"]])
    allp = {p["part_id"]: p for p in parts}
    allp.update(_metas(plan.items))
    Lx = {x["id"]: x for x in plan.layers}
    lo, hi = union_bb(list(allp.values()))
    hand_ids = [p for lay in ("housing", "bin", "battery", "motor", "electronics") for p in Lx.get(lay, {}).get("parts", []) if p in allp]
    hand = [allp[p] for p in hand_ids]
    hlo, hhi = union_bb(hand)
    st = [step(1, "The vacuum", _intro(facts), camera(lo, hi, view=(1, 0.3, 1.4)), [], []),
          step(2, "Housing opens", Lx["housing"]["caption"], camera(*exploded_bb({k: allp[k] for k in hand_ids}, plan.layers, ["housing"])),
               ["housing"], Lx["housing"]["parts"][:3])]
    if "motor" in Lx:
        mlo, mhi = union_bb([allp[p] for p in Lx["motor"]["parts"]])
        st.append(step(3, "The motor", Lx["motor"]["caption"], camera(mlo, mhi, zoom=0.5), ["housing", "bin"], Lx["motor"]["parts"]))
    if "battery" in Lx:
        st.append(step(len(st) + 1, "Power", Lx["battery"]["caption"], camera(*union_bb([allp[p] for p in Lx["battery"]["parts"]]), zoom=0.6),
                       ["housing", "battery"], [p for p in Lx["battery"]["parts"] if p in _metas(plan.items)][:8]))
    if "bin" in Lx:
        st.append(step(len(st) + 1, "Cyclone + bin", Lx["bin"]["caption"], camera(*union_bb([allp[p] for p in Lx["bin"]["parts"]]), zoom=0.8),
                       ["bin"], Lx["bin"]["parts"][:4]))
    st.append(step(len(st) + 1, "Back together", _outro(facts), camera(hlo, hhi, view=(-1, 0.4, 1.3)), [], []))
    plan.steps = st
    return plan


# ---- smartphone / camera / home robot / irrigation / lamp / tracker (shell products with family touches) ---


def plan_smartphone(facts: Facts) -> Plan:
    B = Builder(facts, "pcb_green")
    h = housing(facts.parts) or facts.parts
    frame = sorted(facts.parts, key=lambda p: -np.prod(p["measured_bbox_mm"]))[0]
    lo, hi = _bb(frame)
    lo, hi = lo + [2.0, 0.6, 2.0], hi - [2.0, 0.6, 2.0]
    size, c = hi - lo, (lo + hi) / 2
    front = next((p for p in facts.parts if p["role"] == "window"), None)
    face_up = front is None or front["centroid_mm"][1] >= c[1]
    s = 1 if face_up else -1
    disp = B.line(r"display|touch")
    B.add(_short(disp.part) if disp else "Display", "component", "display", "display",
          M.box((size[0] * 0.96, 1.2, size[2] * 0.95), (c[0], c[1] + s * (size[1] / 2 - 0.8), c[2])), disp, "display stack under the cover glass (estimate)")
    mb = B.line(r"mainboard|main pcb|odm")
    zb = lo[2] + size[2] * 0.72
    B.add(_short(mb.part) if mb else "Mainboard", "pcb", "mainboard", "pcb_green",
          M.rounded_slab((size[0] * 0.9, 1.0, size[2] * 0.36), (c[0], c[1] - s * 1.0, zb), 2.0), mb, "ODM mainboard, upper third (estimate)")
    B.add("SoC + memory (shielded)", "component", "mainboard", "module", M.box((14, 1.4, 14), (c[0] - size[0] * 0.15, c[1] - s * 1.0 - s * 1.2, zb)), mb,
          "shield can over the SoC / PoP memory (estimate)")
    bl = _battery_line(facts)
    if bl is not None:
        vol = bl.body.extras["volume_cm3"] * 1000 if bl.body.shape == "pouch" else 12000
        L, W = size[0] * 0.82, size[2] * 0.5
        th = min(max(vol / (L * W), 2.5), size[1] - 3.0)
        B.add(f"Li-ion battery {_cap(bl)}".strip(), "battery", "battery", "battery",
              M.rounded_slab((L, th, W), (c[0], c[1] - s * 0.5, lo[2] + size[2] * 0.3), 2.0), bl, bl.body.source)
    cams = _role(facts.parts, "component", "lens")
    cl = B.line(r"camera")
    if cams:
        cc = np.array(sorted(cams, key=lambda p: -np.prod(p["measured_bbox_mm"]))[0]["centroid_mm"])
        B.add(_short(cl.part) if cl else "Camera module", "component", "cameras", "lens", M.box((9, 5, 9), (cc[0], c[1] - s * 1.5, cc[2])), cl,
              "camera module 9 × 9 × 5 mm under the lens (estimate)")
    al = B.line(r"antenna")
    for i, zz in enumerate((lo[2] + 1.0, hi[2] - 1.0)):
        B.add(f"Antenna {i + 1}", "antenna", "mainboard", "antenna", M.box((size[0] * 0.7, 0.3, 1.5), (c[0], c[1], zz)), al, "antenna flex at the end (estimate)")
    ul = B.line(r"usb")
    B.add("USB-C receptacle", "connector", "mainboard", "connector", M.box((8.9, 3.2, 7.3), (c[0], c[1], lo[2] + 3.6)), ul, "USB-C 8.9 × 7.3 × 3.2 mm")
    layer_of = {p["part_id"]: ("glass" if p["role"] == "window" and abs(p["centroid_mm"][1] - (c[1] + s * size[1] / 2)) < 2 else "frame") for p in facts.parts}
    T = max(size[1], 8.0)
    internal = lambda lay: [it["extras"]["part_id"] for it in B.items if it["extras"]["layer_id"] == lay]  # noqa: E731
    ids = lambda lay: [p for p, l_ in layer_of.items() if l_ == lay]  # noqa: E731
    Ls = [layer("glass", "Cover glass", 0, ids("glass"), (0, s, 0), T * 6, "Front cover glass"),
          layer("display", "Display", 1, internal("display"), (0, s, 0), T * 4.5, _caption_parts(_lines(facts, r"display"), 1) or "Display"),
          layer("mainboard", "Mainboard", 2, internal("mainboard"), (0, s, 0), T * 2.5, _caption_parts(_lines(facts, r"mainboard|antenna|usb"), 2)),
          layer("battery", "Battery", 3, internal("battery"), (0, s, 0), T * 1.5, _battery_caption(facts)),
          layer("cameras", "Cameras", 4, internal("cameras"), (0, -s, 0), T * 1.5, _caption_parts(_lines(facts, r"camera"), 1) or "Camera"),
          layer("frame", "Frame + back", 5, ids("frame"), (0, -s, 0), T * 0.5, _shell_caption(facts, "shell_top"))]
    plan = Plan(items=B.items, layer_of=layer_of, layers=[x for x in Ls if x["parts"]])
    plan.steps = storyboard_layers(facts, plan, "phone", view=(0.9, 1.3 * s, 1.1))
    return plan


def storyboard_layers(facts: Facts, plan: Plan, title: str, view=(1.0, 0.62, 1.35)) -> list[dict]:
    """Generic storyboard: assembled → peel the layers one by one (outermost first) → back together."""
    parts = {p["part_id"]: p for p in facts.parts}
    parts.update(_metas(plan.items))
    lo, hi = union_bb(list(parts.values()))
    st = [step(1, f"The {title}", _intro(facts), camera(lo, hi, view=view), [], [])]
    ex: list[str] = []
    for L in sorted(plan.layers, key=lambda x: x["order"]):
        if len(st) >= 6:
            break
        if L["explode_distance_mm"] <= 0:
            continue
        ex = ex + [L["id"]]
        focus = L["parts"][:6]
        st.append(step(len(st) + 1, L["name"], L["caption"], camera(*exploded_bb(parts, plan.layers, ex), view=view), list(ex), focus))
    for L in sorted(plan.layers, key=lambda x: -len(x["parts"])):  # at least 5 steps: close-ups of the richest layers
        if len(st) >= 4:
            break
        flo, fhi = union_bb([parts[p] for p in L["parts"] if p in parts])
        st.append(step(len(st) + 1, f"{L['name']} — close-up", L["caption"], camera(flo, fhi, view=view, zoom=0.9), list(ex), L["parts"][:6]))
    st.append(step(len(st) + 1, "Back together", _outro(facts), camera(lo, hi, view=(-view[0], view[1], view[2])), [], []))
    return st


def plan_generic(facts: Facts, title: str = "product", pcb_mat: str = "pcb_green") -> Plan:
    p = plan_shell(facts, pcb_mat=pcb_mat)
    B = Builder(facts, pcb_mat)
    B.items = p.items
    B._ids = {it["extras"]["part_id"]: 1 for it in p.items}
    lo, hi = cavity_of(housing(facts.parts), facts.wall)
    c = (lo + hi) / 2
    fam = facts.family
    if fam == "camera":
        lens = _role(facts.parts, "lens", "component") or _named(facts.parts, r"lens|camera")
        ll = B.line(r"lens|image sensor")
        if lens:
            lc = np.array(sorted(lens, key=lambda q: -np.prod(q["measured_bbox_mm"]))[0]["centroid_mm"])
            B.add("Image sensor + lens module", "lens", "pcb", "lens", M.box((12, 12, 8), (lc[0], lc[1], lc[2] - 6)), ll, "lens module 12 × 12 × 8 mm behind the lens (estimate)")
        ej = B.line(r"ejector|film")
        if ej is not None:
            B.add(_short(ej.part), "component", "pcb", "module", M.box(((hi - lo)[0] * 0.6, (hi - lo)[1] * 0.25, (hi - lo)[2] * 0.3),
                                                                       (c[0], lo[1] + (hi - lo)[1] * 0.8, c[2])), ej, "film ejector engine (estimate)")
    if fam == "irrigation":
        vl = B.line(r"valve|solenoid")
        B.add("Solenoid valve coil", "component", "pcb", "coil", M.cylinder([hi[0] - 18, lo[1] + 2, c[2]], [hi[0] - 18, lo[1] + 26, c[2]], 11), vl,
              "valve coil Ø22 × 24 mm (estimate)")
    if fam == "home_robot":
        for ln in _lines(facts, r"gearmotor|gear motor"):
            for i, side in enumerate((-1, 1)[: max(1, int(ln.qty))]):
                B.add(f"Drive gearmotor {i + 1}", "motor", "pcb", "motor", M.cylinder([c[0], lo[1] + 12, c[2] + side * 10], [c[0], lo[1] + 12, c[2] + side * 38], 12), ln,
                      "gearmotor Ø24 × 28 mm at the wheel axle (estimate)")
        li = B.line(r"lidar")
        if li is not None:
            B.add(_short(li.part), "component", "shell_top", "module", M.cylinder([c[0], hi[1] - 2, c[2]], [c[0], hi[1] + 18, c[2]], 20), li, "2D lidar Ø40 × 20 mm on top (estimate)")
    if fam == "lamp":
        B.add("LED board (COB)", "pcb", "pcb", "pcb_green", M.rounded_slab((30, 1.6, 30), (c[0], hi[1] - 3, c[2]), 3), B.line(r"led"),
              "LED board under the diffuser (estimate)")
    p.items = B.items
    internal = {it["extras"]["part_id"] for it in B.items}
    Lx = {x["id"]: x for x in p.layers}
    for it in B.items:
        pid, lay = it["extras"]["part_id"], it["extras"]["layer_id"]
        if lay in Lx and pid not in Lx[lay]["parts"]:
            Lx[lay]["parts"].append(pid)
    del internal
    p.steps = storyboard_shell(facts, p, title, housing_word={"camera": "body", "irrigation": "controller", "lamp": "base",
                                                              "tracker": "card", "home_robot": "robot"}.get(fam, "housing"))
    return p


# ---- solid products: construction layers ------------------------------------


def plan_board(facts: Facts, hull_mesh=None) -> Plan:
    B = Builder(facts)
    hull = sorted(facts.parts, key=lambda p: -np.prod(p["measured_bbox_mm"]))[0]
    lo, hi = _bb(hull)
    size, c = hi - lo, (lo + hi) / 2
    replace = {}
    if hull_mesh is not None:
        pos, nrm, tri = hull_mesh
        fn = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
        up = fn[:, 1] >= 0
        core = pos.copy()
        core = c + (core - c) * np.array([0.992, 0.9, 0.985])
        B.add("PU foam core (blank)", "other", "core", "foam", (core, nrm, tri), B.line(r"foam|blank|core"), "hull offset inward by the laminate (estimate)")
        replace[hull["part_id"]] = {"mesh": (pos, nrm, tri[up]), "material": MATS["laminate"],
                                    "extras": {"name": "Deck laminate (fibreglass + resin)", "material": MATS["laminate"]["name"]}}
        B.add("Bottom laminate (fibreglass + resin)", "other", "bottom_glass", "laminate", (pos * [1, 1, 1], nrm, tri[~up]), B.line(r"glass|laminat|cloth|resin"),
              "bottom half of the measured hull (estimate)")
    ax = int(np.argmax(size))
    st_l = size[ax] * 0.96
    B.add("Stringer", "frame", "core", "stringer", M.box((st_l, size[1] * 0.55, 3.0) if ax == 0 else (3.0, size[1] * 0.55, st_l), c), B.line(r"stringer|wood"),
          "3 mm basswood stringer on the centreline (estimate)")
    fins = [p for p in facts.parts if p["part_id"] != hull["part_id"] and (re.search(r"fin", p["name"], re.I) or p["role"] == "other")]
    for i, f in enumerate([p for p in fins if re.search(r"fin", p["name"], re.I)]):
        fc = np.array(f["centroid_mm"])
        B.add(f"Fin box {i + 1}", "fastener", "fins", "finbox", M.box((28, 8, 10), (fc[0], fc[1] + f["measured_bbox_mm"][1] / 2 + 3, fc[2])), B.line(r"fin box|fcs|futures"),
              "fin box 28 × 10 × 8 mm glassed into the bottom (estimate)")
    tail = lo[ax] + size[ax] * 0.05
    p_tail = c.copy()
    p_tail[ax] = tail
    B.add("Leash plug", "fastener", "deck", "plug", M.cylinder(p_tail + [0, size[1] * 0.25, 0], p_tail + [0, size[1] * 0.5, 0], 9), B.line(r"leash"),
          "leash plug Ø18 mm at the tail (estimate)")
    pad_c = c.copy()
    pad_c[ax] = lo[ax] + size[ax] * 0.14
    pad_c[1] = hi[1] - size[1] * 0.1
    B.add("Traction pad", "other", "deck", "pad", M.box((size[ax] * 0.14, 5.0, size[2] * 0.7) if ax == 0 else (size[0] * 0.7, 5.0, size[ax] * 0.14), pad_c),
          B.line(r"traction|pad|deck grip"), "EVA traction pad 5 mm over the tail (estimate)")
    layer_of = {hull["part_id"]: "deck_glass"}
    for f in fins:
        layer_of[f["part_id"]] = "fins"
    for p in facts.parts:
        layer_of.setdefault(p["part_id"], "fins")
    internal = lambda lay: [it["extras"]["part_id"] for it in B.items if it["extras"]["layer_id"] == lay]  # noqa: E731
    ids = lambda lay: [p for p, l_ in layer_of.items() if l_ == lay]  # noqa: E731
    T = max(size[1], 40.0)
    w = facts.weight
    Ls = [layer("deck", "Deck hardware", 0, internal("deck"), (0, 1, 0), T * 4.0, "EVA traction pad + leash plug (Estimate)"),
          layer("deck_glass", "Deck laminate", 1, ids("deck_glass"), (0, 1, 0), T * 2.6, "Fibreglass cloth + resin laminate over the deck" +
                (f" — board weight {_lv(w, 1)}" if w else "")),
          layer("core", "Foam core + stringer", 2, internal("core"), (0, 1, 0), T * 0.01, _caption_parts(_lines(facts, r"foam|blank|stringer"), 2) or
                "PU foam blank with a wood stringer"),
          layer("bottom_glass", "Bottom laminate", 3, internal("bottom_glass"), (0, -1, 0), T * 2.0, "Fibreglass laminate under the board"),
          layer("fins", "Fins + fin boxes", 4, ids("fins") + internal("fins"), (0, -1, 0), T * 3.6, _caption_parts(_lines(facts, r"fin"), 2) or "Fins and fin boxes")]
    plan = Plan(items=B.items, layer_of=layer_of, layers=[x for x in Ls if x["parts"]], kind="construction", replace=replace)
    plan.steps = storyboard_layers(facts, plan, "board", view=(0.5, 1.0, 1.4))
    return plan


def plan_furniture(facts: Facts) -> Plan:
    B = Builder(facts)
    parts = facts.parts
    lo, hi = union_bb(parts)
    size = hi - lo
    layer_of = {}
    for p in parts:
        nm = f"{p['name']} {p['part_id']}".lower()
        y = p["centroid_mm"][1]
        if p["role"] == "strap" or re.search(r"pad|fabric|basket", nm):
            layer_of[p["part_id"]] = "soft"
        elif y > lo[1] + size[1] * 0.8:
            layer_of[p["part_id"]] = "top"
        elif re.search(r"leg|frame|steel|metal", nm) or p["role"] == "frame":
            layer_of[p["part_id"]] = "frame"
        else:
            layer_of[p["part_id"]] = "panels"
    fl = B.line(r"screw|fastener|bolt|cam|dowel")
    legs = [p for p in parts if layer_of[p["part_id"]] == "frame"]
    llo, lhi = union_bb(legs or parts)
    for i, (x, z) in enumerate([(llo[0] + 20, llo[2] + 20), (lhi[0] - 20, llo[2] + 20), (llo[0] + 20, lhi[2] - 20), (lhi[0] - 20, lhi[2] - 20)]):
        for j, yy in enumerate((lo[1] + size[1] * 0.35, hi[1] - size[1] * 0.08)):
            B.add(f"Connector bolt {i + 1}.{j + 1}", "fastener", "fasteners", "fastener", M.cylinder([x, yy, z - 25], [x, yy, z + 25], 3.0, seg=12), fl,
                  "M6 × 50 connector bolt + barrel nut at each rail joint (estimate)")
    internal = lambda lay: [it["extras"]["part_id"] for it in B.items if it["extras"]["layer_id"] == lay]  # noqa: E731
    ids = lambda lay: [p for p, l_ in layer_of.items() if l_ == lay]  # noqa: E731
    H = max(size[1], 200.0)
    Ls = [layer("soft", "Pad + baskets", 0, ids("soft"), (0, 0.6, 1), H * 0.8, _caption_parts(_lines(facts, r"pad|basket|mattress"), 2) or "Soft parts"),
          layer("top", "Top + guard rails", 1, ids("top"), (0, 1, 0), H * 0.6, _shell_caption(facts, "shell_top")),
          layer("panels", "Panels + shelf", 2, ids("panels"), (0, 0, 1), H * 0.45, _caption_parts(_lines(facts, r"panel|shelf|rail|plywood"), 2) or "Panels"),
          layer("fasteners", "Fasteners", 3, internal("fasteners"), (0, 1, 0), H * 0.1, _caption_parts(_lines(facts, r"screw|fastener|bolt|hardware"), 1) or "Fasteners"),
          layer("frame", "Frame + legs", 4, ids("frame"), (0, -1, 0), 0.0, "Frame and legs")]
    plan = Plan(items=B.items, layer_of=layer_of, layers=[x for x in Ls if x["parts"]], kind="construction")
    plan.steps = storyboard_layers(facts, plan, "piece", view=(1.0, 0.7, 1.4))
    return plan


def plan(facts: Facts, hull_mesh=None) -> Plan:
    fam = facts.family
    if fam in ("wearable_band", "ring", "wearable"):
        return plan_wearable(facts)
    if fam == "drone":
        return plan_drone(facts)
    if fam == "stick_vacuum":
        return plan_vacuum(facts)
    if fam == "smartphone":
        return plan_smartphone(facts)
    if fam == "board":
        return plan_board(facts, hull_mesh)
    if fam in ("furniture", "solar_array"):
        return plan_furniture(facts)
    title = {"camera": "camera", "irrigation": "controller", "lamp": "lamp", "tracker": "tracker", "home_robot": "robot",
             "hair_dryer": "dryer"}.get(fam, "product")
    return plan_generic(facts, title, "pcb_black" if fam in ("camera", "tracker") else "pcb_green")


__all__ = ["plan", "Facts", "Line", "Plan", "MATS", "LABEL_NOTE"]
