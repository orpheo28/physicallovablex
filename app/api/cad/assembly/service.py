"""Assembly service (C2): a version's model → ProjectAssembly, cached per version; hooks for engineering, parts, costs.

    enabled() -> bool                                  # env CAD_ASSEMBLY (default 1 since C5; 0: nothing changes anywhere)
    assembly_for(pid, n=None, force=False) -> ProjectAssembly      # GET /projects/{id}/assembly?version=n
    to_contract(result, pid, n, source) -> ProjectAssembly         # engine Result → contract (GLB axes, +Y up)
    part_extras(pid, n=None) -> {part_id: {parent_part_id, joint, explode_vector, explode_distance_mm}}   # PartMeta hook
    fastener_bom(pid, n=None) -> [BOMItem]                         # aggregated fastener lines (fx1…)
    merge_fastener_lines(items, fasteners) -> [BOMItem]            # generic "fastener set" lines replaced
    costs_hook(ctx, items) -> [BOMItem]                            # C5: call in api.costs.bom.load_bom

Solids: the labelled STEP next to the version's GLB (`model_v<k>.step`, `v<n>.step`, `d<n>.step`), grouped into parts by the
GLB's W29 node tree. Cache: FILES_DIR/<pid>/assembly_v<n>.json keyed by engine version + STEP / GLB size and mtime.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path

from contracts.artifacts import (AssemblyClearance, AssemblyInterference, AssemblyJoint, AssemblyNode, BOMItem, LabeledValue,
                                 ProjectAssembly)

from api.cad.assembly import engine as E
from api.cad.assembly import fasteners as fx
from api.cad.assembly.checks import assembly_checks

log = logging.getLogger("cad.assembly")
_locks: dict[str, threading.Lock] = {}
_reg = threading.Lock()
FASTENER_LINE = re.compile(r"fastener|screw|bolt|hardware kit|fixings?", re.I)


def enabled() -> bool:
    return os.environ.get("CAD_ASSEMBLY", "1").strip().lower() in ("1", "true", "yes", "on")  # C5: on by default


def _lock(key: str) -> threading.Lock:
    with _reg:
        return _locks.setdefault(key, threading.Lock())


def glb_axes(v) -> list[float]:
    """CAD (Z up, mm) → GLB axes (+Y up): (x, y, z) → (x, z, −y) — the rotation build123d's glTF export applies."""
    return [round(float(v[0]), 4), round(float(v[2]), 4), round(-float(v[1]) + 0.0, 4)]


def family_of(arts: dict) -> str | None:
    from api.cad.family_mode import family_of as fam
    from api.studio import product as P

    d = P.chosen(arts.get(2))
    if d is None:
        return None
    f = fam(d)
    if f:
        return f
    try:
        return {3: "wearable_band", 4: "ring"}.get(int((d.cad_parameters or {}).get("family", 0)))
    except (TypeError, ValueError):
        return None


def step_for(pid: str, glb_path: Path) -> Path | None:
    from api.cad.files import resolve_file

    cand = [glb_path.with_suffix(".step")]
    stem = glb_path.stem
    for name in (f"{stem}.step", f"{stem.removesuffix('_ai')}.step", f"{stem.removesuffix('_ai')}_enclosure.step"):
        p = resolve_file(pid, name)
        if p is not None:
            cand.append(p)
    return next((c for c in cand if c.is_file()), None)


