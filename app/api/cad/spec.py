"""Stage 3 — CAD + spec. Owner: W2.

Direction = inputs["direction_id"], else DesignArtifact.chosen_direction_id, else the first direction.
The enclosure is built with build123d (cached by params hash) and copied to
api/data/files/<project_id>/enclosure.{step,stl,glb}. Overall dimensions and part envelopes come from the
re-imported STEP (Measured); weight = measured volume × stated density (Estimate). BOM + electronics block
diagram: LLM ("fast") → else the project's cached example BOM → else a generic template from the brief.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from api.cad import family_mode
from api.cad.build import FAMILY_CODES, build_direction, normalize, project_dir, shape_facts
from api.cad.look import apply_materials, look_for
from api.stages.registry import StageContext, stage_handler
from contracts.artifacts import (
    Assumption,
    BOMCategory,
    BOMItem,
    CadFile,
    Dimensions,
    ElectronicsBlock,
    ElectronicsEdge,
    LabeledValue,
    ProcessType,
    SpecArtifact,
    SpecPart,
)

log = logging.getLogger("cad.spec")

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


# --------------------------------------------------------------------------- direction → CAD params


def pick_direction(ctx: StageContext, design):
    wanted = (ctx.inputs or {}).get("direction_id") or design.chosen_direction_id
    for d in design.directions:
        if d.id == wanted:
            return d
    return design.directions[0]


def params_for(direction) -> dict[str, float]:
    """Use the direction's cad_parameters if they are ours, else derive a rounded box from its dimensions."""
    cp = direction.cad_parameters or {}
    if {"family", "length", "width", "height"} <= set(cp):
        return normalize(cp)
    L, W, H = direction.dimensions.length.value, direction.dimensions.width.value, direction.dimensions.height.value
    shape = f"{direction.shape} {direction.name}".lower()
    fam = 1 if any(k in shape for k in ("puck", "disc", "cylind", "round")) else (2 if H < 0.25 * min(L, W) else 0)
    return normalize({"family": fam, "length": L, "width": W, "height": H, "fillet": min(L, W) * 0.12,
                      "edge_fillet": 3.0, "wall": cp.get("wall", 2.0)})


def density_for(direction) -> tuple[float, str]:
    if "density_g_cm3" in (direction.cad_parameters or {}):
        d = direction.cad_parameters["density_g_cm3"]
    else:
        d = 2.70 if "alumin" in direction.material.lower() else 1.15
    name = "aluminium 6063" if d > 2 else "PC/ABS"
    return d, name


# --------------------------------------------------------------------------- BOM + electronics


class BomLine(BaseModel):
    id: str = Field(description="e1.. electronic, m1.. mechanical, k1.. packaging")
    part: str
    category: BOMCategory
    qty: float
    description: str | None = None
    manufacturer_pn: str | None = None


class BomDraft(BaseModel):
    bom: list[BomLine] = Field(min_length=4, max_length=30)
    electronics_blocks: list[ElectronicsBlock] = Field(min_length=2, max_length=12)
    electronics_edges: list[ElectronicsEdge] = Field(default_factory=list, max_length=20)


BOM_PROMPT = """Product: {name} — {one_liner}
Category: {category}. Key features: {features}. Battery: {battery}. Wireless: {wireless}.
{enclosure}

Write the bill of materials for one finished unit: electronic parts (use common LCSC/JLCPCB-available generic parts,
give a manufacturer part number when you are confident), mechanical parts ({mech}) and packaging — at most 18 lines, grouping passives. If the product has no electronics (no battery, no
wireless, nothing powered), list NO electronic lines at all. Also give the block diagram (blocks b1.. and edges between
block ids with the signal): electronic blocks, or the main functional/mechanical sub-assemblies for a non-electronic
product."""


BOM_TIMEOUT_S = 20.0  # stage 3 margin: a slow BOM call falls back to the example/template BOM (partial live result)
BOM_MAX_TOKENS = 2000


