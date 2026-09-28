"""Assembly engine (C2): labelled solids → components → mates as build123d Joints → pose, motion study, measured checks.

    load_step(step_path, glb_path=None) -> [Comp]      # one component per PartMeta part (GLB node), solids from the STEP
    from_shapes([(part_id, name, role, shape), …]) -> [Comp]   # in-process assemblies (tests, family builds)
    solve(comps, family=None) -> Result                 # everything ProjectAssembly needs (CAD axes, Z up, mm)

Every number here is measured on the solids with OCCT: boolean common (interference volume, tolerance TOL mm³),
BRepExtrema distance (clearance), line ∩ solid (material under a screw). Mates, screw sizes and counts are rules (see
mates.py / fasteners.py) and say so.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from api.cad.assembly import fasteners as fx
from api.cad.assembly.mates import Mate, build_tree, contact_class

log = logging.getLogger("cad.assembly")

ENGINE = "c2.2"  # c2.2 (C5): joints held by modelled C1 hardware get no rule-of-thumb fasteners; furniture panels press-fit
TOL = 0.01          # mm³: an intersection smaller than this is numerical noise, not an interference
PROBE = 3.0         # mm: pairs whose bounding boxes are closer than this get a measured distance
SWEEP_PROBE = 12.0  # mm: candidate parts around a moving part during the motion study
TOUCH = 0.05        # mm: closer than this = in contact


@dataclass
class Comp:
    part_id: str
    name: str
    role: str
    labels: list[str]
    shape: Any          # build123d Compound in world coordinates
    volume: float
    bb: Any
    hardware: bool = False  # C1 standard part / DFM feature modelled in the CAD (GLB root extras `stdparts`)


@dataclass
class JointOut:
    id: str
    parent: int
    child: int
    mate: Mate
    origin: tuple[float, float, float]
    axis: tuple[float, float, float] | None
    fasteners: list = field(default_factory=list)
    engagement: dict | None = None
    residual_mm: float = 0.0


@dataclass
class Result:
    comps: list[Comp]
    root: int
    parent: dict[int, int]
    joints: dict[int, JointOut]           # keyed by child index
    body: dict[int, int]                  # rigid body id per component
    pairs: dict[tuple[int, int], dict]
    interferences: list[dict]
    clearances: list[dict]
    explode: dict[int, tuple[tuple[float, float, float], float]]
    unsupported: list[int]
    fastener_uses: list
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- loading


def _solids(r) -> list:
    if r is None:
        return []
    if hasattr(r, "solids"):
        try:
            return list(r.solids())
        except Exception:  # noqa: BLE001
            return []
    out = []
    for x in r:
        out += _solids(x)
    return out


def _vol(shape) -> float:
    return float(sum(abs(s.volume) for s in _solids(shape)))


def _leaves(s) -> list:
    ch = list(getattr(s, "children", None) or [])
    if not ch:
        return [s]
    out = []
    for k in ch:
        out += _leaves(k)
    return out


def _norm_label(lb: str) -> str:
    """STEP product names lose the dot: 'body_1' → 'body.1' (GLB mesh names keep it)."""
    lb = lb or ""
    if "." in lb:
        return lb
    m = re.match(r"^(.*)_(\d+)$", lb)
    return f"{m.group(1)}.{m.group(2)}" if m else lb


def glb_parts(glb_path: Path | str) -> list[tuple[str, str, str, list[str]]]:
    """(part_id, name, role, [labels]) of a finished GLB (W29 node tree)."""
    from pygltflib import GLTF2

    g = GLTF2.load(str(glb_path))
    out = []
    for n in g.nodes:
        if isinstance(n.extras, dict) and "part_id" in n.extras:
            labels = [g.nodes[c].name for c in (n.children or []) if g.nodes[c].name]
            out.append((n.extras["part_id"], n.extras.get("name") or n.extras["part_id"], n.extras.get("role") or "other", labels))
    return out


def glb_hardware(glb_path: Path | str) -> set[str]:
    """part_ids of the standard parts / DFM features a pro build placed (C1: GLB root extras `stdparts`)."""
    from pygltflib import GLTF2

    g = GLTF2.load(str(glb_path))
    out: set[str] = set()
    for n in g.nodes:
        if isinstance(n.extras, dict) and isinstance(n.extras.get("stdparts"), dict):
            out |= set(n.extras["stdparts"])
    return out


def _mk(part_id: str, name: str, role: str, labels: list[str], shapes: list) -> Comp | None:
    from build123d import Compound

    solids = [s for sh in shapes for s in _solids(sh)]
    if not solids:
        return None
    shape = Compound(solids)
    shape.label = part_id
    return Comp(part_id, name, role, labels, shape, _vol(shape), shape.bounding_box())


def load_step(step_path: Path | str, glb_path: Path | str | None = None) -> list[Comp]:
    from build123d import import_step

    from api.cad.parts import default_name

    root = import_step(str(step_path))
    by_label: dict[str, list] = {}
    for lf in _leaves(root):
        by_label.setdefault(_norm_label(lf.label or ""), []).append(lf)
    comps: list[Comp] = []
    used: set[str] = set()
    if glb_path is not None:
        hw = glb_hardware(glb_path)
        for pid, name, role, labels in glb_parts(glb_path):
            shapes = [s for lb in labels for s in by_label.get(lb, [])]
            used.update(labels)
            c = _mk(pid, name, role, labels, shapes)
            if c is not None:
                c.hardware = pid in hw
                comps.append(c)
    for lb, shapes in by_label.items():  # solids the GLB does not name: their own part (material-role name)
        if lb in used:
            continue
        info = default_name(lb or "body.1")
        pid = info["part_id"]
        while any(c.part_id == pid for c in comps):
            pid += "_x"
        c = _mk(pid, info["name"], info["role"], [lb], shapes)
        if c is not None:
            comps.append(c)
    return comps


def from_shapes(items: list[tuple]) -> list[Comp]:
    """[(part_id, name, role, shape | [shapes])] → components (labels = part_id)."""
    out = []
    for it in items:
        pid, name, role, shp = it[:4]
        labels = list(it[4]) if len(it) > 4 else [f"{role}.1"]
        c = _mk(pid, name, role, labels, shp if isinstance(shp, (list, tuple)) else [shp])
        if c is not None:
            out.append(c)
    return out


# --------------------------------------------------------------------------- geometry helpers


def _v(p) -> tuple[float, float, float]:
    return (float(p.X), float(p.Y), float(p.Z))


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _len(a):
    return math.sqrt(_dot(a, a))


def _unit(a, default=(0.0, 0.0, 1.0)):
    n = _len(a)
    return default if n < 1e-9 else (a[0] / n, a[1] / n, a[2] / n)


def _size(bb) -> tuple[float, float, float]:
    return (float(bb.size.X), float(bb.size.Y), float(bb.size.Z))


def _center(bb) -> tuple[float, float, float]:
    return _v(bb.center())


def _gap(a, b) -> float:
    g = [max(0.0, a.min.X - b.max.X, b.min.X - a.max.X), max(0.0, a.min.Y - b.max.Y, b.min.Y - a.max.Y),
         max(0.0, a.min.Z - b.max.Z, b.min.Z - a.max.Z)]
    return math.sqrt(sum(x * x for x in g))


def _bb_overlap(a, b, tol: float = 1e-6) -> bool:
    return (a.min.X <= b.max.X + tol and b.min.X <= a.max.X + tol and a.min.Y <= b.max.Y + tol and b.min.Y <= a.max.Y + tol
            and a.min.Z <= b.max.Z + tol and b.min.Z <= a.max.Z + tol)


E3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def overlap(a, b) -> tuple[float, tuple | None, str | None]:
    """(volume mm³, centre of the common solid's bbox, error) of the boolean common of two shapes."""
    try:
        common = _solids(a.intersect(b))
    except Exception as e:  # noqa: BLE001
        return 0.0, None, f"boolean common failed: {e}"
    vol = sum(abs(s.volume) for s in common)
    if vol <= 0:
        return 0.0, None, None
    from build123d import Compound

    return float(vol), _center(Compound(common).bounding_box()), None


def distance(a, b) -> tuple[float, tuple | None, tuple | None]:
    try:
        d, p1, p2 = a.distance_to_with_closest_points(b)
        return float(d), _v(p1), _v(p2)
    except Exception:  # noqa: BLE001
        try:
            return float(a.distance_to(b)), None, None
        except Exception:  # noqa: BLE001
            return math.inf, None, None


def measure_pairs(comps: list[Comp]) -> dict[tuple[int, int], dict]:
    pairs: dict[tuple[int, int], dict] = {}
    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            a, b = comps[i], comps[j]
            gap = _gap(a.bb, b.bb)
            row: dict[str, Any] = {"gap": gap, "overlap": 0.0, "dist": None}
            if _bb_overlap(a.bb, b.bb):
                v, c, err = overlap(a.shape, b.shape)
                if err:
                    row["error"] = err
                if v > TOL:
                    row["overlap"], row["center"] = v, c
            if row["overlap"] <= TOL and gap <= PROBE:
                d, p1, p2 = distance(a.shape, b.shape)
                row["dist"] = d
                if p1 is not None and p2 is not None:
                    row["center"] = _mul(_add(p1, p2), 0.5)
            pairs[(i, j)] = row
    return pairs


def _pair(pairs, i, j) -> dict:
    return pairs.get((min(i, j), max(i, j))) or {}


def _sym_axis(bb) -> int | None:
    s = _size(bb)
    for i in range(3):
        o = [s[k] for k in range(3) if k != i]
        if o[1] > 0 and 0.85 <= o[0] / o[1] <= 1.18 and abs(s[i] - (o[0] + o[1]) / 2) > 0.08 * max(o):
            return i
    return None


def _stack_axis(c: Comp, p: Comp, origin=None) -> tuple[float, float, float]:
    """Principal axis along which the child sits away from the parent (normalised by the parent half-size), + sign."""
    ref = origin if origin is not None else _center(p.bb)
    rel = _sub(_center(c.bb), ref)
    ps = _size(p.bb)
    r = [rel[k] / max(ps[k] / 2, 1e-6) for k in range(3)]
    k = max(range(3), key=lambda i: abs(r[i]))
    if abs(r[k]) < 1e-3:
        rel = _sub(_center(c.bb), _center(p.bb))
        r = [rel[k2] / max(ps[k2] / 2, 1e-6) for k2 in range(3)]
        k = max(range(3), key=lambda i: abs(r[i]))
        if abs(r[k]) < 1e-3:
            return (0.0, 0.0, 1.0)
    return _mul(E3[k], 1.0 if r[k] >= 0 else -1.0)


def joint_frame(c: Comp, p: Comp, m: Mate, pair: dict) -> tuple[tuple, tuple]:
    """(origin, unit axis) of the joint in CAD coordinates."""
    cc, pc = _center(c.bb), _center(p.bb)
    contact = pair.get("center")
    toward = _sub(cc, pc)
    if m.axis_hint == "thin":
        s = _size(c.bb)
        k = min(range(3), key=lambda i: s[i])
        ax = E3[k]
        return cc, _mul(ax, 1.0 if _dot(ax, toward) >= 0 else -1.0)
    if m.axis_hint == "symmetry":
        k = _sym_axis(c.bb)
        if k is None:
            s = _size(c.bb)
            k = min(range(3), key=lambda i: s[i])
        ax = E3[k]
        return cc, _mul(ax, 1.0 if _dot(ax, toward) >= 0 else -1.0)
    if m.axis_hint == "z":
        return contact or cc, (0.0, 0.0, 1.0)
    if m.axis_hint == "gimbal":
        ps = _size(p.bb)
        k = 0 if ps[0] >= ps[1] else 1
        return cc, E3[k]
    if m.axis_hint == "hinge_edge":
        s = _size(c.bb)
        k = 0 if s[0] >= s[1] else 1          # hinge line along the longer horizontal side
        other = 1 - k
        sign = -1.0 if toward[other] >= 0 else 1.0   # on the side away from the parent's centre
        o = list(cc)
        o[other] = cc[other] + sign * s[other] / 2
        o[2] = c.bb.min.Z
        return tuple(o), E3[k]
    if m.axis_hint == "press":
        ref = contact if pair.get("overlap", 0) > 0 and contact is not None else pc
        return contact or cc, _stack_axis(c, p, ref)
    ax = _stack_axis(c, p)
    return (contact or cc), ax


def _loc(origin, axis):
    from build123d import Location, Plane

    x = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    # Gram-Schmidt so x ⟂ z
    x = _unit(_sub(x, _mul(axis, _dot(x, axis))))
    return Location(Plane(origin=origin, x_dir=x, z_dir=axis)), x


# --------------------------------------------------------------------------- joints (build123d)


class Posed:
    """build123d joints of one mate: parent joint + child copy in the joint frame (RigidJoint at its origin)."""

    def __init__(self, jid: str, parent: Comp, child: Comp, m: Mate, origin, axis):
        from build123d import Axis, LinearJoint, Location, RevoluteJoint, RigidJoint

        self.m = m
        loc, x = _loc(origin, axis)
        if m.kind == "linear":  # LinearJoint places a RigidJoint child translated along the axis, orientation unchanged
            loc = Location(origin)
        if m.kind == "revolute":
            lo, hi = m.range or (0, 360)
            self.pj = RevoluteJoint(jid, parent.shape, axis=Axis(origin, axis), angle_reference=x, angular_range=(lo, hi))
        elif m.kind == "linear":
            lo, hi = m.range or (0, 1)
            self.pj = LinearJoint(jid, parent.shape, axis=Axis(origin, axis), linear_range=(-abs(hi), abs(hi)))
        else:
            self.pj = RigidJoint(jid, parent.shape, loc)
        self.local = child.shape.moved(loc.inverse())
        self.cj = RigidJoint(jid, self.local, Location())
        self.base = None

    def place(self, value: float = 0.0):
        """Connect with the joint at `value` (deg / mm; linear: pressed = −value along the axis). Returns the child shape."""
        if self.m.kind == "revolute":
            self.pj.connect_to(self.cj, angle=value)
        elif self.m.kind == "linear":
            self.pj.connect_to(self.cj, position=-value)
        else:
            self.pj.connect_to(self.cj)
        return self.local

    def delta(self, value: float):
        """World transform that takes the assembled pose (value 0) to `value`."""
        if self.base is None:
            self.base = self.place(0.0).location
        loc = self.place(value).location
        return loc * self.base.inverse()


# --------------------------------------------------------------------------- solve


def _children(parent: dict[int, int]) -> dict[int, list[int]]:
    ch: dict[int, list[int]] = {}
    for c, p in parent.items():
        ch.setdefault(p, []).append(c)
    return ch


def _subtree(ch: dict[int, list[int]], i: int) -> list[int]:
    out, stack = [], [i]
    while stack:
        k = stack.pop()
        out.append(k)
        stack += ch.get(k, [])
    return out


def _order(root: int, ch: dict[int, list[int]]) -> list[int]:
    out, q = [], [root]
    while q:
        k = q.pop(0)
        out.append(k)
        q += sorted(ch.get(k, []))
    return out


def _line_material(shape, p0, p1) -> float:
    from build123d import Edge

    try:
        e = Edge.make_line(p0, p1)
        r = shape.intersect(e)
    except Exception:  # noqa: BLE001
        return 0.0
    if r is None:
        return 0.0
    try:
        edges = r.edges() if hasattr(r, "edges") else [x for y in r for x in y.edges()]
    except Exception:  # noqa: BLE001
        return 0.0
    return float(sum(x.length for x in edges))


def _screw_points(c: Comp, p: Comp, axis, origin, qty: int, parting: bool) -> list[list[tuple]]:
    """Candidate screw positions (projected on the plane ⟂ axis), outer to inner rings; each ring has `qty` points."""
    k = max(range(3), key=lambda i: abs(axis[i]))
    u, w = [i for i in range(3) if i != k]
    ref = c if (c.volume <= p.volume) else p
    lo = [ref.bb.min.X, ref.bb.min.Y, ref.bb.min.Z]
    hi = [ref.bb.max.X, ref.bb.max.Y, ref.bb.max.Z]
    rings = []
    for inset in (0.12, 0.2, 0.3, 0.4):
        pts2 = []
        if parting:
            a0, a1 = lo[u] + inset * (hi[u] - lo[u]), hi[u] - inset * (hi[u] - lo[u])
            b0, b1 = lo[w] + inset * (hi[w] - lo[w]), hi[w] - inset * (hi[w] - lo[w])
            corners = [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]
            mids = [((a0 + a1) / 2, b0), ((a0 + a1) / 2, b1), (a0, (b0 + b1) / 2), (a1, (b0 + b1) / 2)]
            pts2 = (corners + mids + [(a0 + (a1 - a0) * t, b) for t in (0.25, 0.75) for b in (b0, b1)])[:qty]
        else:
            r = (0.5 - inset) * min(hi[u] - lo[u], hi[w] - lo[w])
            cu, cw = origin[u], origin[w]
            pts2 = [(cu + r * math.cos(2 * math.pi * i / qty + math.pi / 4), cw + r * math.sin(2 * math.pi * i / qty + math.pi / 4))
                    for i in range(qty)]
        ring = []
        for a, b in pts2:
            pt = [0.0, 0.0, 0.0]
            pt[u], pt[w] = a, b
            ring.append(tuple(pt))
        rings.append(ring)
    return rings


def _engagement(c: Comp, p: Comp, m: Mate, origin, axis, size: str) -> dict:
    """Measured material under each screw (line ∩ solid) → screw length, engagement, verdict."""
    k = max(range(3), key=lambda i: abs(axis[i]))
    lo = min(_v(c.bb.min)[k], _v(p.bb.min)[k]) - 1
    hi = max(_v(c.bb.max)[k], _v(p.bb.max)[k]) + 1
    f = m.fasteners
    qty = int(f.get("qty") or 0)
    if f.get("per_perimeter"):
        per = max(p.bb.size.X + p.bb.size.Y, c.bb.size.X + c.bb.size.Y) * 2 if k == 2 else 2 * sum(_size(c.bb)) / 1.5
        qty = int(min(f.get("max", 12), max(f.get("min", 4), round(per / f["per_perimeter"]))))
    d = fx.nominal(size)
    rows = []
    best_ring = None
    for ring in _screw_points(c, p, axis, origin, qty, m.parting):
        rr = []
        for pt in ring:
            a, b = list(pt), list(pt)
            a[k], b[k] = lo, hi
            mc, mp = _line_material(c.shape, tuple(a), tuple(b)), _line_material(p.shape, tuple(a), tuple(b))
            rr.append((pt, mc, mp))
        ok = sum(1 for _, mc, mp in rr if mc > 0 and mp > 0)
        if best_ring is None or ok > best_ring[0]:
            best_ring = (ok, rr)
        if ok == len(rr):
            break
    rr = best_ring[1] if best_ring else []
    insert = bool(f.get("insert"))
    li = fx.insert_length(size) if insert else 0.0
    need = (1.5 if f.get("tapped") else 2.0) * d if not insert else 0.8 * li
    missing = sum(1 for _, mc, mp in rr if mc <= 0 or mp <= 0)
    rr = [x for x in rr if x[1] > 0 and x[2] > 0]
    for pt, mc, mp in rr:
        head, thread = (mc, mp) if mc <= mp else (mp, mc)
        flange = min(head, 2 * d)
        if insert:
            length = fx.screw_length(flange + li)
            eng = min(li, length - flange)
            fits = thread >= li + 0.5
        else:
            length = fx.screw_length(flange + need)
            eng = min(length - flange, max(0.0, thread - 0.3))
            fits = thread >= need
        verdict = "fail" if head <= 0 or thread <= 0 or (insert and not fits) else ("warn" if eng < need or not fits else "pass")
        rows.append({"point": pt, "head_mm": round(head, 2), "thread_mm": round(thread, 2), "flange_mm": round(flange, 2),
                     "screw_len": length, "engagement_mm": round(eng, 2), "need_mm": round(need, 2), "verdict": verdict})
    worst = "pass" if rows else "warn"  # no common material under any screw: the mate needs bosses at detail design
    for r in rows:
        if r["verdict"] == "fail" or (r["verdict"] == "warn" and worst == "pass"):
            worst = r["verdict"]
    length = max((r["screw_len"] for r in rows), default=fx.screw_length(2 * d + (li or 2 * d)))
    return {"size": size, "qty": qty, "insert": insert, "missing": missing, "insert_len": li, "screw_len": length, "rows": rows, "verdict": worst,
            "min_engagement": min((r["engagement_mm"] for r in rows), default=0.0),
            "min_thread_mat": min((r["thread_mm"] for r in rows), default=0.0)}


CLEAR_RULES = {  # (warn below mm, rule)
    "prop": (2.0, "Propeller ≥ 2 mm from any other part over a full turn (blade flex; multirotor build practice)"),
    "bearing": (1.0, "Rolling / rotating part ≥ 1 mm running clearance to its surroundings (debris, moulding tolerance)"),
    "slide": (0.2, "Push button pressed to the end of its travel keeps ≥ 0.2 mm to neighbouring parts (ISO 20457 moulded tolerances)"),
    "hinge": (1.0, "Hinged part keeps ≥ 1 mm to its neighbours over its swing"),
    "parting": (0.3, "Shells meet at the parting line: gap ≤ 0.3 mm (visible-gap limit for moulded enclosures)"),
}


def _held_by_hardware(comps: list[Comp], pairs: dict, c: int, p: int) -> list[str]:
    """Names of the modelled hardware parts (screws, inserts, bosses, weld lip…) that connect c to p: a chain of
    hardware components in contact, touching c at one end and p at the other. [] = the joint has no modelled hardware."""
    hw = [k for k, x in enumerate(comps) if x.hardware and k not in (c, p)]
    touch = lambda a, b: contact_class(_pair(pairs, a, b), TOUCH) > 0  # noqa: E731
    seen = {k for k in hw if touch(k, c)}
    todo = list(seen)
    while todo:
        k = todo.pop()
        for q in hw:
            if q not in seen and touch(k, q):
                seen.add(q)
                todo.append(q)
    if not any(touch(k, p) for k in seen):
        return []
    return sorted(comps[k].name for k in seen)


def _is_moving(m: Mate) -> bool:
    return m.dof > 0


def solve(comps: list[Comp], family: str | None = None) -> Result:
    notes: list[str] = []
    pairs = measure_pairs(comps)
    if len(comps) == 1:
        return Result(comps, 0, {}, {}, {0: 0}, pairs, [], [], {0: ((0.0, 0.0, 1.0), 0.0)}, [], [], notes)
    root, parent, mates = build_tree(comps, pairs, family)
    ch = _children(parent)
    order = _order(root, ch)

    # rigid bodies: union over rigid joints
    body = {i: i for i in range(len(comps))}

    def find(i):
        while body[i] != i:
            body[i] = body[body[i]]
            i = body[i]
        return i

    for c, p in parent.items():
        if mates[c].dof == 0 or mates[c].locked:
            body[find(c)] = find(p)
    roots = {}
    bodies = {i: roots.setdefault(find(i), len(roots)) for i in order}

    # joints: frames, build123d joints, closure residual, fasteners
    joints: dict[int, JointOut] = {}
    posed: dict[int, Posed] = {}
    uses = []
    unsupported = [c for c, p in parent.items() if contact_class(_pair(pairs, c, p), TOUCH) == 0]
    for n, c in enumerate([i for i in order if i != root], 1):
        p = parent[c]
        m = mates[c]
        origin, axis = joint_frame(comps[c], comps[p], m, _pair(pairs, c, p))
        jo = JointOut(id=f"j{n}", parent=p, child=c, mate=m, origin=origin, axis=axis)
        try:
            ps = Posed(jo.id, comps[p], comps[c], m, origin, axis)
            placed = ps.place(0.0)
            jo.residual_mm = _len(_sub(_center(placed.bounding_box()), _center(comps[c].bb)))
            posed[c] = ps
        except Exception as e:  # noqa: BLE001
            notes.append(f"joint {jo.id} ({comps[c].part_id}): build123d joint failed: {e}")
            jo.residual_mm = math.nan
        f = m.fasteners
        if c in unsupported:  # no contact: no material to screw into where it is drawn (clips / spring bars still count)
            f = {} if f.get("type") == "screws" else f
            jo.mate.rule += f" — NO CONTACT with {comps[p].name} (gap {(_pair(pairs, c, p).get('dist') or _pair(pairs, c, p).get('gap') or 0):.2f} mm): attach at detail design"
        held = _held_by_hardware(comps, pairs, c, p) if f.get("type") == "screws" else []
        if held:  # C5: the CAD already carries this joint's screws / inserts (C1, counted in the BOM): not twice
            f = {}
            jo.mate.rule += f" — held by the modelled hardware ({', '.join(held)})"
        if f.get("type") == "screws":
            size = fx.size_for(max(_size(comps[c].bb)) if not m.parting else max(max(_size(comps[c].bb)), max(_size(comps[p].bb))))
            eng = _engagement(comps[c], comps[p], m, origin, axis, size)
            jo.engagement = eng
            jo.fasteners = fx.uses_for_screwed(size, eng["screw_len"], eng["qty"], eng["insert"])
        elif f.get("type") == "spring_bars":
            s = _size(comps[c].bb)
            k = max(range(3), key=lambda i: abs(axis[i]))
            width = min(s[i] for i in range(3) if i != k) if s else 20.0
            jo.fasteners = fx.spring_bars(int(f.get("qty", 2)), min(max(width + 2, 10.0), 30.0))
        uses += jo.fasteners
        joints[c] = jo

    # a push button or a wheel sits in a pocket / wheel well that may run through every part of its host's rigid body
    def host(c: int) -> set[int]:
        m = mates.get(c)
        if m is None or not (m.method == "slide" or (m.method == "bearing" and m.axis_hint == "symmetry")):
            return {parent[c]} if c in parent else set()
        return {k for k in range(len(comps)) if bodies[k] == bodies[parent[c]] and k not in _subtree(ch, c)}

    hosts = {c: host(c) for c in parent}

    # interferences at the assembled pose
    inter = []
    for (i, j), row in pairs.items():
        v = row.get("overlap", 0.0)
        if v <= TOL:
            continue
        partner = parent.get(i) == j or parent.get(j) == i
        mate = mates.get(i) if parent.get(i) == j else mates.get(j) if parent.get(j) == i else None
        if partner and mate is not None and mate.parting:
            kind, note = "interference", "The two shells overlap across their parting line (they must only meet)"
        elif partner:
            kind, note = "joint_seat", f"Seat of joint {mate.method.replace('_', '-') if mate else ''}: concept overlap at the mate"
        elif j in hosts.get(i, ()) or i in hosts.get(j, ()):
            mover = i if j in hosts.get(i, ()) else j
            kind, note = "joint_seat", (f"Pocket / well of {comps[mover].name} through {comps[j if mover == i else i].name} "
                                        "(same rigid body as its joint parent)")
        elif bodies[i] == bodies[j]:
            kind, note = "static_overlap", "Same rigid body: concept geometry interpenetrates (pocket at detail design)"
        else:
            kind, note = "interference", "Parts that move relative to each other occupy the same space"
        inter.append({"a": i, "b": j, "volume": v, "kind": kind, "note": note})

    # motion study + clearances
    clear = []
    for c, jo in joints.items():
        m = jo.mate
        if m.parting:
            row = _pair(pairs, c, jo.parent)
            gap = 0.0 if row.get("overlap", 0) > TOL else (row.get("dist") if row.get("dist") is not None else row.get("gap", 0.0))
            warn, rule = CLEAR_RULES["parting"]
            clear.append({"part": c, "against": jo.parent, "min": gap, "motion": "static (parting line)",
                          "verdict": "pass" if gap <= warn else "warn", "rule": rule})
            continue
        if not _is_moving(m) or m.locked:
            continue
        key = "prop" if comps[c].role == "prop" else m.method if m.method in CLEAR_RULES else "hinge"
        warn, rule = CLEAR_RULES.get(key, CLEAR_RULES["hinge"])
        sub = _subtree(ch, c)
        others = [k for k in range(len(comps)) if k not in sub]
        steps = [0.0]
        if m.sweep is not None and c in posed:
            a0, a1, nstep = m.sweep
            steps = [a0 + (a1 - a0) * t / nstep for t in range(nstep + (0 if m.kind == "revolute" and a1 - a0 >= 360 else 1))]
        worst: dict[int, float] = {}
        hit: dict[int, float] = {}
        for val in steps:
            if val == 0.0 or c not in posed:
                shapes = {k: comps[k].shape for k in sub}
            else:
                try:
                    T = posed[c].delta(val)
                except Exception as e:  # noqa: BLE001
                    notes.append(f"motion study of {comps[c].part_id} at {val:g}: {e}")
                    continue
                shapes = {k: comps[k].shape.moved(T) for k in sub}
            for k, sh in shapes.items():
                sbb = sh.bounding_box()
                for o in others:
                    if k == c and o in hosts.get(c, {jo.parent}):
                        continue
                    if _gap(sbb, comps[o].bb) > SWEEP_PROBE:
                        continue
                    if _bb_overlap(sbb, comps[o].bb):
                        v, _, _ = overlap(sh, comps[o].shape)
                        if v > TOL:
                            if k == c and parent.get(o) == c:
                                continue
                            hit[o] = max(hit.get(o, 0.0), v)
                            worst[o] = 0.0
                            continue
                    d, _, _ = distance(sh, comps[o].shape)
                    if k == c and parent.get(o) == c:
                        continue
                    worst[o] = min(worst.get(o, math.inf), d)
        motion = ("static" if len(steps) == 1 else
                  f"{m.kind} {steps[0]:g}–{m.sweep[1]:g}{'°' if m.kind == 'revolute' else ' mm'} ({len(steps)} poses)")
        if not worst:
            clear.append({"part": c, "against": None, "min": None, "motion": motion, "verdict": "pass", "rule": rule,
                          "note": f"no part within {SWEEP_PROBE:g} mm"})
            continue
        o = min(worst, key=lambda k: (worst[k], -hit.get(k, 0)))
        dmin = worst[o]
        verdict = "fail" if o in hit else ("warn" if dmin < warn else "pass")
        clear.append({"part": c, "against": o, "min": dmin, "motion": motion, "verdict": verdict, "rule": rule,
                      "hit_volume": hit.get(o)})
        for oo, v in hit.items():  # a collision during the motion is an interference too
            if not any({x["a"], x["b"]} == {c, oo} for x in inter):
                inter.append({"a": c, "b": oo, "volume": v, "kind": "interference",
                              "note": f"Collision during the motion study ({motion})"})

    # exploded view: joint-derived direction, cumulative along the tree
    explode: dict[int, tuple[tuple, float]] = {root: ((0.0, 0.0, 1.0), 0.0)}
    offs: dict[int, tuple] = {root: (0.0, 0.0, 0.0)}
    for c in order:
        if c == root:
            continue
        jo = joints[c]
        cc = _center(comps[c].bb)
        if jo.mate.kind in ("revolute", "linear") and jo.axis is not None and jo.mate.axis_hint in ("thin", "symmetry", "press"):
            d = jo.axis
            if _dot(d, _sub(cc, _center(comps[jo.parent].bb))) < 0:
                d = _mul(d, -1.0)
        else:
            d = _stack_axis(comps[c], comps[jo.parent])
        s = _size(comps[c].bb)
        dist = abs(_dot(s, d)) * 0.6 + 0.12 * max(_size(comps[root].bb)) / max(1, len(_subtree(ch, c)) ** 0.5)
        off = _add(offs[jo.parent], _mul(d, dist))
        offs[c] = off
        explode[c] = (_unit(off), _len(off))

    return Result(comps, root, parent, joints, bodies, pairs, inter, clear, explode, unsupported, uses, notes)


__all__ = ["Comp", "Result", "load_step", "from_shapes", "solve", "glb_parts", "measure_pairs", "overlap", "distance",
           "ENGINE", "TOL"]