def to_contract(r: E.Result, pid: str, n: int, source: str) -> ProjectAssembly:
    comps = r.comps
    pid_of = {i: c.part_id for i, c in enumerate(comps)}
    joints = []
    for c in sorted(r.joints, key=lambda k: int(r.joints[k].id[1:])):
        j = r.joints[c]
        m = j.mate
        joints.append(AssemblyJoint(
            id=j.id, parent=pid_of[j.parent], child=pid_of[c], kind=m.kind, method=m.method, dof=0 if m.locked else m.dof,
            origin_mm=[round(x, 2) for x in glb_axes(j.origin)], axis=glb_axes(j.axis) if j.axis is not None else None,
            range=list(m.range) if m.range is not None and m.dof else None, fasteners=j.fasteners,
            rule=m.rule + (" (DOF locked in use)" if m.locked else "")))
    nodes = []
    for i, c in enumerate(comps):
        vec, dist = r.explode.get(i, ((0.0, 0.0, 1.0), 0.0))
        nodes.append(AssemblyNode(
            part_id=c.part_id, name=c.name, role=c.role, parent=pid_of.get(r.parent.get(i)) if i in r.parent else None,
            joint_id=r.joints[i].id if i in r.joints else None, rigid_body=r.body.get(i, 0),
            volume=LabeledValue(value=round(c.volume, 1), unit="mm³", label="measured", source_or_assumption="Solid volume (OCCT)"),
            explode_vector=glb_axes(vec), explode_distance_mm=round(dist, 1)))
    inter = [AssemblyInterference(a=pid_of[x["a"]], b=pid_of[x["b"]], kind=x["kind"], note=x["note"],
                                  volume=LabeledValue(value=round(x["volume"], 2), unit="mm³", label="measured",
                                                      source_or_assumption="Boolean common of the two solids (OCCT)"))
             for x in sorted(r.interferences, key=lambda x: ({"interference": 0, "static_overlap": 1}.get(x["kind"], 2), -x["volume"]))]
    clear = []
    for c in r.clearances:
        mv = c.get("min")
        clear.append(AssemblyClearance(
            part_id=pid_of[c["part"]], against=pid_of[c["against"]] if c.get("against") is not None else "—",
            min_clearance=LabeledValue(value=round(mv, 2) if mv is not None else float(E.SWEEP_PROBE), unit="mm", label="measured",
                                       source_or_assumption="BRepExtrema distance" + ("" if mv is not None else
                                                                                      f": nothing within {E.SWEEP_PROBE:g} mm (lower bound)")),
            motion=c["motion"], verdict=c["verdict"], rule=c["rule"]))
    checks = assembly_checks(r)
    fbom = fx.bom_lines(r.fastener_uses)
    bad = sum(1 for x in r.interferences if x["kind"] == "interference")
    moving = sum(1 for j in r.joints.values() if j.mate.dof and not j.mate.locked)
    nfx = sum(u.qty for u in r.fastener_uses)
    summary = (f"{len(comps)} parts · {len(r.joints)} joints ({moving} moving) · {bad} interference{'s' if bad != 1 else ''} · "
               f"{nfx} fasteners")
    return ProjectAssembly(project_id=pid, version=n, source=source, root=pid_of[r.root], nodes=nodes, joints=joints,
                           interferences=inter, clearances=clear, fasteners=fbom, checks=checks, summary=summary,
                           engine=E.ENGINE)


def _cache_key(step: Path, glb: Path) -> str:
    s, g = step.stat(), glb.stat()
    return f"{E.ENGINE}:{fx.SOURCE}:{s.st_size}:{int(s.st_mtime)}:{g.st_size}:{int(g.st_mtime)}"


def assembly_for(pid: str, n: int | None = None, force: bool = False) -> ProjectAssembly:
    """Raises api.stages.runner.NotFound (404) for an unknown project / version / a model without a labelled STEP."""
    from api.cad.build import project_dir
    from api.stages import runner
    from api.studio.parts import version_context

    ctx = version_context(pid, n)
    step = step_for(pid, ctx.path)
    if step is None:
        raise runner.NotFound(f"version {ctx.n}: no STEP next to {ctx.glb_url} — assembly needs the labelled solids")
    source = f"/files/{pid}/{step.name}"
    cache = project_dir(pid) / f"assembly_v{ctx.n}.json"
    key = _cache_key(step, ctx.path)
    with _lock(f"{pid}:{ctx.n}"):
        if not force and cache.is_file():
            try:
                raw = json.loads(cache.read_text())
                if raw.get("key") == key:
                    return ProjectAssembly.model_validate(raw["assembly"])
            except (OSError, ValueError, KeyError):
                pass
            except Exception:  # noqa: BLE001 — older schema: recompute
                pass
        comps = E.load_step(step, ctx.path)
        if not comps:
            raise runner.NotFound(f"{step.name}: no solids")
        res = E.solve(comps, family_of(ctx.arts))
        for note in res.notes:
            log.info("assembly %s v%s: %s", pid, ctx.n, note)
        out = to_contract(res, pid, ctx.n, source)
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"key": key, "assembly": out.model_dump(mode="json")}))
        except OSError as e:
            log.info("assembly cache not written for %s: %s", pid, e)
        return out


