"""Composite joints built from the standard parts + DFM rules (C1): what a family places in one call.

    screw_joint(size, at, direction, grip, head, into, boss_len) -> [screw, insert | nut, boss?]   placed, tagged
    add_parts(parts, shapes, default)  -> labels each placed standard part `<look role>.<n ≥ 100>` and appends it
    named(shape, name, kind)           -> tag a plain feature (latch button, access panel) with a part name
    std_length(v) -> the next ISO 4762 / 14583 preferred length ≥ v
    material_role(shape, default) -> look role for a placed standard part ("steel", "brass", "hardwood", …)

Imports only build123d + math (+ stdparts): usable from the codegen sandbox.
"""

from __future__ import annotations

from build123d import Vector

from api.cad.stdparts import dfm, hardware
from api.cad.stdparts import tables as T

STD_LENGTHS = (2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0)


def std_length(v: float) -> float:
    return next((x for x in STD_LENGTHS if x >= v - 1e-6), STD_LENGTHS[-1])


def screw_joint(size: str = "M3", at=(0.0, 0.0, 0.0), direction=(0.0, 0.0, -1.0), grip: float = 2.0, head: str = "pan",
                into: str = "insert", boss_len: float | None = None, wall: float = 2.0, length: float | None = None) -> list:
    """A screw whose head bears on the surface point `at`, shank along `direction`, clamping a `grip`-thick part onto
    a mating part that holds `into` = insert (heat-set) | pt (thread-forming boss hole) | nut | tap (threaded metal).
    `boss_len`: the mating part is a shell — a drafted boss (dfm.screw_boss) stands on its floor `boss_len` beyond the
    joint face. Screw length = grip + thread engagement (insert length / 2·d / nut + 2 P), preferred series."""
    s = size if size.startswith("M") else f"M{size}"
    d = T.NOMINAL[s]
    n = Vector(*direction).normalized()
    p0 = Vector(*at)
    face = p0 + n * grip
    out = []
    if into == "insert" and s in T.INSERT_HEATSET:
        engage = T.INSERT_HEATSET[s][1]
        out.append(hardware.heat_set_insert(s).along(face, n))
    elif into == "nut":
        engage = T.NUT_ISO4032[s][0] + T.PITCH[s] * 2
        out.append(hardware.hex_nut(s).along(face, n * -1))  # nut body from the face along n
    else:
        engage = 2.0 * d
    extra = T.CSK_ISO14581[s][1] if head == "countersunk" else 0.0
    length = length or std_length(grip + engage * 0.9 + extra)
    sc = hardware.pt_screw(d, length) if into == "pt" else hardware.screw(s, length, head)
    out.insert(0, sc.along(p0, n))
    if boss_len is not None and boss_len > 0.8:
        fast = "insert" if into == "insert" else ("tap" if into == "tap" else "pt")
        boss = dfm.screw_boss(s, boss_len, wall, fastener=fast)
        h = boss.std_meta["dfm"]["height_mm"]
        placed = hardware.frame(face + n * h, n) * boss  # base on the floor, hole opening at the joint face
        placed.std_meta = dict(boss.std_meta)
        out.append(placed)
    return out


def material_role(shape, default: str = "body") -> str:
    """Look role (api.cad.families.family_look) for a placed part from its std_meta material."""
    m = getattr(shape, "std_meta", None) or {}
    mat = str(m.get("material") or "").lower()
    if m.get("kind") in ("boss", "rib", "snap_fit", "weld_lip", "feature"):
        return m.get("look_role") or default
    if "brass" in mat:
        return "brass"
    if "beech" in mat or m.get("kind") == "wood_dowel":
        return "hardwood"
    if "epdm" in mat or "rubber" in mat:
        return "rubber"
    if "pom" in mat or "nylon" in mat or "abs" in mat or "pa-gf" in mat:
        return "coat"
    return "steel"


def named(shape, name: str, kind: str = "feature", role: str = "other", look_role: str | None = None):
    """Give a plain feature (a latch button, an access panel) a part name in the GLB / parts list."""
    shape.std_meta = {"kind": kind, "role": role, "name": name, "group": name, **({"look_role": look_role} if look_role else {})}
    return shape


def add_parts(parts: list, shapes: list, default: str = "body") -> list:
    """Label each placed part `<material role>.<100 + index>` and append it to `parts` (returns `parts`)."""
    for s in shapes:
        s.label = f"{material_role(s, default)}.{100 + len(parts)}"
        parts.append(s)
    return parts


__all__ = ["screw_joint", "std_length", "material_role", "named", "add_parts", "STD_LENGTHS"]
