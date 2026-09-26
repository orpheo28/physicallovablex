"""Stage 5 — Investment. Deterministic cost engine (PRD §11). Owner: W3.

Python computes every number; the LLM at most proposes BOM lines (bom.py). Every figure is a LabeledValue.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from api.stages.registry import StageContext, stage_handler
from contracts.artifacts import (
    Assumption,
    BOMItem,
    CostLine,
    CostsArtifact,
    CostTier,
    LandedCostComponent,
    ProcessType,
    SpecPart,
    ToolingItem,
)

from . import freight, landed
from ._common import EXTENDED_NOTE, VTRUST_SOURCE, LCSC_SOURCE, SNAPSHOT_DATE, label_of, lcsc_source, lv, usd
from .bom import load_bom
from .lcsc import get_part, price_at, stock_of

DEFAULT_VOLUMES = [500, 2000, 10000]
DEFAULT_VF = 0.92
DEFAULT_REF = 2000
FX_TO_USD = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27}

LABOUR_RATE = 6.0  # USD/h all-in direct labour, Guangdong (assumption)
ASSEMBLY_BASE_MIN = 6.0
ASSEMBLY_MIN_PER_LINE = 0.6
FACTORY_OVERHEAD = 1.40  # factory overhead + margin on assembly labour
FACTORY_MARGIN = 0.15  # factory margin + scrap/yield loss on materials (BOM + packaging)
ZETAR = "Zetar Mold 2026 price list (vendor, medium confidence), https://zetarmold.com/injection-mold-price-list-2026"

DENSITY = {"pc/abs": 1.15, "abs": 1.05, "pc": 1.2, "polycarbonate": 1.2, "pp": 0.9, "pom": 1.41, "nylon": 1.14, "pa": 1.14,
           "aluminium": 2.7, "aluminum": 2.7, "steel": 7.85, "spcc": 7.85, "stainless": 8.0, "zinc": 6.6, "silicone": 1.15, "tpu": 1.2,
           "abs+pc": 1.15, "wood": 0.7, "bamboo": 0.7, "brass": 8.5}
PRICE_KG = {"pc/abs": 3.2, "abs": 2.2, "pc": 3.0, "polycarbonate": 3.0, "pp": 1.4, "pom": 2.8, "nylon": 3.5, "pa": 3.5,
            "aluminium": 3.5, "aluminum": 3.5, "steel": 1.0, "spcc": 1.0, "stainless": 3.0, "zinc": 3.0, "silicone": 5.0, "tpu": 4.0,
            "abs+pc": 3.2, "wood": 3.0, "bamboo": 3.0, "brass": 8.0}


def _material_key(material: str) -> str:
    low = material.lower()
    for k in sorted(DENSITY, key=len, reverse=True):
        if k in low:
            return k
    return "abs"


# --------------------------------------------------------------------------- spec-derived helpers


def has_battery(ctx: StageContext) -> bool:
    brief = ctx.artifact(1)
    if brief is not None:
        return bool(brief.has_battery)
    return bool(re.search(r"battery|li-?ion|lipo|rechargeable", ctx.project.prompt, re.I))


def product_weight_kg(ctx: StageContext) -> float:
    spec = ctx.artifact(3)
    if spec is not None and spec.weight.value > 0:
        g = spec.weight.value * (1000.0 if spec.weight.unit.lower() == "kg" else 1.0)
        return g / 1000.0
    return 0.35


_EAST_COAST = re.compile(r"east coast|new york|\bNYC?\b|new jersey|\bNJ\b|savannah|boston|miami|atlantic", re.I)


def product_volume_m3(ctx: StageContext) -> float:
    """Packed volume per unit: spec bounding box × packaging allowance (Estimate), else a small-consumer-product default."""
    spec = ctx.artifact(3)
    if spec is not None:
        d = spec.overall_dimensions
        f = {"mm": 1.0, "cm": 10.0, "m": 1000.0}.get(d.length.unit.lower(), 1.0)
        if min(d.length.value, d.width.value, d.height.value) > 0:
            return freight.packed_volume_m3(d.length.value * f, d.width.value * f, d.height.value * f)
    return 0.004


def freight_lane(ctx: StageContext) -> str:
    brief = ctx.artifact(1)
    text = " ".join([ctx.project.prompt or "", *(getattr(brief, "target_markets", None) or [])])
    return freight.EAST_COAST_LANE if _EAST_COAST.search(text) else freight.DEFAULT_LANE


def freight_opts(ctx: StageContext) -> dict:
    """Options shared by stage 5 and stage 11 so both landed costs are computed identically."""
    return {"weight_kg": product_weight_kg(ctx), "volume_m3": product_volume_m3(ctx), "lane": freight_lane(ctx)}


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]{3,}", s.lower()) if t not in {"the", "and", "with", "for", "pcb"}}


def _find_spec_part(item: BOMItem, parts: list[SpecPart]) -> SpecPart | None:
    it = _tokens(item.part.split(",")[0])
    best, score = None, 0
    for p in parts:
        s = len(it & _tokens(p.name))
        if s > score:
            best, score = p, s
    return best if score else None


def part_cost(p: SpecPart) -> tuple[float, str] | None:
    """Unit cost of a spec part from its geometry × material price + conversion. None when there is no geometry."""
    mk = _material_key(p.material)
    dens, price = DENSITY[mk], PRICE_KG[mk]
    d = p.dimensions
    if d is None:
        return None
    L, W, H = d.length.value, d.width.value, d.height.value
    proc = str(getattr(p.process_hint, "value", p.process_hint))
    t = p.wall_thickness.value if p.wall_thickness else None
    if proc == "injection_molding" and t:
        vol = 2 * (L * W + L * H + W * H) * t * 0.6 / 1000.0  # open shell ≈ 60% of a closed box, cm³
        mass_g = vol * dens
        resin = mass_g / 1000 * price
        conv = 0.25 + 0.012 * vol
        return resin + conv, (
            f"Moulded shell {L:g}×{W:g}×{H:g} mm, wall {t:g} mm ≈ {vol:.1f} cm³ × {dens} g/cm³ = {mass_g:.0f} g × ${price}/kg "
            f"+ ${conv:.2f} moulding/finish conversion"
        )
    if proc == "extrusion":
        wall = t or 1.5
        area = 2 * (min(L, W, H) + sorted([L, W, H])[1]) * wall  # mm² hollow section
        length = max(L, W, H)
        vol = area * length / 1000.0
        mass_g = vol * dens
        c = mass_g / 1000 * price + 0.45
        return c, f"Extrusion section ≈ {area:.0f} mm² × {length:g} mm = {vol:.1f} cm³ × {dens} g/cm³ = {mass_g:.0f} g × ${price}/kg + $0.45 cut/finish"
    if proc == "sheet_metal":
        thick = t or min(L, W, H)
        vol = L * W * thick / 1000.0
        mass_g = vol * dens
        c = mass_g / 1000 * price + 0.25
        return c, f"Stamped plate {L:g}×{W:g}×{thick:g} mm = {vol:.1f} cm³ × {dens} g/cm³ = {mass_g:.0f} g × ${price}/kg + $0.25 stamping/plating"
    if proc == "cnc":
        stock = L * W * H / 1000.0  # cm³ billet
        mass_g = stock * dens
        machining = 6.0 + 0.015 * stock  # set-up share + removal time, assumption
        return mass_g / 1000 * price + machining, (
            f"CNC from billet {L:g}×{W:g}×{H:g} mm = {stock:.0f} cm³ × {dens} g/cm³ = {mass_g:.0f} g × ${price}/kg "
            f"+ ${machining:.2f} machining/finish ($6 + $0.015/cm³ of billet, assumption)"
        )
    return None


def tooling_items(ctx: StageContext, bom: list[BOMItem]) -> list[ToolingItem]:
    spec = ctx.artifact(3)
    items: list[ToolingItem] = []
    if spec is not None and spec.parts:
        for p in spec.parts:
            proc = str(getattr(p.process_hint, "value", p.process_hint))
            if proc == "injection_molding":
                d = p.dimensions
                area = d.length.value * d.width.value if d else 60 * 40
                big = d is not None and max(d.length.value, d.width.value) > 300
                if big:
                    cost = 30000.0
                    note = f"Large part (>300 mm): low end of the complex multi-cavity steel mold range $30,000-100,000. {ZETAR}"
                else:
                    cost = round(1000 + 2000 * min(1.0, area / 22500.0), -1)
                    note = f"Simple 1-cavity mold: point in the sourced range $1,000-3,000 scaled by projected area {area:,.0f} mm². {ZETAR}"
                items.append(ToolingItem(name=f"{p.name} mold (1-cavity)", process=ProcessType.injection_molding, cost=usd(cost, "estimate", note, nd=0)))
            elif proc == "extrusion":
                items.append(ToolingItem(name=f"Extrusion die ({p.name})", process=ProcessType.extrusion, cost=usd(600, "estimate", "Typical small-profile extrusion die, assumption", nd=0)))
            elif proc == "sheet_metal":
                items.append(ToolingItem(name=f"Stamping die ({p.name})", process=ProcessType.sheet_metal, cost=usd(1200, "estimate", "Single-stage blanking die, assumption", nd=0)))
            elif proc == "die_casting":
                items.append(ToolingItem(name=f"Die-casting die ({p.name})", process=ProcessType.die_casting, cost=usd(8000, "estimate", "Small single-cavity die-casting die, assumption", nd=0)))
        return items
    for it in bom:
        if str(getattr(it.category, "value", it.category)) == "mechanical" and re.search(r"housing|shell|case|diffuser|cover|lid|enclosure|bezel", it.part, re.I) and re.search(r"mould|mold|pc|abs|plastic|shell|housing|diffuser", it.part, re.I):
            items.append(ToolingItem(name=f"{it.part} mold (1-cavity)", process=ProcessType.injection_molding,
                                     cost=usd(1800, "estimate", f"Simple 1-cavity mold, mid-point of the sourced range $1,000-3,000 (no CAD geometry available). {ZETAR}", nd=0)))
    return items


def certifications(ctx: StageContext) -> tuple[float, str, list[tuple[str, float]]]:
    dfm = ctx.artifact(4)
    if dfm is not None and dfm.certifications:
        rows = [(f"{c.market} {c.standard}", c.cost_est.value) for c in dfm.certifications if c.required]
        return sum(v for _, v in rows), f"Sum of {len(rows)} required certifications from stage 4 (their own cost estimates)", rows
    brief = ctx.artifact(1)
    markets = [m.upper() for m in (brief.target_markets if brief else ["US", "EU"])]
    wireless = bool(brief.wireless) if brief else False
    rows = []
    if "US" in markets:
        rows.append(("US FCC Part 15" + (" (intentional radiator)" if wireless else "B"), 6000 if wireless else 3000))
    if any(m in markets for m in ("EU", "FR", "DE", "UK")):
        rows.append(("EU CE (LVD/EMC" + ("/RED)" if wireless else ")"), 6500 if wireless else 3500))
    if has_battery(ctx):
        rows.append(("Li-ion UN38.3 + IEC 62133-2", 2500))
    return sum(v for _, v in rows), "Default certification estimates (no stage 4 certifications): " + ", ".join(f"{n} ${v:,.0f}" for n, v in rows), rows


# --------------------------------------------------------------------------- cost model


@dataclass
class Line:
    item: BOMItem
    base: float  # unit price at the reference decay step (estimate path)
    note: str
    lcsc: bool = False


@dataclass
class Unit:
    bom: float
    assembly: float
    packaging: float
    lines: list[tuple[Line, float]] = field(default_factory=list)

    @property
    def unit(self) -> float:
        return self.bom + self.assembly + self.packaging


@dataclass
class CostModel:
    lines: list[Line]
    volumes: list[int]
    vf: float
    assembly_min: float
    assembly_note: str

    def steps(self, qty: int) -> int:
        return max((i for i, v in enumerate(self.volumes) if qty >= v), default=0)

    def unit_cost(self, qty: int) -> Unit:
        k = self.steps(qty)
        decay = self.vf ** k
        bom = pack = 0.0
        out: list[tuple[Line, float]] = []
        for ln in self.lines:
            if ln.lcsc:
                p = price_at(ln.item.lcsc_pn, max(1, round(qty * ln.item.qty))) or ln.base
            else:
                p = ln.base * decay
            out.append((ln, p))
            ext = p * ln.item.qty
            if str(getattr(ln.item.category, "value", ln.item.category)) == "packaging":
                pack += ext
            else:
                bom += ext
        assembly = self.assembly_min / 60.0 * LABOUR_RATE * FACTORY_OVERHEAD * decay + FACTORY_MARGIN * (bom + pack)
        return Unit(bom, assembly, pack, out)

    @classmethod
    def from_ctx(cls, ctx: StageContext) -> "CostModel":
        inp = ctx.inputs or {}
        prev = ctx.artifact(5)
        vols = sorted({int(v) for v in inp.get("volumes", [])}) if inp.get("volumes") else []
        if len(vols) < 3:
            brief = ctx.artifact(1)
            bv = sorted(set(brief.target_volumes)) if brief and len(set(brief.target_volumes)) >= 3 else None
            vols = [t.quantity for t in prev.tiers] if (prev is not None and ctx.stage != 5) else (bv or DEFAULT_VOLUMES)
        vf = float(inp.get("volume_factor", prev.volume_factor.value if (prev is not None and ctx.stage != 5) else DEFAULT_VF))
        if not 0.5 <= vf <= 1.0:
            raise ValueError(f"volume_factor must be between 0.5 and 1.0, got {vf}")
        ref = int(inp.get("reference_quantity", DEFAULT_REF))
        bom, _, _ = load_bom(ctx, ref)
        spec = ctx.artifact(3)
        lines: list[Line] = []
        for it in bom:
            if it.lcsc_pn and it.unit_cost_est is not None and label_of(it.unit_cost_est) == "sourced":
                lines.append(Line(it, it.unit_cost_est.value, lcsc_source(it.lcsc_pn), lcsc=True))
                continue
            base = it.unit_cost_est.value if it.unit_cost_est else None
            note = it.unit_cost_est.source_or_assumption if it.unit_cost_est else ""
            if str(getattr(it.category, "value", it.category)) == "mechanical" and spec is not None:
                sp = _find_spec_part(it, spec.parts)
                pc = part_cost(sp) if sp else None
                if pc:
                    base, note = pc[0] * (sp.quantity if sp.quantity and sp.quantity > 1 else 1), f"{sp.name}: {pc[1]}"
            if base is None and it.qty > 20:  # many identical small parts (switches, sockets, fasteners): per-piece placeholder
                base, note = 0.12, f"Placeholder USD 0.12 per piece for a small part used {it.qty:g}× per unit: no price in the BOM and no geometry"
            if base is None:
                base, note = 0.5, "Placeholder USD 0.50: no price in the BOM and no geometry"
            lines.append(Line(it, base, note or "BOM price assumption"))
        n = sum(1 for ln in lines if str(getattr(ln.item.category, "value", ln.item.category)) != "packaging")
        mins = ASSEMBLY_BASE_MIN + ASSEMBLY_MIN_PER_LINE * n
        return cls(lines, vols, vf, mins, f"{mins:.1f} min = {ASSEMBLY_BASE_MIN:g} base + {ASSEMBLY_MIN_PER_LINE:g} × {n} BOM lines; × ${LABOUR_RATE:.0f}/h × {FACTORY_OVERHEAD:g} overhead, + {FACTORY_MARGIN:.0%} factory margin and scrap on materials")


# --------------------------------------------------------------------------- stage 5


def target_price(ctx: StageContext) -> tuple[float, str, str] | None:
    brief = ctx.artifact(1)
    if brief is None:
        return None
    p = brief.target_retail_price
    fx = FX_TO_USD.get(p.unit.upper())
    if fx is None:
        return None
    note = f"Brief target price {p.value:g} {p.unit}" + (f" × {fx} (assumed FX)" if fx != 1.0 else "")
    return p.value * fx, note, label_of(p)


def _round2(x: float) -> float:
    return round(x + 1e-12, 2)


def build_costs(ctx: StageContext) -> CostsArtifact:
    model = CostModel.from_ctx(ctx)
    inp = ctx.inputs or {}
    vols = model.volumes
    ref = int(inp.get("reference_quantity", DEFAULT_REF))
    if ref not in vols:
        ref = vols[len(vols) // 2] if DEFAULT_REF not in vols else DEFAULT_REF
    bom_items, gen, bom_notes = load_bom(ctx, ref)
    spec = ctx.artifact(3)
    hts = landed.hts_for(ctx)
    fopts = freight_opts(ctx)
    tools = tooling_items(ctx, bom_items)
    tooling_total = sum(t.cost.value for t in tools)
    cert_total, cert_note, _ = certifications(ctx)

    # per-line table at the reference quantity
    ref_unit = model.unit_cost(ref)
    bom_lines = []
    for ln, p in ref_unit.lines:
        it = ln.item
        if ln.lcsc:
            part = get_part(it.lcsc_pn)
            price = lv(p, "USD", "sourced", lcsc_source(it.lcsc_pn), nd=4)
            stock = lv(stock_of(it.lcsc_pn) or 0, "units", "sourced", lcsc_source(it.lcsc_pn, "stock"), nd=0)
            ext = lv(p * it.qty, "USD", "estimate", f"{EXTENDED_NOTE}: {it.qty:g} × {p:.4f} (price break at {round(ref * it.qty):,} pcs, {part.pn if part else ''})", nd=4)
        else:
            price = lv(p, "USD", "estimate", ln.note, nd=4)
            stock = None
            ext = lv(p * it.qty, "USD", "estimate", f"{it.qty:g} × {p:.4f}", nd=4)
        bom_lines.append(CostLine(bom_item_id=it.id, part=it.part, qty_per_unit=it.qty, unit_price=price, lcsc_pn=it.lcsc_pn, stock=stock, extended=ext))

    tp = target_price(ctx)
    tiers: list[CostTier] = []
    landed_by_q: dict[int, tuple[list[LandedCostComponent], float, float]] = {}
    for q in vols:
        u = model.unit_cost(q)
        comps, total = landed.landed_cost(u.unit, q, landed.choose_mode(q, **fopts), hts, False, tooling_total=tooling_total, **fopts)
        landed_by_q[q] = (comps, total.value, u.unit)
    ref_landed = landed_by_q[ref][1] if ref in landed_by_q else landed.landed_cost(ref_unit.unit, ref, landed.choose_mode(ref, **fopts), hts, False, tooling_total=tooling_total, **fopts)[1].value

    if tp is not None:
        target, tp_note, tp_label = tp
        target_lv = usd(target, "estimate", tp_note + " (retail price incl. VAT where applicable)")
    else:
        target = round(3.0 * ref_landed, 2)
        target_lv = usd(target, "estimate", f"No target price in the brief: assumed 3 × landed cost at {ref:,} units")

    for i, q in enumerate(vols):
        u = model.unit_cost(q)
        _, lt, _ = landed_by_q[q]
        margin = (target - lt) / target * 100 if target else 0.0
        tiers.append(
            CostTier(
                quantity=q,
                bom_cost=usd(u.bom, "estimate", f"Electronics at LCSC price breaks ({LCSC_SOURCE}); other lines base × {model.vf:g}^{model.steps(q)}"),
                assembly_cost=usd(u.assembly, "estimate", f"Assembly + factory overhead/margin: {model.assembly_note}; labour × {model.vf:g}^{model.steps(q)}"),
                packaging_cost=usd(u.packaging, "estimate", f"Packaging BOM lines × {model.vf:g}^{model.steps(q)}"),
                unit_cost=usd(u.unit, "estimate", "BOM + assembly + packaging (ex-works, FOB basis)"),
                tooling_amortisation=usd(tooling_total / q, "estimate", f"${tooling_total:,.0f} tooling ÷ {q:,}"),
                margin_pct=lv(margin, "pct", "estimate", f"(${target:.2f} target − ${lt:.2f} landed estimate) ÷ target; before retailer margin, VAT and marketing", nd=1),
            )
        )

    # cash breakdown at the reference quantity
    comps_ref, _, _ = (landed_by_q[ref] if ref in landed_by_q else (None, 0, 0))
    if comps_ref is None:
        comps_ref = landed.landed_cost(ref_unit.unit, ref, landed.choose_mode(ref, **fopts), hts, False, tooling_total=tooling_total, **fopts)[0]
    g = landed.cash_components(comps_ref, ref)
    first_order = ref_unit.unit * ref
    samples = 3 * (10 * ref_unit.unit + 120.0)
    rows: list[tuple[str, float, str, str]] = [
        ("Tooling", tooling_total, "estimate", "Sum of tooling lines"),
        ("Certification", cert_total, "estimate", cert_note),
        ("Samples (T0, T1, golden)", samples, "estimate", f"3 rounds × (10 units × ${ref_unit.unit:.2f} + $120 express shipping)"),
        (f"First production order ({ref:,} × FOB)", first_order, "estimate", f"{ref:,} × ${ref_unit.unit:.2f} ex-works"),
        ("Pre-shipment inspection", g["qc"], "estimate", f"V-Trust rate (Sourced) × estimated man-days: ${landed.QC_MAN_DAY_USD:.0f}/man-day ({VTRUST_SOURCE}) × {landed.qc_man_days(ref)} man-days"),
        ("Freight + insurance", g["freight"], "fictional", "demo freight and insurance rates — demo data"),
        ("Duties (HTS + Section 301)", g["duties"], "estimate", f"HTS {hts.code}: {hts.general_rate.source_or_assumption}; IEEPA 0; Section 122 off"),
        ("Broker, port, 3PL", g["broker3pl"], "estimate", f"Broker/port/3PL per-unit rates × {ref:,}"),
        ("Platform / agent fee", g["platform"], "estimate", f"{landed.PLATFORM_FEE_PCT:g}% of FOB (benchmark 5-10%)"),
    ]
    cash = [LandedCostComponent(name=n, amount=usd(_round2(v), lab, note)) for n, v, lab, note in rows]
    total = _round2(sum(c.amount.value for c in cash))

    # break-even: fixed cash before the first unit ÷ contribution per unit (landed without tooling amortisation)
    var_landed = ref_landed - tooling_total / ref
    contribution = target - var_landed
    fixed = tooling_total + cert_total + samples
    # not profitable at the target price: still a valid (and useful) answer — say so instead of failing the stage
    breakeven = math.ceil(fixed / contribution) if contribution > 0 else 0
    breakeven_note = (
        f"(tooling + certification + samples = ${fixed:,.0f}) ÷ (${target:.2f} target − ${var_landed:.2f} variable landed cost)"
        if contribution > 0
        else f"NOT REACHABLE: target ${target:.2f} is below the variable landed cost ${var_landed:.2f} — raise the price or cut BOM/assembly cost"
    )

    assumptions = [
        Assumption(id="a1", text=f"Volume curve: non-LCSC lines and assembly × {model.vf:g} per tier step ({' → '.join(f'{v:,}' for v in vols)})", label="estimate", source="Demo assumption (PRD §11), editable", stage=5),
        Assumption(id="a2", text=f"Assembly {model.assembly_note}", label="estimate", source=None, stage=5),
        Assumption(id="a3", text=f"Electronic lines matched to the JLCPCB/LCSC parts snapshot of {SNAPSHOT_DATE} (CDFER/jlcpcb-parts-database, MIT); unmatched lines are estimates", label="sourced", source="https://github.com/CDFER/jlcpcb-parts-database", stage=5),
        Assumption(id="a4", text="Simple 1-cavity injection mold $1,000-3,000; complex multi-cavity steel mold $30,000-100,000", label="estimate", source=ZETAR, stage=5),
        Assumption(id="a5", text=cert_note, label="estimate", source=None, stage=5),
        Assumption(id="a6", text=f"Landed-cost basis for margin and cash: sea freight (fictional rates), HTS {hts.code} (general {hts.general_rate.value:g}%, Section 301 {hts.section_301_rate.value:g}%), IEEPA 0, Section 122 off", label="estimate", source=hts.source_url, stage=5),
        Assumption(id="a7", text=target_lv.source_or_assumption, label="estimate", source=None, stage=5),
    ] + [Assumption(id=f"b{i}", text=n, label="estimate", source=None, stage=5) for i, n in enumerate(bom_notes, 1)]

    return CostsArtifact(
        project_id=ctx.project.id,
        generated_by=gen,
        assumptions=assumptions,
        bom_lines=bom_lines,
        volume_factor=lv(model.vf, "ratio", "estimate", f"Volume curve: unit cost × {model.vf:g} per tier step", nd=3),
        tiers=tiers,
        tooling=tools,
        tooling_total=usd(tooling_total, "estimate", "Sum of tooling lines", nd=0),
        certification_total=usd(cert_total, "estimate", cert_note, nd=0),
        reference_quantity=ref,
        total_cash_needed=usd(total, "estimate", "Sum of cash_breakdown"),
        cash_breakdown=cash,
        target_retail_price=target_lv,
        breakeven_units=lv(breakeven, "units", "estimate", breakeven_note, nd=0),
    )


@stage_handler(5)
def run_costs(ctx: StageContext) -> CostsArtifact:
    return build_costs(ctx)