SHELL_MECH = 'include the two shells, named exactly "Top shell" and "Bottom shell", and the screws'


def _bom_llm(brief, p: dict[str, float], material: str, product: str | None = None) -> tuple[BomDraft, str]:
    """`product` (W21 family directions): what was designed, replacing the two-shell enclosure paragraph."""
    from api.llm import complete_json, model_for

    w = p["wall"]
    enclosure = (f"Enclosure (already designed): two injection-moulded {material} shells, outer {p['length']:.0f} × "
                 f"{p['width']:.0f} × {p['height']:.0f} mm, wall {w} mm, 4 × M2.5 screws. Internal cavity ≈ "
                 f"{p['length'] - 2 * w:.0f} × {p['width'] - 2 * w:.0f} × {p['height'] - 2 * w:.0f} mm.")
    prompt = BOM_PROMPT.format(
        name=brief.product_name, one_liner=brief.one_liner, category=brief.category,
        features="; ".join(brief.key_features), battery=brief.has_battery, wireless=", ".join(brief.wireless) or "none",
        enclosure=product or enclosure,
        mech="the main structural parts, fasteners and consumables of this product" if product and "not a moulded" in product else SHELL_MECH,
    )
    draft = complete_json("fast", prompt, BomDraft, max_tokens=BOM_MAX_TOKENS, timeout_s=BOM_TIMEOUT_S)
    ids = {b.id for b in draft.electronics_blocks}
    draft.electronics_edges = [e for e in draft.electronics_edges if e.source in ids and e.target in ids]
    return draft, f"llm:{model_for('fast')}"


def _bom_from_example(example: str | None):
    if not example:
        return None
    try:
        from api.stages.runner import load_fixture

        if not (FIXTURES_DIR / example / "03_cad_spec.json").exists():
            return None
        fx = load_fixture(example, 3)
        return BomDraft.model_construct(bom=fx.bom, electronics_blocks=fx.electronics_blocks,
                                        electronics_edges=fx.electronics_edges), fx
    except Exception:  # noqa: BLE001
        return None


def _est(v: float, why: str) -> LabeledValue:
    return LabeledValue(value=v, unit="USD", label="estimate", source_or_assumption=why)


