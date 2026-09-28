"""Mate inference (C2): which part is joined to which, and how — from the part roles / names (W29 PartMeta) and the
family, never from an LLM.

    build_tree(comps, pairs, family=None) -> (root index, {child: parent}, {child: Mate})
    classify(child, parent, family) -> Mate      # joint kind / method / DOF + the rule that decided it

Tree: Prim's maximum spanning tree from the root over the contact graph. An edge's key is (preferred pairing, contact
class, overlap volume): a prop joins its motor, a motor its arm, a lens its camera, before any bigger overlap; a part with
no contact at all joins its nearest part and is reported as unsupported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

WHEEL = re.compile(r"\b(wheels?|rollers?|roll|brush(?: roll)?|casters?|tyres?|tires?|castors?)\b", re.I)
LID = re.compile(r"\b(lid|door|flap|hatch)\b", re.I)
HINGE = re.compile(r"\bhinges?\b", re.I)
GIMBAL = re.compile(r"\bgimbal\b|\byoke\b", re.I)
PRESS = re.compile(r"\b(trigger|button|key|switch|shutter)\b", re.I)
STRAP = {"strap"}
INLAY = {"window", "lens", "diffuser"}
SHELLS = {"shell_top", "shell_bottom"}
STRUCTURAL = {"shell_top", "shell_bottom", "frame", "other", "arm", "motor", "battery", "component"}
SOFT_LABELS = {"rubber", "fabric"}  # material roles of seals, feet, pads (bonded / press-fitted, no screws)
NEVER_PARENT = {"prop", "button", "diffuser", "connector", "antenna", "cable", "fastener_small"}

# child role → parent roles it prefers (family metadata: drone prop → motor → arm → hinge → fuselage, lens → camera …)
PREFERRED: dict[str, tuple[str, ...]] = {
    "prop": ("motor",),
    "motor": ("arm", "frame"),
    "arm": ("fastener", "frame", "shell_top", "shell_bottom"),
    "lens": ("component",),
    "window": ("shell_top", "shell_bottom", "frame", "other", "component"),
    "diffuser": ("shell_top", "shell_bottom", "other", "battery", "frame", "component"),
    "button": ("shell_top", "shell_bottom", "other", "frame"),
    "connector": ("shell_top", "shell_bottom", "other", "pcb"),
    "strap": ("shell_bottom", "shell_top"),
    "shell_top": ("shell_bottom",),
    "shell_bottom": ("shell_top",),
}


@dataclass
class Mate:
    kind: str                 # rigid | revolute | linear
    method: str               # screwed | snap_fit | inlay | press_fit | bonded | clip | hinge | bearing | slide | latch
    dof: int
    rule: str
    axis_hint: str | None = None   # "symmetry" | "thin" | "stack" | "z" | "hinge_edge" | "press" | None
    range: tuple[float, float] | None = None
    sweep: tuple[float, float, int] | None = None  # (from, to, steps) of the motion study; None = pose only
    parting: bool = False     # two shells meeting at a parting line: any overlap is an interference
    fasteners: dict[str, Any] = field(default_factory=dict)  # {"type": screws|spring_bars, "qty", "insert": bool, "tapped": bool}
    locked: bool = False      # set-and-lock DOF (folding arm): rigid in the use pose, motion not studied


def _span(c) -> float:
    s = c.bb.size
    return max(s.X, s.Y, s.Z)


def _footprint_perimeter(c, axis: int) -> float:
    s = [c.bb.size.X, c.bb.size.Y, c.bb.size.Z]
    a, b = [s[i] for i in range(3) if i != axis]
    return 2 * (a + b)


def _dims(c) -> tuple[float, float, float]:
    return (float(c.bb.size.X), float(c.bb.size.Y), float(c.bb.size.Z))


def is_parting_pair(a, b) -> bool:
    """Two shells meeting at a parting line: stacked along one axis with a similar footprint (±30 %) on the other two.
    Shell-named parts that are really a panel on a body (different footprint, or side by side) are not."""
    ca = [(a.bb.min.X + a.bb.max.X) / 2, (a.bb.min.Y + a.bb.max.Y) / 2, (a.bb.min.Z + a.bb.max.Z) / 2]
    cb = [(b.bb.min.X + b.bb.max.X) / 2, (b.bb.min.Y + b.bb.max.Y) / 2, (b.bb.min.Z + b.bb.max.Z) / 2]
    da, db = _dims(a), _dims(b)
    k = max(range(3), key=lambda i: abs(ca[i] - cb[i]) / max((da[i] + db[i]) / 2, 1e-6))
    if abs(ca[k] - cb[k]) < 0.25 * (da[k] + db[k]) / 2:
        return False
    lo = [a.bb.min.X, a.bb.min.Y, a.bb.min.Z], [b.bb.min.X, b.bb.min.Y, b.bb.min.Z]
    hi = [a.bb.max.X, a.bb.max.Y, a.bb.max.Z], [b.bb.max.X, b.bb.max.Y, b.bb.max.Z]
    along = min(hi[0][k], hi[1][k]) - max(lo[0][k], lo[1][k])  # interval overlap along the stack axis
    if along > 0.3 * min(da[k], db[k]):
        return False  # one sits inside the other's height: a nested part, not two shells meeting at a line
    return all(0.7 <= da[i] / max(db[i], 1e-6) <= 1 / 0.7 for i in range(3) if i != k)


def is_soft(c) -> bool:
    return all(lb.split(".")[0] in SOFT_LABELS for lb in c.labels)


def classify(child, parent, family: str | None = None) -> Mate:
    """Joint of `child` to `parent` (Comp objects with .role, .name, .labels, .bb, .volume)."""
    cr, pr, cn, pn = child.role, parent.role, child.name, parent.name
    soft = is_soft(child)
    if cr == "prop":
        return Mate("revolute", "bearing", 1, "Propeller on its motor shaft: revolute about the thin axis of the rotor disc "
                    "(multirotor family rule)", "thin", (0, 360), (0, 360, 12))
    if WHEEL.search(cn) and cr in ("other", "frame", "component"):
        return Mate("revolute", "bearing", 1, "Wheel / roller on an axle: revolute about its symmetry axis (rolling part rule)",
                    "symmetry", (0, 360), None)
    if cr == "arm" and (HINGE.search(pn) or (pr == "fastener" and family == "drone")):
        return Mate("revolute", "hinge", 1, "Folding arm on its hinge (drone family: arms fold for transport, locked open in "
                    "flight — checked in the flight pose, fold not swept)", "z", (0, 90), None, locked=True)
    if GIMBAL.search(pn) and cr in ("component", "lens", "other") and not GIMBAL.search(cn):
        return Mate("revolute", "bearing", 1, "Gimbal camera in its yoke: tilt axis (2-axis gimbal rule), swept ±20°",
                    "gimbal", (-90, 30), (-20, 20, 4))
    if cr == "button" or (PRESS.search(cn) and cr == "other"):
        return Mate("linear", "slide", 1, "Push button / trigger: linear travel 0.5 mm into its housing (tactile switch travel)",
                    "press", (0, 0.5), (0, 0.5, 2))
    if LID.search(cn) and cr in SHELLS | {"other", "window"}:
        return Mate("revolute", "hinge", 1, "Lid / door: revolute hinge on its rear edge, swept 0-100°", "hinge_edge", (0, 100),
                    (0, 100, 5))
    if family == "furniture" and cr in SHELLS | STRUCTURAL and pr in SHELLS | STRUCTURAL:  # C5: no moulded shells in plywood
        return Mate("rigid", "press_fit", 0, "Flat-pack panel joint: beech dowels pressed in + cam locks / wood screws (furniture "
                    "rule; the panel overlap is the dowel / rebate seat, not a parting line)", "stack")
    if cr in SHELLS and pr in SHELLS and is_parting_pair(child, parent):
        big = _span(child) >= 60 or _span(parent) >= 60
        if big:
            return Mate("rigid", "screwed", 0, "Two shells at a parting line: screws into heat-set inserts, one boss every "
                        "~80 mm of perimeter (min 4) — moulded-enclosure rule", "stack", parting=True,
                        fasteners={"type": "screws", "insert": True, "per_perimeter": 80.0, "min": 4, "max": 12})
        return Mate("rigid", "snap_fit", 0, "Two shells under 60 mm: snap-fit closure (no screws) — small-enclosure rule",
                    "stack", parting=True)
    if cr in STRAP:
        return Mate("rigid", "clip", 0, "Strap retained by two spring bars (wearable rule)", "stack",
                    fasteners={"type": "spring_bars", "qty": 2})
    if cr in INLAY or cr in ("connector", "antenna", "cable", "pcb", "fastener"):
        how = "press_fit" if cr in ("connector", "fastener") else "inlay"
        return Mate("rigid", how, 0, f"{child.name} set into {parent.name}: {how.replace('_', '-')} (insert rule; the host is "
                    "pocketed around it at detail design)", "stack")
    if cr == "battery":
        return Mate("rigid", "latch", 0, "Battery pack held by a latch (removable pack rule)", "stack")
    if soft:
        return Mate("rigid", "bonded", 0, "Soft part (rubber / fabric): bonded or press-fitted (seal / pad / foot rule)", "stack")
    if cr == "motor" and pr in ("arm", "frame"):
        return Mate("rigid", "screwed", 0, "Motor bolted to its arm: 4 screws into the motor base threads (motor-mount rule)",
                    "stack", fasteners={"type": "screws", "insert": False, "tapped": True, "qty": 4})
    span = _span(child)
    if span >= 20 and child.volume >= 1000 and pr in STRUCTURAL | SHELLS and cr in STRUCTURAL | SHELLS:
        metal = any(lb.split(".")[0] in ("metal", "steel") for lb in child.labels + parent.labels)
        qty = 2 if span < 150 else 4
        return Mate("rigid", "screwed", 0, f"Structural part ≥ 20 mm: {qty} screws" + (" into tapped metal" if metal else
                    " into heat-set inserts") + " (structural-joint rule)", "stack",
                    fasteners={"type": "screws", "insert": not metal, "tapped": metal, "qty": qty})
    return Mate("rigid", "snap_fit", 0, "Small moulded part: snap-fit / press-fit (small-part rule)", "stack")


_GENERIC_WORDS = {"part", "parts", "shell", "body", "main", "cover", "plate", "light", "window", "clear", "dark", "metal",
                  "rubber", "glass", "lower", "upper", "front", "rear", "left", "right", "housing"}


def _words(name: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z]{3,}", (name or "").lower())} - _GENERIC_WORDS


def _pref(child, parent) -> int:
    """Pairing preference of `parent` for `child`: -1 never … 4 (family rule + shared name word)."""
    if parent.role in NEVER_PARENT or (is_soft(parent) and not is_soft(child)):
        return -1
    if child.role == "arm" and (HINGE.search(parent.name) or parent.role == "fastener"):
        base = 3  # drone family: arm → folding hinge → fuselage
    elif parent.role in PREFERRED.get(child.role, ()):
        base = 2
    elif GIMBAL.search(parent.name) and GIMBAL.search(child.name) is None and child.role in ("component", "lens"):
        base = 2
    else:
        base = 1 if parent.role in STRUCTURAL | SHELLS else 0
    return base + (1 if _words(child.name) & _words(parent.name) else 0)


def choose_root(comps) -> int:
    cands = [i for i, c in enumerate(comps) if c.role in ("shell_bottom", "shell_top", "frame", "other")] or list(range(len(comps)))
    order = {"shell_bottom": 0, "shell_top": 1, "frame": 2, "other": 2}
    return max(cands, key=lambda i: (comps[i].volume, -order.get(comps[i].role, 3)))


def contact_class(pair: dict | None, tol_touch: float = 0.05) -> int:
    if not pair:
        return 0
    if pair.get("overlap", 0.0) > 0.0:
        return 2
    d = pair.get("dist")
    return 1 if d is not None and d <= tol_touch else 0


def build_tree(comps, pairs: dict[tuple[int, int], dict], family: str | None = None):
    n = len(comps)
    root = choose_root(comps)
    parent: dict[int, int] = {}
    inside = {root}

    def pair(u: int, v: int) -> dict | None:
        return pairs.get((min(u, v), max(u, v)))

    # the best pairing each part can get from a part it touches: a node waits for that parent to enter the tree
    best_pref = {v: max([_pref(comps[v], comps[u]) for u in range(n) if u != v and contact_class(pair(u, v)) > 0] or [-9])
                 for v in range(n)}

    def key(u: int, v: int) -> tuple:
        p = pair(u, v)
        cc = contact_class(p)
        ov = p.get("overlap", 0.0) if p else 0.0
        d = p.get("dist") if p and p.get("dist") is not None else (p.get("gap", 1e9) if p else 1e9)
        pr = _pref(comps[v], comps[u]) if cc > 0 else -9
        # contact first, then "this is the part's best parent", then pairing, contact class, overlap, distance
        return (1 if cc > 0 else 0, 1 if pr >= best_pref[v] else 0, pr, cc, ov, -d)

    while len(inside) < n:
        best = None
        for u in inside:
            for v in range(n):
                if v in inside:
                    continue
                k = key(u, v)
                if best is None or k > best[0]:
                    best = (k, u, v)
        _, u, v = best
        parent[v] = u
        inside.add(v)
    mates = {v: classify(comps[v], comps[u], family) for v, u in parent.items()}
    return root, parent, mates


__all__ = ["Mate", "classify", "build_tree", "choose_root", "contact_class"]