def part_extras(pid: str, n: int | None = None) -> dict[str, dict]:
    """PartMeta additive fields for GET /parts (C5 hook): parent, joint kind, joint-derived explode vector."""
    asm = assembly_for(pid, n)
    kind = {j.child: j.kind for j in asm.joints}
    return {nd.part_id: {"parent_part_id": nd.parent, "joint": kind.get(nd.part_id), "explode_vector": nd.explode_vector,
                         "explode_distance_mm": nd.explode_distance_mm} for nd in asm.nodes}


def fastener_bom(pid: str, n: int | None = None) -> list[BOMItem]:
    return list(assembly_for(pid, n).fasteners)


NOT_GENERIC = re.compile(r"anchor|anti-?tip|wall|strap|hinge|leash|fin\b|gasket|seal|magnet|bearing|wheel", re.I)


def is_generic_fastener(b: BOMItem) -> bool:
    """A lump 'fastener set / screws' line (template or LLM) by its part name, not a counted standard part (C1 hw…,
    C2 fx…) nor a functional kit that happens to contain screws (anti-tip wall anchor, hinge, strap…)."""
    return (str(getattr(b.category, "value", b.category)) == "mechanical" and not b.id.startswith(("fx", "hw"))
            and bool(FASTENER_LINE.search(b.part)) and not NOT_GENERIC.search(b.part))


def merge_fastener_lines(items: list[BOMItem], fasteners: list[BOMItem]) -> list[BOMItem]:
    """BOM + the assembly's fastener lines, one source of truth (C5): the hardware modelled in the CAD (C1 `hw` lines,
    counted on the model) stays; the assembly adds measured-length lines only for the joints that hardware does not
    hold (the engine skips those); a generic 'fastener set / screws' line is replaced by the counted ones (not double
    counted); ids stay unique."""
    counted = [b for b in items if b.id.startswith("hw")] + list(fasteners)
    if not counted:
        return list(items)
    keep = [b for b in items if not is_generic_fastener(b)]
    ids = {b.id for b in keep}
    return keep + [f for f in fasteners if f.id not in ids]


def costs_hook(ctx, items: list[BOMItem]) -> list[BOMItem]:
    """C5 hook for api.costs.bom.load_bom (after the BOM is chosen, before match_bom): the assembly's fastener lines replace
    a generic fastener line. No-op when CAD_ASSEMBLY=0 or the assembly is unavailable."""
    if not enabled():
        return list(items)
    try:
        return merge_fastener_lines(items, fastener_bom(ctx.project.id))
    except Exception as e:  # noqa: BLE001 — costs never fail because of the assembly
        log.info("fastener lines skipped for %s: %s", ctx.project.id, e)
        return list(items)


def engineering_group(project_id: str) -> tuple[list, ProjectAssembly] | None:
    """(assembly checks, ProjectAssembly) for the current version, or None (flag off / no STEP / failure — logged)."""
    if not enabled():
        return None
    try:
        asm = assembly_for(project_id)
    except Exception as e:  # noqa: BLE001 — engineering never fails because of the assembly group
        log.info("assembly group skipped for %s: %s", project_id, e)
        return None
    return list(asm.checks), asm


__all__ = ["enabled", "assembly_for", "to_contract", "part_extras", "fastener_bom", "merge_fastener_lines", "costs_hook",
           "is_generic_fastener",
           "engineering_group",
           "glb_axes"]