def bom_template(brief, material: str) -> BomDraft:
    wireless = [w.lower() for w in (brief.wireless or [])]
    radio = "wi-fi" in " ".join(wireless) or "wifi" in " ".join(wireless)
    ble = any("ble" in w or "bluetooth" in w for w in wireless)
    mcu = ("ESP32-C3 Wi-Fi/BLE module", "ESP32-C3-MINI-1") if radio else (
        ("BLE SoC module nRF52832", "nRF52832-QFAA") if ble else ("8-bit MCU, SOP-8", "PY32F002AF15P6TU"))
    feature = brief.key_features[0] if brief.key_features else "Main function"
    blocks = [ElectronicsBlock(id="b1", name="USB-C input", function="5 V power / charging input")]
    edges: list[ElectronicsEdge] = []
    items = [BOMItem(id="e1", part="USB-C receptacle 16P SMD", category=BOMCategory.electronic, qty=1,
                     unit_cost_est=_est(0.12, "Generic USB-C 16P, template estimate"))]
    if brief.has_battery:
        items += [
            BOMItem(id="e2", part="Li-ion charger IC TP4056 (ESOP-8)", category=BOMCategory.electronic, qty=1,
                    manufacturer_pn="TP4056", unit_cost_est=_est(0.06, "Template estimate")),
            BOMItem(id="e3", part="Li-Po cell 3.7 V with protection PCM", category=BOMCategory.electronic, qty=1,
                    unit_cost_est=_est(2.5, "Template estimate, capacity sized to cavity")),
        ]
        blocks += [ElectronicsBlock(id="b2", name="Charger (TP4056)", function="CC/CV Li-ion charging"),
                   ElectronicsBlock(id="b3", name="Battery", function="Energy storage")]
        edges += [ElectronicsEdge(source="b1", target="b2", signal="VBUS 5 V"),
                  ElectronicsEdge(source="b2", target="b3", signal="Charge 4.2 V"),
                  ElectronicsEdge(source="b3", target="b4", signal="VBAT → 3.3 V LDO")]
    else:
        edges.append(ElectronicsEdge(source="b1", target="b4", signal="5 V → 3.3 V LDO"))
    items += [
        BOMItem(id="e4", part=mcu[0], category=BOMCategory.electronic, qty=1, manufacturer_pn=mcu[1],
                unit_cost_est=_est(1.8 if (radio or ble) else 0.15, "Template estimate")),
        BOMItem(id="e5", part="LDO 3.3 V 300 mA SOT-23-5", category=BOMCategory.electronic, qty=1,
                manufacturer_pn="ME6211C33M5G-N", unit_cost_est=_est(0.05, "Template estimate")),
        BOMItem(id="e6", part=f"Function block: {feature}", category=BOMCategory.electronic, qty=1,
                unit_cost_est=_est(1.5, "Placeholder for the product-specific sensor/actuator")),
        BOMItem(id="e7", part="Main PCB 2-layer + passives, assembled", category=BOMCategory.electronic, qty=1,
                unit_cost_est=_est(1.2, "PCB + SMT assembly, template estimate")),
        BOMItem(id="m1", part=f"Top shell, {material}", category=BOMCategory.mechanical, qty=1,
                unit_cost_est=_est(0.9, "Injection moulded, template estimate")),
        BOMItem(id="m2", part=f"Bottom shell, {material}", category=BOMCategory.mechanical, qty=1,
                unit_cost_est=_est(0.9, "Injection moulded, template estimate")),
        BOMItem(id="m3", part="Self-tapping screw M2.5 × 6 (PT thread)", category=BOMCategory.mechanical, qty=4,
                unit_cost_est=_est(0.01, "Template estimate")),
        BOMItem(id="k1", part="Retail box + insert", category=BOMCategory.packaging, qty=1,
                unit_cost_est=_est(0.6, "Template estimate")),
        BOMItem(id="k2", part="USB-C cable 1 m", category=BOMCategory.packaging, qty=1,
                unit_cost_est=_est(0.5, "Template estimate")),
    ]
    blocks += [ElectronicsBlock(id="b4", name=mcu[0].split(",")[0], function="Control" + (" + radio" if radio or ble else "")),
               ElectronicsBlock(id="b5", name=feature[:40], function="Product function")]
    edges.append(ElectronicsEdge(source="b4", target="b5", signal="GPIO / I²C / PWM"))
    return BomDraft.model_construct(bom=items, electronics_blocks=blocks, electronics_edges=edges)


def _to_items(lines) -> list[BOMItem]:
    out = []
    for x in lines:
        if isinstance(x, BOMItem):
            out.append(x)
        else:
            out.append(BOMItem(id=x.id, part=x.part, category=x.category, qty=x.qty, description=x.description,
                               manufacturer_pn=x.manufacturer_pn))
    return out


# --------------------------------------------------------------------------- handler


def _mm(v: float, check: str) -> LabeledValue:
    return LabeledValue(value=round(v, 2), unit="mm", label="measured", source_or_assumption=check)


def _dims(size, check: str) -> Dimensions:
    return Dimensions(length=_mm(size[0], check), width=_mm(size[1], check), height=_mm(size[2], check))


def _full_product(direction) -> CadFile | None:
    """The chosen direction's full-product GLB (shells + visible parts, materials) — first GLB = the viewer default."""
    from api.cad.files import resolve_file

    parts = (direction.glb_url or "").strip("/").split("/")
    if len(parts) != 3 or parts[0] != "files" or not parts[2].endswith(".glb"):
        return None
    path = resolve_file(parts[1], parts[2])
    if path is None:
        return None
    return CadFile(format="glb", url=direction.glb_url, description="Full product — materials", size_bytes=path.stat().st_size)


