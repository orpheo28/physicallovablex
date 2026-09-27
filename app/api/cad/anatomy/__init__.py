"""Product anatomy (W29): an illustrative internal layout generated from the real BOM, layer by layer. No LLM.

    GET /projects/{id}/anatomy?version=n → ProjectAnatomy   (contracts/api.md "3D parts & anatomy")
    anatomy(pid, n=None) -> ProjectAnatomy                  # built on first request, cached per version

Files: /files/<pid>/anatomy_v<n>.glb (companion GLB: exterior parts with the same part ids + internal bodies, each a
named node with PartMeta extras) and anatomy_v<n>.json (the ProjectAnatomy). Always labelled "Illustrative internal
layout — not a routed PCB"; internal bodies carry label "estimate" and the sizing rule in their package / name.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path

from fastapi import APIRouter

from api.cad import glb
from api.cad.anatomy import layout as LAY
from api.cad.anatomy.packages import body_for
from api.cad.build import normalize, project_dir
from contracts.artifacts import ANATOMY_LABEL, ProjectAnatomy

log = logging.getLogger("cad.anatomy")

ANATOMY_VERSION = "a4"  # bump when the layout rules change (cached anatomy_v<n>.json is rebuilt)
_locks: dict[str, threading.Lock] = {}
_reg = threading.Lock()


def _lock(key: str) -> threading.Lock:
    with _reg:
        return _locks.setdefault(key, threading.Lock())


def family_for(arts: dict) -> str:
    """Anatomy family: W21 product family, W17 wearable, else the engineering category (lamp, tracker…) or generic."""
    from api.cad import family_mode
    from api.cad.build import FAMILIES
    from api.studio import product as P

    d = P.chosen(arts.get(2))
    if d is not None:
        fam = family_mode.family_of(d)
        if fam:
            return fam
        f17 = FAMILIES.get(int(normalize(d.cad_parameters or {}).get("family", 0)))
        if f17 in ("wearable_band", "ring"):
            return f17
    brief = arts.get(1)
    text = " ".join(str(x) for x in [getattr(brief, "category", ""), getattr(brief, "product_name", ""), getattr(brief, "one_liner", "")]).lower()
    for rx, fam in ((r"lamp|light", "lamp"), (r"track|wallet|card|tag", "tracker"), (r"camera", "camera"), (r"phone", "smartphone"),
                    (r"irrigat|garden|valve", "irrigation"), (r"robot", "home_robot"), (r"wear|band|strap", "wearable_band")):
        if re.search(rx, text):
            return fam
    return "generic"


def facts_for(ctx, parts: list[dict]) -> LAY.Facts:
    from api.costs.lcsc import get_part, match_bom
    from api.studio import product as P

    arts = ctx.arts
    brief, spec, costs = arts.get(1), arts.get(3), arts.get(5)
    d = P.chosen(arts.get(2))
    priced = {ln.bom_item_id: ln for ln in (costs.bom_lines if costs is not None else [])}
    bom = list(spec.bom) if spec is not None else []
    try:
        matched = {m.id: m for m in match_bom([b.model_copy() for b in bom if b.lcsc_pn is None and str(getattr(b.category, "value", b.category)) == "electronic"])}
    except Exception:  # noqa: BLE001
        matched = {}
    lines = []
    for b in bom:
        cl = priced.get(b.id)
        pn = b.lcsc_pn or (cl.lcsc_pn if cl else None) or (matched.get(b.id).lcsc_pn if b.id in matched else None)
        lp = get_part(pn) if pn else None
        price = cl.unit_price.model_dump() if cl else (b.unit_cost_est.model_dump() if b.unit_cost_est else None)
        lines.append(LAY.Line(id=b.id, part=b.part, qty=float(b.qty), category=str(getattr(b.category, "value", b.category)),
                              lcsc_pn=pn, package=lp.package if lp else None, price=price, body=body_for(b, lp)))
    od = spec.overall_dimensions if spec is not None else None
    wall = 1.8
    if spec is not None:
        w = [p.wall_thickness.value for p in spec.parts if p.wall_thickness is not None]
        wall = float(min(w)) if w else wall
    elif d is not None:
        wall = float(normalize(d.cad_parameters or {}).get("wall", wall))
    eng = _engineering(ctx)
    el = eng.electronics if eng is not None else None
    if el is not None and el.battery_capacity is not None:  # a pack line without its capacity: use the engineering figure
        from api.cad.anatomy.packages import battery_body

        for ln in lines:
            if ln.body is not None and ln.body.kind == "battery" and not (ln.body.extras or {}).get("mah"):
                v = el.battery_voltage.value if el.battery_voltage is not None else 3.7
                cells = (ln.body.extras or {}).get("cells")
                ln.body = battery_body(f"{ln.part} {el.battery_capacity.value:.0f} mAh {v:g} V" + (f" {cells}S" if cells else ""))
                ln.body.source += " (capacity from the engineering power budget)"
    facts = LAY.Facts(family=family_for(arts), product=getattr(brief, "product_name", "") or "The product", parts=parts, lines=lines,
                      dims=(od.length.value, od.width.value, od.height.value) if od else None, wall=max(0.8, min(wall, 4.0)),
                      material=d.material if d else "", finish=d.finish if d else "",
                      weight=spec.weight.model_dump() if spec is not None and spec.weight else None)
    if eng is not None:
        el = eng.electronics
        if el is not None:
            facts.battery_life = el.battery_life.model_dump() if el.battery_life else None
            facts.average_current = el.average_current.model_dump() if el.average_current else None
        hover = next((c for c in eng.checks if c.id in ("hover_time", "flight_time")), None)
        if hover is not None and hover.value is not None:
            facts.flight_time = hover.value.model_dump()
    if costs is not None and costs.tiers:
        t = next((t for t in costs.tiers if t.quantity == costs.reference_quantity), costs.tiers[len(costs.tiers) // 2])
        facts.unit_cost = {"value": t.unit_cost.value, "quantity": t.quantity, "label": t.unit_cost.label}
    return facts


def _engineering(ctx):
    from api.studio import store

    try:
        if ctx.n == store.current(ctx.pid) or ctx.n == 0:
            from api.engineering.service import get_engineering

            return get_engineering(ctx.pid)
        # an older version: its own figures, computed from its snapshot (no cache write, no firmware)
        from api.engineering.service import compute
        from api.stages import runner
        from api.stages.registry import StageContext

        sctx = StageContext(project=runner.get_project(ctx.pid), stage=0, inputs={}, artifacts=dict(ctx.arts))
        return compute(sctx, llm_firmware=False, background=False, with_firmware=False)
    except Exception as e:  # noqa: BLE001 — captions just lose the battery-life figure
        log.info("anatomy: no engineering for %s: %s", ctx.pid, e)
    return None


_DENS = [(r"alumin", 2.70), (r"stainless|steel", 7.9), (r"glass", 2.5), (r"wood|beech|birch|plywood", 0.68), (r"foam|pad", 0.1),
         (r"silicone|lsr", 1.15), (r"tpu|tpe|rubber", 1.2), (r"carbon", 1.6), (r"pa12|nylon", 1.15)]


def total_mass(ctx, parts: list[dict], items: list[dict], facts) -> dict | None:
    """W29b: whole-product mass = exterior parts (measured surface area × wall × material density — shells, tubes,
    covers) + internal bodies (18650 cell 46 g, Li-po pouch at 180 Wh/kg, motors, PCBs). Estimate, formula stated.
    Solid products (board, furniture) keep the measured-volume weight of stage 3."""
    if facts.family in ("board", "furniture", "solar_array") or not parts:
        return None
    try:
        areas = glb.part_areas(ctx.path)
    except Exception:  # noqa: BLE001
        return None
    ext_g = 0.0
    for p in parts:
        mat = (p.get("material") or "").lower()
        dens = next((d for rx, d in _DENS if re.search(rx, mat)), 1.15)
        wall = 1.0 if dens > 2.6 else facts.wall  # metal tubes / covers are thinner than moulded walls
        vol_solid = p["measured_bbox_mm"][0] * p["measured_bbox_mm"][1] * p["measured_bbox_mm"][2]
        shell = areas.get(p["part_id"], 0.0) / 2 * wall  # both faces of a wall are in the mesh area → half
        ext_g += min(shell, vol_solid) / 1000 * dens
    int_g, bits = 0.0, []
    for it in items:
        ex = it["extras"]
        name = ex["name"].lower()
        pos = it["mesh"][0]
        size = pos.max(axis=0) - pos.min(axis=0)
        if name.startswith("18650"):
            g = 46.0
        elif ex["role"] == "battery":
            bl = next((ln for ln in facts.lines if ln.id == ex.get("bom_item_id")), None)
            wh = (bl.body.extras or {}).get("wh") if bl is not None and bl.body is not None else None
            g = (wh / 180 * 1000) if wh else float(size.prod()) / 1000 * 2.2
        elif ex["role"] == "motor":
            g = float(size.prod()) / 1000 * 3.0 * 0.55  # copper + steel, ~55 % fill of its envelope
        elif ex["role"] == "pcb":
            g = float(size.prod()) / 1000 * 1.85
        elif ex["role"] == "cable":
            g = float(size.max()) * 0.02
        else:
            g = float(size.prod()) / 1000 * 1.5
        int_g += g
    total = ext_g + int_g
    return {"value": round(total, 0), "unit": "g", "label": "estimate", "source_or_assumption": (
        f"All parts: exterior {ext_g:.0f} g (measured surface area × {facts.wall:.1f} mm wall, 1.0 mm for metal, × material "
        f"density) + internals {int_g:.0f} g (cells 46 g per 18650, Li-po 180 Wh/kg, motors, PCBs); the stage-3 weight "
        f"({facts.weight['value']:.0f} g) is the moulded enclosure only" if facts.weight else "")}


def _cached(pid: str, n: int) -> ProjectAnatomy | None:
    from api.cad.files import roots

    for r in roots(pid):
        f = r / f"anatomy_v{n}.json"
        g = r / f"anatomy_v{n}.glb"
        if f.is_file() and g.is_file():
            try:
                raw = json.loads(f.read_text())
                if raw.get("_v") == ANATOMY_VERSION:
                    raw.pop("_v", None)
                    return ProjectAnatomy.model_validate(raw)
            except (OSError, ValueError):
                continue
    return None


def build(ctx, out_dir: Path | None = None) -> ProjectAnatomy:
    from api.studio.parts import enriched

    pid, n = ctx.pid, ctx.n
    parts = enriched(ctx)
    facts = facts_for(ctx, parts)
    hull = None
    if facts.family == "board" and parts:
        big = max(parts, key=lambda p: p["measured_bbox_mm"][0] * p["measured_bbox_mm"][1] * p["measured_bbox_mm"][2])
        hull = glb.part_mesh(ctx.path, big["part_id"])
    pl = LAY.plan(facts, hull)
    facts.total_mass = total_mass(ctx, parts, pl.items, facts)
    if facts.total_mass is not None and pl.steps:  # the closing step states the whole-product mass
        pl.steps[-1]["caption"] = LAY._outro(facts)
    out = Path(out_dir) if out_dir else project_dir(pid)
    gpath = out / f"anatomy_v{n}.glb"
    metas = glb.compose(gpath, ctx.path, pl.items, layer_of=pl.layer_of, replace=pl.replace)
    all_ids = {m["part_id"] for m in metas}
    owner: dict[str, str] = {}
    for L in sorted(pl.layers, key=lambda x: x["order"]):
        L["parts"] = [p for p in dict.fromkeys(L["parts"]) if p in all_ids and p not in owner]
        owner.update({p: L["id"] for p in L["parts"]})
    layers = [L for L in pl.layers if L["parts"]]
    for m in metas:
        if m["part_id"] in owner:
            m["layer_id"] = owner[m["part_id"]]
    known = {L["id"] for L in layers}
    for s in pl.steps:
        s["layers_exploded"] = [x for x in s["layers_exploded"] if x in known]
        s["focus_parts"] = [x for x in s["focus_parts"] if x in all_ids]
    los = [[c - s / 2 for c, s in zip(m["centroid_mm"], m["measured_bbox_mm"])] for m in metas if m["layer_id"] != "context"]
    his = [[c + s / 2 for c, s in zip(m["centroid_mm"], m["measured_bbox_mm"])] for m in metas if m["layer_id"] != "context"]
    bbox = [round(max(h[i] for h in his) - min(lo[i] for lo in los), 2) for i in range(3)]
    for m in metas:  # every node's layer is one of the returned layers
        if m["layer_id"] not in known and layers:
            m["layer_id"] = layers[-1]["id"]
            layers[-1]["parts"].append(m["part_id"])
    glb.set_extras(gpath, {m["part_id"]: m for m in metas})
    res = ProjectAnatomy(version=n, glb_url=f"/files/{pid}/{gpath.name}", label=ANATOMY_LABEL, kind=pl.kind, bbox_mm=bbox,
                         layers=layers, steps=pl.steps, parts=metas)
    (out / f"anatomy_v{n}.json").write_text(json.dumps({"_v": ANATOMY_VERSION, **res.model_dump(mode="json")}, indent=1))
    return res


def anatomy(pid: str, n: int | None = None) -> ProjectAnatomy:
    from api.studio.parts import version_context

    ctx = version_context(pid, n)
    with _lock(f"{pid}:{ctx.n}"):
        hit = _cached(pid, ctx.n)
        if hit is not None:
            return hit
        return build(ctx)


def register(router: APIRouter) -> None:
    @router.get("/projects/{project_id}/anatomy", response_model=ProjectAnatomy, tags=["parts"])
    def get_anatomy(project_id: str, version: int | None = None) -> ProjectAnatomy:
        return anatomy(project_id, version)


__all__ = ["anatomy", "build", "facts_for", "family_for", "ANATOMY_VERSION"]
