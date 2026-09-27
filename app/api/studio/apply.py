"""Apply a RefinePatch to the current product, deterministically (W17). No LLM in here.

    apply(project, n, patch, before) -> Applied        # before/after = {stage: artifact} for stages 1-7

Order: brief (features, requirements, price, markets) → chosen direction (family, dimensions, colour, material,
finish) → CAD rebuilt from the parameters (cached by hash; version files v<n>.glb + v<n>_enclosure.{step,stl,glb}
are new names, so nothing current is touched until the caller commits) → spec (bbox Measured, weight, parts, BOM with
added components matched to the LCSC snapshot) → DFM (measured checks re-run, certifications re-mapped, component
risks) → costs (stage 5 code) → shortlist (stage 7 code). Any exception = nothing committed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from api.cad import directions as cad_directions
from api.cad import family_mode
from api.cad.build import FAMILY_CODES, build_direction, normalize, project_dir, publish, shape_facts
from api.cad.look import apply_materials, build_assembly, features_for, look_for
from api.cad.wearables import PRESETS as WEARABLE_PRESETS
from api.costs.lcsc import component_risk, match_bom
from api.stages.registry import StageContext
from api.studio import battery as battery_mod
from api.studio import product as P
from api.studio.patch import RefinePatch
from contracts.artifacts import (
    Assumption,
    BOMCategory,
    BOMItem,
    CadFile,
    DFMArtifact,
    Dimensions,
    ElectronicsBlock,
    ElectronicsEdge,
    FactoryPack,
    Label,
    LabeledValue,
    ProcessType,
    SpecPart,
    StructuredSpec,
    VersionChange,
)

log = logging.getLogger("studio.apply")

BBOX_CHECK = "Bounding box of the built STEP (build123d/OCCT)"
STRAP_THICKNESS = 2.4


@dataclass
class Applied:
    arts: dict
    render: bool = False  # colour / material / shape / dimensions changed → new concept render
    ai_review: bool = False  # geometry, material or BOM changed → AI DFM review in the background
    replan: bool = False  # stage 6 (processes per part) is stale
    battery: bool = False  # W21b: battery upgraded → runtime before/after in the change list
    rematch: bool = False  # W21c: an existing line was upgraded in place → re-match it to the LCSC snapshot
    drop: set[int] = field(default_factory=set)
    notes: list[VersionChange] = field(default_factory=list)


def _note(text: str, area: str = "requirement") -> VersionChange:
    return VersionChange(area=area, label="Note", before=None, after=text, label_kind=Label.estimate)


def _lv_mm(v: float, what: str) -> LabeledValue:
    return LabeledValue(value=round(v, 1), unit="mm", label="estimate", source_or_assumption=f"Design parameter ({what}), built in CAD")


def _mm(v: float, check: str) -> LabeledValue:
    return LabeledValue(value=round(v, 2), unit="mm", label="measured", source_or_assumption=check)


def _dims(size, check: str) -> Dimensions:
    return Dimensions(length=_mm(size[0], check), width=_mm(size[1], check), height=_mm(size[2], check))


def family_params(family: str, brief) -> dict[str, float]:
    code = FAMILY_CODES[family]
    if code in WEARABLE_PRESETS:
        return normalize(WEARABLE_PRESETS[code])
    pr = cad_directions._PRESETS[cad_directions.preset_key(brief)][family]
    return normalize({"family": code, "length": pr["length"], "width": pr["width"], "height": pr["height"],
                      "fillet": pr["fillet"], "edge_fillet": pr.get("edge_fillet", 3.0), "wall": pr.get("wall", 2.0),
                      "draft_deg": 1.5, "split_ratio": 0.6, "boss_count": 4})


def render_extra(family: str, params: dict, brief) -> str:
    """Render-prompt details that match the viewer model (the desk-product details do not apply to wearables)."""
    from api.cad.look import describe_features

    if family == "wearable_band":
        return (f"; details: a soft {params.get('strap_width', 24):.0f} mm wide strap looping under the pod, an optical "
                "sensor window underneath, no screen, no buttons")
    if family == "ring":
        return "; details: a smooth band with a small sensor bump on the inside, no screen, no buttons"
    return describe_features(features_for(brief))


# --------------------------------------------------------------------------- spec helpers


def ensure_strap(spec, params: dict, family: str, material: str, finish: str) -> bool:
    """wearable_band: a strap BOM line + spec part (moulded LSR, Estimate dimensions); other families: none. → changed?"""
    has_line = [b for b in spec.bom if "strap" in b.part.lower()]
    has_part = [p for p in spec.parts if p.name.lower().startswith("strap")]
    if family != "wearable_band":
        if not has_line and not has_part:
            return False
        spec.bom = [b for b in spec.bom if b not in has_line]
        spec.parts = [p for p in spec.parts if p not in has_part]
        return True
    _, cname, chex = P.split_finish(finish)
    strap_finish = P.join_finish("Matte", cname, chex)
    why = "Design parameter (strap), not measured: the strap is drawn in the viewer model only"
    dims = Dimensions(length=LabeledValue(value=params["strap_length"], unit="mm", label="estimate", source_or_assumption=why),
                      width=LabeledValue(value=params["strap_width"], unit="mm", label="estimate", source_or_assumption=why),
                      height=LabeledValue(value=STRAP_THICKNESS, unit="mm", label="estimate", source_or_assumption=why))
    part = SpecPart(id="p5", name="Strap", material="Liquid silicone rubber (LSR)", finish=strap_finish,
                    process_hint=ProcessType.injection_molding, tolerance="±0.2 mm on width and pin holes", dimensions=dims,
                    wall_thickness=LabeledValue(value=STRAP_THICKNESS, unit="mm", label="estimate", source_or_assumption=why))
    spec.parts = [p for p in spec.parts if p not in has_part] + [part]
    if not has_line:
        spec.bom.append(BOMItem(id=P.next_bom_id(spec.bom, "mechanical"), part="Strap, liquid silicone rubber (LSR) with pin buckle",
                                category=BOMCategory.mechanical, qty=1,
                                description=f"{params['strap_width']:.0f} mm wide, {params['strap_length']:.0f} mm long"))
    return True


def _pcb_dims(params: dict, w: float) -> Dimensions:
    def est(v: float, what: str) -> LabeledValue:
        return LabeledValue(value=round(max(v, 5.0) if what != "thickness" else v, 1), unit="mm", label="estimate",
                            source_or_assumption=f"PCB {what}: fits the inner cavity with 1 mm clearance")

    k = 0.7 if int(params["family"]) in (1, 4) else 1.0
    margin = 2 * w + 2 + (4 if int(params["family"]) >= 3 else 12)
    return Dimensions(length=est(params["length"] * k - margin, "length"), width=est(params["width"] * k - margin, "width"),
                      height=est(1.6 if int(params["family"]) < 3 else 0.8, "thickness"))


def rebuild_cad(project_id: str, n: int, design, spec, brief, params: dict, family: str) -> dict:
    """Build the version files and update direction + spec geometry in place. Returns the shape facts."""
    d = P.chosen(design)
    pdir = project_dir(project_id)
    files = build_direction(params, pdir)  # cache paths (hash of params)
    stems = {k: pdir / f"v{n}_enclosure.{k}" for k in ("step", "stl", "glb")}
    for k, dst in stems.items():
        publish(files[k], dst)
    look = look_for(d.material, d.finish)
    try:
        apply_materials(stems["glb"], look)
    except Exception as e:  # noqa: BLE001 — a grey model is still a valid model
        log.info("enclosure materials skipped: %s", e)
    full = pdir / f"v{n}.glb"
    try:
        build_assembly(params, full, look, features_for(brief))
    except Exception as e:  # noqa: BLE001 — the shells are still the product
        log.warning("assembly v%d failed, shells only: %s", n, e)
        publish(stems["glb"], full)
    facts = shape_facts(stems["step"])

    density = P.MATERIALS[P.material_key(d.material)][1]
    d.cad_parameters = {**params, "density_g_cm3": density}
    d.glb_url = f"/files/{project_id}/v{n}.glb"
    d.dimensions = Dimensions(length=_lv_mm(params["length"], "length"), width=_lv_mm(params["width"], "width"),
                              height=_lv_mm(params["height"], "height"))

    spec.direction_id = d.id
    spec.product_name = brief.product_name
    spec.overall_dimensions = _dims(facts["size"], BBOX_CHECK + (", pod only (strap excluded)" if family == "wearable_band" else ""))
    vol = facts["volume_mm3"] / 1000.0
    mat_name = d.material.split(" (")[0]
    spec.weight = LabeledValue(value=round(vol * density, 1), unit="g", label="estimate",
                               source_or_assumption=f"Enclosure volume {vol:.1f} cm³ (measured) × {mat_name} {density} g/cm³; electronics, battery and strap not included")
    process = ProcessType.cnc if density > 2 else ProcessType.injection_molding
    shells = {"Bottom shell": 0, "Top shell": 1}
    for p in spec.parts:
        if p.name in shells and shells[p.name] < len(facts["solids"]):
            p.dimensions = _dims(facts["solids"][shells[p.name]]["size"], BBOX_CHECK + ", this part")
            p.material, p.finish, p.process_hint = d.material, d.finish, process
            p.wall_thickness = LabeledValue(value=params["wall"], unit="mm", label="estimate",
                                            source_or_assumption="Design parameter (nominal wall); measured in DFM stage 4")
        elif p.process_hint in (ProcessType.pcba, ProcessType.pcba.value):
            p.dimensions = _pcb_dims(params, params["wall"])
    size = lambda f: f.stat().st_size  # noqa: E731
    spec.cad_files = [
        CadFile(format="glb", url=d.glb_url, description="Full product — materials", size_bytes=size(full)),
        CadFile(format="step", url=f"/files/{project_id}/v{n}_enclosure.step", description="Moulded parts (DFM) — both shells, STEP AP214", size_bytes=size(stems["step"])),
        CadFile(format="stl", url=f"/files/{project_id}/v{n}_enclosure.stl", description="Moulded parts (DFM) — mesh for 3D printing", size_bytes=size(stems["stl"])),
        CadFile(format="glb", url=f"/files/{project_id}/v{n}_enclosure.glb", description="Moulded parts (DFM) — viewer model", size_bytes=size(stems["glb"])),
    ]
    ensure_strap(spec, params, family, d.material, d.finish)
    return facts


# --------------------------------------------------------------------------- downstream (DFM, costs, shortlist)


def refresh_dfm(project_id: str, n: int, arts: dict, family: str, ai_pending: bool) -> DFMArtifact:
    from api.dfm.measure import measure

    brief, spec, prev = arts[1], arts[3], arts.get(4)
    step = project_dir(project_id) / f"v{n}_enclosure.step"
    moulded = next((p for p in spec.parts if p.process_hint in (ProcessType.injection_molding, "injection_molding")), None)
    d = P.chosen(arts.get(2))
    if d is not None and family_mode.is_solid(d):  # W21: surfboard / furniture / PV array — no moulded-shell checks
        from api.studio.cad import solid_measured

        measured = solid_measured(d, spec.parts[0].id if spec.parts else None)
    else:
        measured = measure(step, (0, 0, 1), finish=moulded.finish if moulded else None,
                           material=moulded.material if moulded else None, part_id=moulded.id if moulded else None)
    ai = [i for i in (prev.issues if prev else []) if str(getattr(i.method, "value", i.method)) == "ai_reviewed"]
    issues = [x.model_copy(update={"id": f"m{i}"}) for i, x in enumerate(measured, 1)]
    issues += [x.model_copy(update={"id": f"a{i}"}) for i, x in enumerate(ai, 1)]
    order = {"critical": 0, "major": 1, "minor": 2}
    issues.sort(key=lambda x: (order.get(str(getattr(x.severity, "value", x.severity)), 3), str(getattr(x.method, "value", x.method)) != "measured"))
    certs = P.refresh_certs(brief, spec, prev.certifications if prev else [], family)
    risks = component_risk(match_bom(spec.bom))
    assumptions = [a for a in (prev.assumptions if prev else []) if not a.id.startswith("a4_studio")]
    assumptions.append(Assumption(id="a4_studio", label="estimate", stage=4, text=(
        f"Studio v{n}: measured checks re-run on the rebuilt STEP; certifications re-mapped by rule"
        + ("; AI-reviewed issues are the previous version's until the background review finishes" if ai_pending and ai else "")
    )))
    return DFMArtifact(project_id=project_id, generated_by=prev.generated_by if prev and ai else "code",
                       assumptions=assumptions, issues=issues, component_risks=risks, certifications=certs)


def stub_pack(project_id: str, arts: dict) -> FactoryPack:
    """What stage 7 reads from the Factory Pack (id + parts), without assembling it (the CN translation is an LLM
    call; "Make it" assembles the real pack before matching)."""
    spec = arts[3]
    return FactoryPack.model_construct(id=f"fp_{project_id}_studio", project_id=project_id,
                                       spec=StructuredSpec.model_construct(parts=spec.parts), target_quantities=[],
                                       cost_estimate=arts[5].tiers if arts.get(5) else [])


def compute_costs(project, arts: dict):
    from api.costs.engine import build_costs

    ctx = StageContext(project=project, stage=5, inputs={}, artifacts={k: v for k, v in arts.items() if k != 5})
    costs = build_costs(ctx)
    costs.project_id = project.id
    return costs


def compute_match(project, arts: dict, use_plan: bool = True):
    from api.agents.negotiation.matching import match

    a = {k: v for k, v in arts.items() if use_plan or k != 6}
    m = match(StageContext(project=project, stage=7, inputs={}, artifacts=a, factory_pack=stub_pack(project.id, arts)))
    m.project_id = project.id
    return m


# --------------------------------------------------------------------------- apply


def _covered(bom: list[BOMItem], request: str, out: "Applied", quiet: bool = False) -> bool:
    """W21c: True when a BOM line already provides the requested capability (then nothing is added). A PPG sensor asked
    to do SpO2 that cannot (no red + IR) is upgraded in place to a MAX30102 instead of adding a second PPG."""
    cap = P.capability(request)
    if cap is None:
        return False
    have = P.provider(bom, cap)
    if have is None:
        return False
    if cap == "ppg" and P.SPO2.search(request) and not P.SPO2.search(f"{have.part} {have.manufacturer_pn or ''} {have.description or ''}"):
        before = have.part
        have.part, have.manufacturer_pn = "Optical heart-rate / SpO2 sensor (PPG, red + IR, MAX30102)", "MAX30102EFD+T"
        have.lcsc_pn, have.unit_cost_est = None, None  # re-matched to the LCSC snapshot below / in stage 5
        have.description = f"Replaces '{before}': red + IR LEDs needed for SpO2"
        out.notes.append(VersionChange(area="component", label="Component upgraded", before=before, after=have.part, label_kind=Label.estimate))
        out.rematch = True
        return True
    if not quiet and not any("Uses the existing" in (n.after or "") for n in out.notes):
        out.notes.append(_note(f"Uses the existing '{have.part}' — it already provides {'SpO2 / heart rate' if cap == 'ppg' else cap}; "
                               "no second part added", "component"))
    return True


def _clampnote(label: str, asked: float, got: float, family: str) -> VersionChange | None:
    if abs(asked - got) < 0.05:
        return None
    return _note(f"{label} {asked:g} mm is outside the plausible range for a {P.FAMILY_SHAPE.get(family, family).lower()}: "
                 f"built at {got:g} mm", area="dimensions")


def apply(project, n: int, patch: RefinePatch, before: dict, cad_res: dict | None = None) -> Applied:
    """`cad_res` (W21): the AI CAD edit for a geometric change (refine_cad result), computed before the commit."""
    from api.studio import cad as studio_cad

    arts = {k: v.model_copy(deep=True) for k, v in before.items()}
    brief, design, spec = arts.get(1), arts.get(2), arts.get(3)
    if brief is None or design is None or spec is None:
        raise LookupError("the product has no brief, design or spec yet")
    out = Applied(arts=arts)
    d = P.chosen(design)
    fam = family_mode.family_of(d)  # W21 product family (board, drone…) or None (W2 / W17 enclosure families)
    fam_asked: dict[str, float] = {}
    material_op = any(o.op == "set_material" for o in patch.ops)
    prev_ai, _ = studio_cad.split(spec.cad_files)
    params = normalize(d.cad_parameters or {})
    family = old_family = P.family_of(params)
    base_fin, cname, chex = P.split_finish(d.finish)
    mkey = P.material_key(d.material)
    geometry = False
    new_items: list[BOMItem] = []
    features_added: list[str] = []
    battery_ops: list = []  # W21b: (factor, capacity) battery upgrades, applied to the BOM after the other ops

    for op in sorted(patch.ops, key=lambda o: 0 if o.op == "set_shape_family" else 1):
        kind = op.op
        if fam and kind == "set_shape_family":
            continue  # a product family keeps its family: the form change goes to the AI CAD (regenerate_geometry)
        if fam and kind == "set_dimensions":
            fam_asked.update({ax: v for ax, v in (("length", op.length), ("width", op.width), ("height", op.height)) if v and v > 0})
            continue
        if kind == "upgrade_battery":
            battery_ops.append((op.factor, op.capacity_mah))
            continue
        if kind == "note_requirement" and battery_mod.wants_battery(op.text):  # backstop: a runtime wish is a battery change
            battery_ops.append((None, None))
            continue
        if kind == "regenerate_geometry":
            if cad_res is None:
                t = op.instruction.strip()[:200]
                why = "AI CAD is off for this project" if studio_cad.current_model(spec) is None else "the AI CAD edit did not run"
                out.notes.append(_note(f"Geometry change noted, not modelled ({why}): {t}", "shape"))
                if t and t not in brief.constraints:
                    brief.constraints.append(t)
            continue
        if kind == "set_shape_family" and op.family != family:
            family, params, geometry = op.family, family_params(op.family, brief), True
            out.replan = True
        elif kind == "set_dimensions":
            names = P.AXIS_NAMES.get(family, ("Length", "Width", "Height"))
            raw = dict(params)
            asked = {ax: v for ax, v in (("length", op.length), ("width", op.width), ("height", op.height)) if v is not None and v > 0}
            if family in ("ring", "puck") and "width" in asked and "length" not in asked:
                asked["length"] = asked.pop("width")
            raw.update(asked)
            if family in ("ring", "puck"):
                raw["width"] = raw["length"]
            new = normalize(raw)
            for ax, v in asked.items():
                if (c := _clampnote(names[("length", "width", "height").index(ax)], v, new[ax], family)) is not None:
                    out.notes.append(c)
            if new != params:
                params, geometry = new, True
        elif kind == "set_color":
            hx = P.valid_hex(op.hex, op.name)
            if hx is None:
                out.notes.append(_note(f"Colour '{op.name}' not understood (no valid #RRGGBB): kept {cname or 'the current colour'}", "color"))
            else:
                cname, chex = (op.name.strip() or "Custom")[:30], hx
        elif kind == "set_material":
            mkey = op.material
            base_fin = (op.finish or P.MATERIALS[mkey][2]).strip()[:60]
            out.replan = out.ai_review = True
        elif kind == "add_feature":
            name = op.name.strip()
            if name and name.lower() not in {f.lower() for f in brief.key_features}:
                brief.key_features.append(name)
                features_added.append(f"{name} {op.description}")
        elif kind == "add_component":
            cat = op.category
            if cat == "electronic" and _covered(spec.bom + new_items, f"{op.part} {op.rationale}", out):
                continue
            kp = P.known_part(f"{op.part} {op.rationale}") if cat == "electronic" else None
            pn = op.manufacturer_pn or (kp[1] if kp else None)
            item = BOMItem(id=P.next_bom_id(spec.bom + new_items, cat), part=op.part.strip()[:80], category=BOMCategory(cat),
                           qty=max(1.0, min(float(op.qty), 50.0)), description=op.rationale.strip() or None, manufacturer_pn=pn)
            new_items.append(item)
        elif kind == "remove_component":
            hit = next((b for b in spec.bom if b.id == op.bom_item_id), None)
            if hit is None:
                out.notes.append(_note(f"No BOM line '{op.bom_item_id}' to remove", "component"))
            elif "shell" in hit.part.lower():
                out.notes.append(_note(f"'{hit.part}' is part of the moulded enclosure and stays in the BOM", "component"))
            else:
                spec.bom = [b for b in spec.bom if b.id != hit.id]
                spec.electronics_blocks = [b for b in spec.electronics_blocks if b.name != hit.part[:40]]
                out.ai_review = True
        elif kind == "set_target_price":
            v = max(1.0, min(float(op.value), 100000.0))
            brief.target_retail_price = LabeledValue(value=v, unit=op.currency, label="estimate",
                                                     source_or_assumption=f"Founder target retail price, set in Studio (version {n})")
        elif kind == "set_markets":
            from api.agents.brief import _parse_markets

            codes = _parse_markets(" ".join(op.markets)) or [m.strip().upper()[:12] for m in op.markets if m.strip()]
            if codes:
                brief.target_markets = codes
        elif kind == "note_requirement":
            t = op.text.strip()[:200]
            if t and t not in brief.constraints:
                brief.constraints.append(t)

    for factor, capacity in battery_ops[:1]:
        ch, why = battery_mod.upgrade(project, arts, factor=factor, capacity=capacity)
        if ch is not None:
            out.notes.append(ch)
            out.battery = True
            out.ai_review = True
        elif why:
            out.notes.append(_note(why, "component"))

    # a capability without its part: add the known catalogue part (deterministic backstop)
    for text in features_added:
        for kp in P.known_parts(text):  # every capability of the feature ("SpO2 and skin temperature" → PPG + temperature)
            if _covered(spec.bom + new_items, f"{kp[0]} {text}", out, quiet=True):
                continue
            new_items.append(BOMItem(id=P.next_bom_id(spec.bom + new_items, "electronic"), part=kp[0], category=BOMCategory.electronic,
                                     qty=1, description=kp[2], manufacturer_pn=kp[1]))

    if out.rematch:
        by_id = {m.id: m for m in match_bom([b for b in spec.bom if b.lcsc_pn is None and b.manufacturer_pn == "MAX30102EFD+T"])}
        spec.bom = [by_id.get(b.id, b) for b in spec.bom]
        out.ai_review = True
    if new_items:
        matched = match_bom([i for i in new_items if i.category == BOMCategory.electronic or i.category == "electronic"])
        by_id = {m.id: m for m in matched}
        ctrl = next((b.id for b in spec.electronics_blocks
                     if any(k in b.name.lower() for k in ("mcu", "soc", "ble", "nrf", "esp32", "controller"))), None)
        for it in new_items:
            it = by_id.get(it.id, it)
            spec.bom.append(it)
            if it.category in (BOMCategory.electronic, "electronic"):
                bid = f"b{max([int(b.id[1:]) for b in spec.electronics_blocks if b.id[1:].isdigit()], default=0) + 1}"
                spec.electronics_blocks.append(ElectronicsBlock(id=bid, name=it.part[:40], function=(it.description or "Added in Studio")[:80]))
                if ctrl:
                    spec.electronics_edges.append(ElectronicsEdge(source=ctrl, target=bid, signal="I²C / GPIO"))
        out.ai_review = True

    # direction look (colour / material / finish / shape)
    old_visual = (d.material, d.finish, d.shape, dict(d.cad_parameters or {}))
    old_look = (d.material, d.finish)
    if not fam or material_op:  # a product family keeps its own material text unless the founder changes it
        d.material = P.MATERIALS[mkey][0]
    d.finish = P.join_finish(base_fin, cname, chex)
    if not fam:
        d.shape = P.FAMILY_SHAPE.get(family, d.shape)
        if family != old_family:
            d.description = P.FAMILY_TEXT.get(family, d.description)
    if fam:
        out.notes += [_note(t, "dimensions") for t in studio_cad.rebuild_family(project.id, n, design, spec, fam_asked)]
        geometry = geometry or bool(fam_asked)
    else:
        rebuild_cad(project.id, n, design, spec, brief, params, family)
    # AI CAD model: the new edit, else the previous version's (recoloured when colour / material changed)
    new_ai = studio_cad.ai_entries(project.id, cad_res) if cad_res else []
    if cad_res and cad_res.get("status") == "fallback":
        out.notes.append(_note("The AI could not apply this change to the CAD program: the previous model is kept "
                               "(parametric changes above are applied)", "shape"))
        new_ai = []
    if new_ai and any(f.format == "glb" for f in new_ai):
        studio_cad.attach(spec, new_ai)
        geometry = True
    else:
        studio_cad.attach(spec, prev_ai)
        if prev_ai and old_look != (d.material, d.finish):
            studio_cad.recolour(project.id, n, spec, d)
    out.render = old_visual != (d.material, d.finish, d.shape, dict(d.cad_parameters or {}))
    out.ai_review = out.ai_review or geometry
    if out.render:
        d.render_url = None  # the new concept render is patched in when it arrives (never show the old look)
    for a in design.assumptions:
        if a.id == "a2_studio":
            design.assumptions.remove(a)
            break
    design.assumptions.append(Assumption(id="a2_studio", label="estimate", stage=2,
                                         text=f"Direction {d.id} refined in Studio (version {n}); dimensions are design parameters, the spec measures the built CAD"))

    arts[4] = refresh_dfm(project.id, n, arts, family, out.ai_review)
    arts[5] = compute_costs(project, arts)
    if out.replan and 6 in arts:
        del arts[6]
        out.drop.add(6)
    try:
        arts[7] = compute_match(project, arts)
    except Exception as e:  # noqa: BLE001 — keep the previous shortlist, say so
        log.warning("studio shortlist failed: %s", e)
        out.notes.append(_note(f"Factory shortlist kept from the previous version ({type(e).__name__})"))
    return out


__all__ = ["apply", "Applied", "rebuild_cad", "ensure_strap", "family_params", "render_extra", "compute_costs",
           "compute_match", "stub_pack", "refresh_dfm"]