@stage_handler(3)
def run(ctx: StageContext) -> SpecArtifact:
    brief, design = ctx.artifact(1), ctx.artifact(2)
    if design is None or brief is None:
        raise LookupError("stage 3 needs the brief (1) and the design directions (2)")
    direction = pick_direction(ctx, design)
    params = params_for(direction)
    density, mat_name = density_for(direction)
    pid = ctx.project.id
    fam = family_mode.family_of(direction)
    solid = fam in family_mode.SOLID
    bbox_check = "Bounding box of the built STEP (build123d/OCCT)"
    product = None  # measured facts of the full product (family directions)

    if solid:  # W21: board / furniture / PV array — the product itself is the CAD (no moulded enclosure)
        res = family_mode.export_product(pid, direction, "enclosure", context=False)
        files, product = res["files"], res["measured"]
        facts = {"size": tuple(product["bbox_mm"]), "volume_mm3": product["volume_mm3"], "solids": []}
        weight = family_mode.solid_weight(fam, product)
        assumptions = [
            Assumption(id="a3_1", label="estimate", stage=3, text=f"Weight from the measured solid volume × per-part densities ({family_mode.DENSITY_NOTE[fam]})"),
            Assumption(id="a3_2", label="estimate", stage=3, text=f"Direction {direction.id} ('{direction.name}'): solid product from the '{fam}' family — no moulded enclosure; enclosure.* files are the product itself"),
        ]
    else:
        files = build_direction(params, project_dir(pid), name="enclosure")
        try:  # viewer colours = the direction's material / finish (geometry untouched)
            apply_materials(files["glb"], look_for(direction.material, direction.finish))
        except Exception as e:  # noqa: BLE001 — a grey model is still a valid model
            log.info("enclosure materials skipped: %s", e)
        facts = shape_facts(files["step"])
        vol_cm3 = facts["volume_mm3"] / 1000.0
        weight = LabeledValue(value=round(vol_cm3 * density, 1), unit="g", label="estimate",
                              source_or_assumption=f"Enclosure volume {vol_cm3:.1f} cm³ (measured) × {mat_name} {density} g/cm³; electronics and battery not included")
        assumptions = [
            Assumption(id="a3_1", label="estimate", stage=3, text=f"{mat_name} density {density} g/cm³ for the weight estimate"),
            Assumption(id="a3_2", label="estimate", stage=3, text=f"Direction {direction.id} ('{direction.name}') built as a two-shell enclosure, wall {params['wall']} mm, draft {params['draft_deg']}°"),
        ]
        if fam:
            product = family_mode.measured_parts(direction)
            assumptions[1] = Assumption(id="a3_2", label="estimate", stage=3, text=(
                f"Direction {direction.id} ('{direction.name}'): full product from the '{fam}' family (overall size measured on it); "
                f"its main moulded housing is modelled as a two-shell enclosure {params['length']:.0f} × {params['width']:.0f} × "
                f"{params['height']:.0f} mm, wall {params['wall']} mm, draft {params['draft_deg']}° (DFM, weight)"))

    generated_by = "code"
    product_text = None
    if fam:
        bb = product["bbox_mm"]
        product_text = (f"Product (already designed, {family_mode.INFO[fam]['shape']}): {family_mode.INFO[fam]['desc']} Overall "
                        f"{bb[0]:.0f} × {bb[1]:.0f} × {bb[2]:.0f} mm, {direction.material}."
                        + (" It is not a moulded enclosure." if solid else
                           f" Main moulded housing: two {direction.material} shells, about {params['length']:.0f} × {params['width']:.0f} × {params['height']:.0f} mm."))
    try:
        from api.stages.runner import call_with_timeout

        # hard cap on the whole call (incl. its validation retry) so stage 3 stays well under 30 s
        extra = (product_text,) if product_text else ()  # (keeps the 3-argument call for W2 directions)
        draft, generated_by = call_with_timeout(_bom_llm, brief, params, direction.material, *extra, timeout=BOM_TIMEOUT_S)
    except Exception as e:  # noqa: BLE001 — template path is a designed alternative
        log.info("stage 3 BOM LLM unavailable: %s", e)
        ex = _bom_from_example(ctx.project.example)
        if solid:
            draft = BomDraft.model_construct(bom=family_mode.solid_bom(fam, product, brief), electronics_blocks=[], electronics_edges=[])
            assumptions.append(Assumption(id="a3_3", label="estimate", stage=3,
                                          text=f"BOM from the '{fam}' category template (LLM unavailable: {type(e).__name__})"))
        elif ex is not None:
            draft = ex[0]
            assumptions.append(Assumption(id="a3_3", label="estimate", stage=3,
                                          text=f"BOM and block diagram from cached example '{ctx.project.example}' (LLM unavailable: {type(e).__name__})"))
        else:
            draft = bom_template(brief, direction.material)
            assumptions.append(Assumption(id="a3_3", label="estimate", stage=3,
                                          text=f"BOM from the generic template (LLM unavailable: {type(e).__name__})"))

    pasted = list(getattr(brief, "pasted_bom", None) or [])
    if pasted:  # prototype mode: the founder's BOM is the source of truth; the draft only adds what it lacks
        has = {str(getattr(b.category, "value", b.category)) for b in pasted}
        extra = [b for b in draft.bom if str(getattr(b.category, "value", b.category)) not in has]
        draft = BomDraft.model_construct(bom=pasted + extra, electronics_blocks=draft.electronics_blocks,
                                         electronics_edges=draft.electronics_edges)
        assumptions.append(Assumption(id="a3_5", label="estimate", stage=3,
                                      text=f"BOM = the {len(pasted)} lines of the pasted prototype BOM" + (f" + {len(extra)} proposed lines for missing categories" if extra else "")))
    wall = LabeledValue(value=params["wall"], unit="mm", label="estimate",
                        source_or_assumption="Design parameter (nominal wall); measured in DFM stage 4")
    if solid:
        return _solid_spec(pid, brief, direction, fam, product, files, facts, weight, assumptions, draft, generated_by, bbox_check)
    solids = facts["solids"]
    process = ProcessType.cnc if density > 2 else ProcessType.injection_molding
    parts = []
    names = ["Bottom shell", "Top shell"]
    for i, s in enumerate(solids[:2]):
        parts.append(SpecPart(id=f"p{i + 1}", name=names[i], material=direction.material, finish=direction.finish,
                              process_hint=process, tolerance="±0.1 mm on mating faces and boss pilots",
                              dimensions=_dims(s["size"], bbox_check + ", this part"), wall_thickness=wall))
    w = params["wall"]
    electronic = any(str(getattr(b.category, "value", b.category)) == "electronic" for b in draft.bom)
    pcb_est = lambda v, what: LabeledValue(value=round(max(v, 5.0) if what != "thickness" else v, 1), unit="mm", label="estimate", source_or_assumption=f"PCB {what}: fits the inner cavity with 1 mm clearance")  # noqa: E731
    if electronic:  # no PCB (and no electronics diagram) for a purely mechanical product
        parts.append(SpecPart(id="p3", name="Main PCB assembly", material="FR-4 1.6 mm", finish="HASL lead-free, green mask",
                              process_hint=ProcessType.pcba, tolerance="±0.2 mm outline",
                              dimensions=Dimensions(length=pcb_est(params["length"] * (0.7 if params["family"] == 1 else 1) - 2 * w - 2 - 12, "length"),
                                                    width=pcb_est(params["width"] * (0.7 if params["family"] == 1 else 1) - 2 * w - 2 - 12, "width"),
                                                    height=pcb_est(1.6, "thickness"))))
    else:
        assumptions.append(Assumption(id="a3_4", label="estimate", stage=3,
                                      text="No electronic BOM line: no PCB part; the block diagram lists functional sub-assemblies"))
    parts.append(SpecPart(id="p4", name="Screws M2.5 × 6 self-tapping", material="Steel", finish="Black zinc",
                          process_hint=ProcessType.other, quantity=int(params["boss_count"]) or 4))

    size_of = lambda k: files[k].stat().st_size  # noqa: E731
    extra = []
    if fam:  # W21: the full product (all parts of the family CAD) as STEP, next to its viewer GLB
        from api.cad.files import resolve_file

        if (path := resolve_file(pid, f"{direction.id}.step")) is not None:
            extra.append(CadFile(format="step", url=f"/files/{pid}/{direction.id}.step", description="Full product — all parts, STEP AP214",
                                 size_bytes=path.stat().st_size))
    overall = _dims(product["bbox_mm"], "Bounding box of the full product (family CAD, build123d/OCCT)") if fam else _dims(facts["size"], bbox_check)
    cad_files = [f for f in [_full_product(direction)] if f is not None] + [
        CadFile(format="step", url=f"/files/{pid}/enclosure.step", description="Moulded parts (DFM) — both shells, STEP AP214", size_bytes=size_of("step")),
        CadFile(format="stl", url=f"/files/{pid}/enclosure.stl", description="Moulded parts (DFM) — mesh for 3D printing", size_bytes=size_of("stl")),
        CadFile(format="glb", url=f"/files/{pid}/enclosure.glb", description="Moulded parts (DFM) — viewer model", size_bytes=size_of("glb")),
    ] + extra
    return SpecArtifact(
        project_id=pid, generated_by=generated_by, assumptions=assumptions, product_name=brief.product_name,
        direction_id=direction.id, overall_dimensions=overall, weight=weight, parts=parts,
        electronics_blocks=list(draft.electronics_blocks), electronics_edges=list(draft.electronics_edges),
        bom=_to_items(draft.bom),
        tolerances=["General ISO 2768-m", "Shell mating faces ±0.1 mm", "Boss pilot Ø2.2 +0.05/0 mm",
                    "Split-line step ≤ 0.1 mm"],
        cad_files=cad_files,
    )


