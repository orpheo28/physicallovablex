"""Assembly checks (C2) → EngineeringCheck rows, domain "assembly": pass / warn / fail with the rule that decided.

    assembly_checks(result) -> [EngineeringCheck]
"""

from __future__ import annotations

import math

from contracts.artifacts import EngineeringCheck, LabeledValue

from api.cad.assembly.engine import SWEEP_PROBE, TOL, Result

RULE_INTERFERENCE = (f"0 intersecting pairs > {TOL:g} mm³ between parts that move relative to each other (different rigid "
                     "bodies, over their motion study) or across a parting line — CAD interference-check practice")
RULE_ENGAGEMENT = ("Heat-set insert: boss holds the insert + 0.5 mm and the screw engages ≥ 80 % of it (McMaster-Carr 94459A "
                   "insert data); tapped metal ≥ 1.5·d; thread-forming screw in plastic ≥ 2·d (EJOT DELTA PT design guide)")
RULE_CLOSURE = "build123d joints re-place every part at its modelled pose: residual < 0.01 mm"
RULE_SUPPORT = "Every part touches the part it is joined to (contact ≤ 0.05 mm)"
RULE_STATIC = ("Parts of one rigid body should not interpenetrate: overlap > 5 % of the smaller part = concept geometry to pocket "
               "at detail design (warn); smaller overlaps are seats (info)")


def _lv(v: float, unit: str, how: str, nd: int = 2) -> LabeledValue:
    return LabeledValue(value=round(float(v), nd), unit=unit, label="measured", source_or_assumption=how)


def _worst(vs: list[str]) -> str:
    for v in ("fail", "warn", "pass"):
        if v in vs:
            return v
    return "info"


def _gap_of(r: Result, i: int) -> float:
    row = r.pairs.get((min(i, r.parent[i]), max(i, r.parent[i]))) or {}
    return float(row["dist"] if row.get("dist") is not None else row.get("gap", 0.0))