def _solid_spec(pid, brief, direction, fam, product, files, facts, weight, assumptions, draft, generated_by, bbox_check) -> SpecArtifact:
    """Stage 3 of a solid product (W21): parts grouped from the family CAD, the product files, no PCB / shell screws."""
    size_of = lambda k: files[k].stat().st_size  # noqa: E731
    parts = family_mode.spec_parts(fam, product)
    tolerances = {"board": ["Outline ±2 mm", "Thickness ±1 mm", "Rocker ±3 mm at nose / tail", "Fin box position ±1 mm"],
                  "furniture": ["General ISO 2768-c", "CNC-routed panels ±0.3 mm", "Hole positions for fittings ±0.2 mm",
                                "All accessible edges rounded r ≥ 2 mm"],
                  "solar_array": ["Rail alignment ±5 mm", "Module gap 20 mm ±3 mm", "Roof-edge margin ≥ 450 mm"]}[fam]
    cad_files = [f for f in [_full_product(direction)] if f is not None] + [
        CadFile(format="step", url=f"/files/{pid}/enclosure.step", description="Product — all parts (solid bodies), STEP AP214", size_bytes=size_of("step")),
        CadFile(format="stl", url=f"/files/{pid}/enclosure.stl", description="Product — mesh", size_bytes=size_of("stl")),
        CadFile(format="glb", url=f"/files/{pid}/enclosure.glb", description="Product — viewer model", size_bytes=size_of("glb")),
    ]
    return SpecArtifact(
        project_id=pid, generated_by=generated_by, assumptions=assumptions, product_name=brief.product_name,
        direction_id=direction.id, overall_dimensions=_dims(facts["size"], "Bounding box of the product (family CAD, build123d/OCCT)"),
        weight=weight, parts=parts, electronics_blocks=list(draft.electronics_blocks), electronics_edges=list(draft.electronics_edges),
        bom=_to_items(draft.bom), tolerances=tolerances, cad_files=cad_files)


__all__ = ["run", "params_for", "pick_direction", "bom_template", "FAMILY_CODES"]