def assembly_checks(r: Result) -> list[EngineeringCheck]:
    comps = r.comps
    name = {i: c.name for i, c in enumerate(comps)}
    out: list[EngineeringCheck] = []

    bad = [x for x in r.interferences if x["kind"] == "interference"]
    vol = sum(x["volume"] for x in bad)
    out.append(EngineeringCheck(
        id="asm_interference", name="Interference between moving parts", domain="assembly",
        value=_lv(len(bad), "pairs", f"Boolean common of every part pair (OCCT), classified by the assembly joints; "
                  f"total {vol:.1f} mm³", nd=0),
        threshold=RULE_INTERFERENCE, verdict="fail" if bad else "pass",
        formula="V(A ∩ B) per pair of solids at the assembled pose and over each moving joint's motion study",
        inputs=[_lv(vol, "mm³", "Sum of interference volumes")],
        notes=[f"{name[x['a']]} ↔ {name[x['b']]}: {x['volume']:.1f} mm³ — {x['note']}" for x in bad][:12]))

    static = [x for x in r.interferences if x["kind"] == "static_overlap"]
    big = [x for x in static if x["volume"] > 0.05 * min(comps[x["a"]].volume, comps[x["b"]].volume)]
    out.append(EngineeringCheck(
        id="asm_static_overlap", name="Overlaps inside rigid bodies (concept geometry)", domain="assembly",
        value=_lv(sum(x["volume"] for x in static), "mm³", f"{len(static)} pairs of rigidly joined parts interpenetrate "
                  f"({len(big)} over 5 % of the smaller part)", nd=1),
        threshold=RULE_STATIC, verdict="warn" if big else "info",
        formula="V(A ∩ B) for parts of the same rigid body that are not directly joined",
        notes=[f"{name[x['a']]} ↔ {name[x['b']]}: {x['volume']:.0f} mm³" for x in sorted(big, key=lambda x: -x["volume"])][:10]))

    rows = [c for c in r.clearances if c.get("min") is not None or c["verdict"] != "pass"]
    mins = [c["min"] for c in r.clearances if c.get("min") is not None and not c["motion"].startswith("static (parting")]
    moving = [c for c in r.clearances if not c["motion"].startswith("static (parting")]
    out.append(EngineeringCheck(
        id="asm_clearance", name="Minimum clearance of moving parts", domain="assembly",
        value=_lv(min(mins) if mins else SWEEP_PROBE, "mm", "BRepExtrema distance from each moving part (with what it carries) to "
                  "every other part except its joint parent / host, over its motion study" if mins else
                  f"Lower bound: no moving part has a neighbour within {SWEEP_PROBE:g} mm (or no moving joint)"),
        threshold="; ".join(sorted({c["rule"] for c in moving})) or "Moving parts clear their surroundings",
        verdict=_worst([c["verdict"] for c in moving]) if moving else "info",
        formula="min over poses of d(moving subtree, other parts); revolute props 12 poses / 360°, buttons pressed 0.5 mm",
        notes=[f"{name[c['part']]} → {name[c['against']] if c['against'] is not None else '—'}: "
               f"{('%.2f mm' % c['min']) if c.get('min') is not None else 'clear'} ({c['motion']}, {c['verdict']})"
               for c in rows if not c["motion"].startswith("static (parting")][:12]))

    parting = [c for c in r.clearances if c["motion"].startswith("static (parting")]
    if parting:
        out.append(EngineeringCheck(
            id="asm_parting_gap", name="Shell parting-line gap", domain="assembly",
            value=_lv(max(c["min"] or 0.0 for c in parting), "mm", "BRepExtrema distance between the two shells of each parting line"),
            threshold=parting[0]["rule"], verdict=_worst([c["verdict"] for c in parting]),
            formula="d(top shell, bottom shell); an overlap is reported as an interference",
            notes=[f"{name[c['part']]} / {name[c['against']]}: {c['min']:.2f} mm" for c in parting]))

    engs = [(j, j.engagement) for j in r.joints.values() if j.engagement]
    if engs:
        rows_e = [row for _, e in engs for row in e["rows"]]
        out.append(EngineeringCheck(
            id="asm_fastener_engagement", name="Screw engagement vs insert / thread", domain="assembly",
            value=_lv(min((row["engagement_mm"] for row in rows_e), default=0.0), "mm",
                      "Material under each screw measured by a line ∩ solid on both parts; flange capped at 2·d (counterbore), "
                      "screw = shortest ISO length reaching the insert / thread"),
            threshold=RULE_ENGAGEMENT, verdict=_worst([e["verdict"] for _, e in engs]),
            formula="engagement = min(insert length, screw length − flange); boss depth = material of the threaded part",
            inputs=[_lv(min((row["thread_mm"] for row in rows_e), default=0.0), "mm", "Smallest boss / thread material measured")],
            notes=[f"{name[j.child]} → {name[j.parent]}: {e['qty']} × {e['size']}×{e['screw_len']:g}"
                   + (f" + insert {e['size']}×{e['insert_len']:g}" if e["insert"] else " (tapped)")
                   + f", engagement ≥ {e['min_engagement']:.1f} mm, {e['verdict']}"
                   + (f" ({e['missing']} position(s) without material on both parts)" if e.get("missing") else "")
                   for j, e in engs][:12]))

    uses: dict[str, int] = {}
    for u in r.fastener_uses:
        k = f"{u.kind} {u.designation} ({u.standard})"
        uses[k] = uses.get(k, 0) + u.qty
    out.append(EngineeringCheck(
        id="asm_fastener_count", name="Fasteners by standard", domain="assembly",
        value=LabeledValue(value=float(sum(uses.values())), unit="pcs", label="estimate",
                           source_or_assumption="Joint rules (screws per parting-line perimeter, motor mounts, spring bars); "
                           "sizes from the part scale"),
        threshold=None, verdict="info", formula="Σ fasteners over the assembly joints",
        notes=[f"{q} × {k}" for k, q in sorted(uses.items())]))

    res = [j.residual_mm for j in r.joints.values()]
    worst = max((x for x in res if not math.isnan(x)), default=0.0)
    failed = sum(1 for x in res if math.isnan(x))
    out.append(EngineeringCheck(
        id="asm_joint_closure", name="Joint closure (build123d Joints)", domain="assembly",
        value=_lv(worst, "mm", f"Each child re-placed from its joint frame with build123d RigidJoint / RevoluteJoint / "
                  f"LinearJoint.connect_to; {len(res)} joints", nd=4),
        threshold=RULE_CLOSURE, verdict="fail" if failed or worst >= 0.01 else "pass",
        formula="|bbox centre after connect_to − modelled bbox centre|",
        notes=[f"{failed} joint(s) could not be built"] if failed else []))

    out.append(EngineeringCheck(
        id="asm_support", name="Every part is attached", domain="assembly",
        value=_lv(len(r.unsupported), "parts", "Parts with no contact (≤ 0.05 mm, BRepExtrema) with the part they are joined to",
                  nd=0),
        threshold=RULE_SUPPORT, verdict="warn" if r.unsupported else "pass",
        formula="d(child, parent) ≤ 0.05 mm for every joint",
        notes=[f"{name[i]} floats {_gap_of(r, i):.2f} mm from {name[r.parent[i]]}" for i in r.unsupported][:10]))
    return out


__all__ = ["assembly_checks"]
