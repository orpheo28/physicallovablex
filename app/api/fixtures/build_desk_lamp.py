"""Hand-authored source of the desk lamp fixture set (PRD Appendix A, prompt 1).

Written as Python so every figure is computed once and stays consistent across stages
(stage 5 total cash = stage 12 cash curve; stage 11 landed cost reconciles with stage 5).
Regenerate the JSON files:  uv run python -m api.fixtures.build_desk_lamp

Honesty notes:
- LCSC prices are real: jlcsearch (tscircuit) query on 2026-09-26, price break for the 500-2000 tier.
- DFM 'measured' findings are the real output of api/dfm/measure.py on the committed CAD
  (api/cad/prebuilt/demo_desk_lamp/enclosure.step), recomputed every time this script runs.
- HTS 8513.10.40.00 general rate 3.5% is Sourced (USITC, api/costs/data/hts.json, verified by W3);
  Section 301 stays an Estimate until a customs broker confirms. Freight, factories, quotes = fictional demo data.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from api.dfm.measure import measure
from api.costs import landed as landed_mod
from api.fixtures._bbox import glb_size_mm
from api.fixtures._live import LiveCosts, live_stage
from contracts import artifacts as A

OUT = Path(__file__).parent / "desk_lamp"
NET = Path(__file__).parent / "network"
PID = "demo_desk_lamp"
T0 = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
LCSC_SRC = "LCSC price via jlcsearch, 2026-09-26"


def lcsc_src(pn: str | None, what: str = "price") -> str:
    """Sourced LCSC value: jlcsearch query date + the product page URL."""
    return f"LCSC {what} via jlcsearch, snapshot 2026-09-26, https://www.lcsc.com/product-detail/{pn}.html"
EUR_USD = 1.08
HTS = json.loads((Path(__file__).parents[1] / "costs" / "data" / "hts.json").read_text())["lines"]["desk_lamp"]
PREBUILT = Path(__file__).parents[1] / "cad" / "prebuilt" / PID


def _measured_dims(glb: str) -> dict:
    """Stage 3 overall dimensions = bounding box of the committed full-product CAD model (Measured), as live spec.py."""
    L, W, H = glb_size_mm(PREBUILT / glb)
    src = f"Bounding box of the committed full-product CAD model /files/{PID}/{glb} (build123d/OCCT export)"
    return {"length": lv(L, "mm", "measured", src), "width": lv(W, "mm", "measured", src), "height": lv(H, "mm", "measured", src)}


def lv(value: float, unit: str, label: str, src: str) -> dict:
    return {"value": round(value, 4), "unit": unit, "label": label, "source_or_assumption": src}


def usd(v: float, label: str = "estimate", src: str = "") -> dict:
    return lv(round(v, 2), "USD", label, src)


def mm(v: float, label: str = "estimate", src: str = "Design parameter") -> dict:
    return lv(v, "mm", label, src)


def dims(l: float, w: float, h: float, src: str = "Design parameter") -> dict:
    return {"length": mm(l, src=src), "width": mm(w, src=src), "height": mm(h, src=src)}


def base(**kw) -> dict:
    return {"project_id": PID, "status": "validated", "fallback": False, "generated_by": "fixture", "generated_at": T0.isoformat(), **kw}


# ----------------------------------------------------------------------------- assumptions register

ASSUMPTIONS = [
    {"id": "a1", "text": f"EUR→USD at {EUR_USD} for the €89 target price", "label": "estimate", "source": None, "stage": 1},
    {"id": "a2", "text": "Volume curve: unit cost × 0.92 per tier step (500 → 2,000 → 10,000)", "label": "estimate", "source": "Demo assumption (PRD §11)", "stage": 5},
    {"id": "a3", "text": "Assembly + factory overhead/margin: $3.10 per unit at 500", "label": "estimate", "source": None, "stage": 5},
    {"id": "a4", "text": "Pre-shipment inspection $268 per man-day", "label": "sourced", "source": "V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26", "stage": 10},
    {"id": "a5", "text": "Platform/agent fee 7% of FOB (benchmark 5-10%)", "label": "estimate", "source": "Dragon Sourcing benchmark 5-10%", "stage": 11},
    {"id": "a6", "text": f"HTS {HTS['code']} (portable lamp with its own battery): general rate {HTS['general_rate_pct']:g}%", "label": "sourced", "source": f"{HTS['general_source']} — {HTS['source_url']}", "stage": 11},
    {"id": "a7", "text": "IEEPA duties not collected since 24/02/2026; de minimis suspended; Section 122 surcharge off (toggle)", "label": "sourced", "source": "CBP CSMS 67834313 (https://content.govdelivery.com/accounts/USDHSCBP/bulletins/40b11c9); Federal Register 24/06/2026", "stage": 11},
    {"id": "a8", "text": "Sea LCL Shenzhen → Los Angeles, $0.85/unit, 32 days door to 3PL", "label": "fictional", "source": "demo data", "stage": 11},
    {"id": "a9", "text": "Simple single-cavity P20 molds $1,800-3,500 each", "label": "estimate", "source": "Zetar Mold 2026 range $1,000-3,000 (vendor, medium)", "stage": 5},
    {"id": "a10", "text": "Measured DFM checks assume a straight two-half tool pulling along ±Z (split line in the XY plane)", "label": "estimate", "source": "api/dfm/measure.py on api/cad/prebuilt/demo_desk_lamp/enclosure.step", "stage": 4},
    {"id": "a11", "text": f"Section 301 China {HTS['section_301_rate_pct']:g}% on HTS {HTS['code']} — confirm with a customs broker", "label": "estimate", "source": HTS["section_301_source"], "stage": 11},
]

# ----------------------------------------------------------------------------- stage 1

brief = base(
    stage=1,
    mode="idea",
    prompt="Magnetic rechargeable desk lamp, minimalist, sold €89",
    product_name="Magnetic Rechargeable Desk Lamp",
    one_liner="A minimalist cordless desk lamp whose LED head snaps magnetically onto an aluminium stem and detaches as a portable light.",
    category="Consumer lighting",
    target_markets=["US", "EU"],
    target_retail_price=lv(89, "EUR", "estimate", "Founder target retail price (incl. VAT in EU)"),
    target_volumes=[500, 2000, 10000],
    key_features=["Magnetic detachable LED head", "USB-C rechargeable 18650 battery, ~10 h at 50%", "Touch dimming, 3 colour temperatures", "Anodised aluminium stem, weighted base"],
    constraints=["Retail €89", "No wireless radio (keeps FCC to Part 15B)", "Ship-ready for US and EU"],
    has_battery=True,
    wireless=[],
    pasted_bom=[],
    clarifying_questions=[
        {"id": "q1", "topic": "markets", "question": "Which markets at launch?", "options": ["US", "EU", "UK"], "answer": "US + EU", "skipped": False},
        {"id": "q2", "topic": "volume", "question": "First production run size?", "options": ["500", "2,000", "10,000"], "answer": "2,000", "skipped": False},
        {"id": "q3", "topic": "target_price", "question": "Confirm target retail price?", "options": ["€69", "€89", "€119"], "answer": "€89", "skipped": False},
        {"id": "q4", "topic": "battery", "question": "Battery runtime target?", "options": ["5 h", "10 h", "20 h"], "answer": "10 h", "skipped": False},
        {"id": "q5", "topic": "wireless", "question": "Any app or wireless control?", "options": ["None", "BLE"], "answer": None, "skipped": True},
    ],
    assumptions=[ASSUMPTIONS[0]],
)

# ----------------------------------------------------------------------------- stage 2

design = base(
    stage=2,
    directions=[
        {"id": "d1", "name": "Column", "description": "Slim anodised aluminium column, rectangular LED head snaps on at the top via 4 magnets.", "shape": "Rectilinear column + bar head", "material": "Aluminium 6063 + PC/ABS", "finish": "Bead-blasted natural anodised stem; warm white MT-11010 texture on head and base", "dimensions": dims(180, 120, 340), "cad_parameters": {"head_length": 180, "head_width": 40, "head_height": 18, "stem_height": 300, "stem_diameter": 16, "base_length": 120, "base_width": 120, "base_height": 22, "wall": 2.0}, "render_url": f"/files/{PID}/d1.png", "glb_url": f"/files/{PID}/d1.glb"},
        {"id": "d2", "name": "Arc", "description": "Single moulded arc from base to head, magnetic puck head for handheld use.", "shape": "Continuous arc", "material": "PC/ABS", "finish": "Soft-touch paint, graphite", "dimensions": dims(220, 110, 320), "cad_parameters": {"arc_radius": 180, "arc_width": 30, "head_diameter": 70, "base_diameter": 110, "wall": 2.2}, "render_url": f"/files/{PID}/d2.png", "glb_url": f"/files/{PID}/d2.glb"},
        {"id": "d3", "name": "Puck", "description": "Low steel base with a magnetic puck lamp that tilts 360°.", "shape": "Disc + hemisphere", "material": "Zinc die-cast + PC", "finish": "Powder coat, charcoal (base); warm white lamp", "dimensions": dims(130, 130, 150), "cad_parameters": {"base_diameter": 130, "base_height": 15, "puck_diameter": 90, "puck_height": 45, "wall": 2.0}, "render_url": f"/files/{PID}/d3.png", "glb_url": f"/files/{PID}/d3.glb"},
    ],
    chosen_direction_id="d1",
    assumptions=[
        {"id": "a2_render", "label": "estimate", "text": "AI concept render — illustrative, not the CAD", "source": None, "stage": 2},
        {"id": "a2_hero", "label": "estimate", "text": f"Rendered from the CAD: /files/{PID}/hero_d1.png, /files/{PID}/hero_d2.png, /files/{PID}/hero_d3.png", "source": None, "stage": 2},
    ],
)

# ----------------------------------------------------------------------------- stage 3 (spec + BOM)

BOM_RAW = [
    # id, part, category, qty, unit price, label, source, lcsc, risk, alternative
    ("e1", "White LED 2835 4000K 0.3 W", "electronic", 24, 0.0077, "sourced", LCSC_SRC, "C210311", ("low", ["Stock 1.09M"]), "Any 2835 4000K CRI>90 bin"),
    ("e2", "Li-ion charger IC TP4056 (ESOP-8)", "electronic", 1, 0.0505, "sourced", LCSC_SRC, "C725790", ("low", ["Stock 288k", "Multi-source"]), "TP4056-MS (C7473158)"),
    ("e3", "USB-C receptacle 16P SMD", "electronic", 1, 0.0598, "sourced", LCSC_SRC, "C2765186", ("low", ["Stock 1.17M"]), "TYPE-C16PIN (C393939)"),
    ("e4", "N-MOSFET AO3400A (LED PWM)", "electronic", 1, 0.0529, "sourced", LCSC_SRC, "C20917", ("low", ["LCSC basic part"]), "AO3400A (C347475)"),
    ("e5", "Touch-dimming MCU (8-bit, SOP-8)", "electronic", 1, 0.25, "estimate", "Part not selected yet; typical 8-bit MCU price", None, ("medium", ["Part not selected"]), "Pick from LCSC basic parts"),
    ("e6", "Li-ion cell 18650 3000 mAh", "electronic", 1, 2.40, "estimate", "Branded cell with UN38.3 report, 2k MOQ", None, ("high", ["Counterfeit/unbranded cell risk", "UN38.3 report required", "Air-freight restrictions"]), "Tier-1 branded 18650 with UN38.3 + IEC 62133-2 reports"),
    ("e7", "Aluminium MCPCB for LED bar 170×12 mm", "electronic", 1, 0.35, "estimate", "JLCPCB aluminium PCB, 2k pcs", None, ("low", []), None),
    ("e8", "Control PCB 2-layer + passives, assembled", "electronic", 1, 0.60, "estimate", "PCBA incl. passives, 2k pcs", None, ("low", []), None),
    ("m1", "Head housing, PC/ABS, textured", "mechanical", 1, 0.95, "estimate", "Part weight 28 g × resin + cycle cost", None, None, None),
    ("m2", "Opal PC diffuser", "mechanical", 1, 0.30, "estimate", "Part weight 9 g", None, None, None),
    ("m3", "Stem, aluminium 6063 extrusion, anodised", "mechanical", 1, 1.60, "estimate", "300 mm cut length + anodising", None, None, None),
    ("m4", "Base shell, PC/ABS", "mechanical", 1, 1.10, "estimate", "Part weight 35 g", None, None, None),
    ("m5", "Steel weight plate, zinc-plated", "mechanical", 1, 0.70, "estimate", "Stamped 3 mm steel, 380 g", None, None, None),
    ("m6", "N52 neodymium magnet Ø10×3 mm", "mechanical", 4, 0.08, "estimate", "Catalogue magnet, 10k pcs", None, ("medium", ["Rare-earth price volatility"]), "N45 grade at slightly lower pull force"),
    ("m7", "Fastener set (M2/M3 screws)", "mechanical", 1, 0.10, "estimate", "Standard fasteners", None, None, None),
    ("m8", "Silicone foot pad", "mechanical", 1, 0.12, "estimate", "Die-cut silicone", None, None, None),
    ("k1", "Retail box + moulded pulp insert", "packaging", 1, 0.90, "estimate", "Rigid 2-piece box, 1-colour print", None, None, None),
    ("k2", "USB-C cable 1 m", "packaging", 1, 0.45, "estimate", "Generic USB-C to USB-C 3 A", None, None, None),
]

bom = []
for bid, part, cat, qty, price, label, src, lcsc, risk, alt in BOM_RAW:
    src = lcsc_src(lcsc) if label == "sourced" else src
    bom.append({
        "id": bid, "part": part, "category": cat, "qty": qty, "description": None, "manufacturer_pn": None, "lcsc_pn": lcsc,
        "unit_cost_est": usd(price, label, src) if label == "estimate" else lv(price, "USD", label, src),
        "risk": {"level": risk[0], "reasons": risk[1]} if risk else None,
        "alternative": alt,
    })

PARTS = [
    {"id": "p1", "name": "Head housing", "material": "PC/ABS (UL94 V-0)", "finish": "MT-11010 texture", "process_hint": "injection_molding", "tolerance": "±0.1 mm on magnet pockets", "dimensions": dims(180, 40, 18), "wall_thickness": mm(2.0), "quantity": 1},
    {"id": "p2", "name": "Diffuser", "material": "Opal PC", "finish": "Frosted", "process_hint": "injection_molding", "tolerance": "±0.15 mm", "dimensions": dims(172, 14, 4), "wall_thickness": mm(1.5), "quantity": 1},
    {"id": "p3", "name": "Stem", "material": "Aluminium 6063-T5", "finish": "Bead-blasted, anodised black", "process_hint": "extrusion", "tolerance": "±0.2 mm length", "dimensions": dims(16, 16, 300), "wall_thickness": mm(1.5), "quantity": 1},
    {"id": "p4", "name": "Base shell", "material": "PC/ABS (UL94 V-0)", "finish": "MT-11010 texture", "process_hint": "injection_molding", "tolerance": "±0.1 mm on USB-C opening", "dimensions": dims(120, 120, 22), "wall_thickness": mm(2.2), "quantity": 1},
    {"id": "p5", "name": "Weight plate", "material": "SPCC steel 3 mm", "finish": "Zinc plated", "process_hint": "sheet_metal", "tolerance": "±0.2 mm", "dimensions": dims(110, 110, 3), "wall_thickness": None, "quantity": 1},
    {"id": "p6", "name": "PCBA (control + LED bar)", "material": "FR-4 + aluminium MCPCB", "finish": "HASL lead-free", "process_hint": "pcba", "tolerance": None, "dimensions": None, "wall_thickness": None, "quantity": 1},
]

spec = base(
    stage=3,
    product_name="Magnetic Rechargeable Desk Lamp",
    direction_id="d1",
    overall_dimensions=_measured_dims("d1.glb"),
    weight=lv(690, "g", "estimate", "Sum of part weight estimates"),
    parts=PARTS,
    electronics_blocks=[
        {"id": "b1", "name": "USB-C input", "function": "5 V charging input"},
        {"id": "b2", "name": "Charger (TP4056)", "function": "CC/CV Li-ion charging, 1 A"},
        {"id": "b3", "name": "18650 cell", "function": "Energy storage, 3000 mAh"},
        {"id": "b4", "name": "MCU", "function": "Touch sensing, PWM dimming, colour modes"},
        {"id": "b5", "name": "LED driver (AO3400A)", "function": "PWM switch for LED bar"},
        {"id": "b6", "name": "LED bar", "function": "24 × 2835 LEDs on MCPCB"},
        {"id": "b7", "name": "Pogo contacts + magnets", "function": "Power transfer head ↔ stem"},
    ],
    electronics_edges=[
        {"source": "b1", "target": "b2", "signal": "VBUS 5 V"},
        {"source": "b2", "target": "b3", "signal": "Charge 4.2 V"},
        {"source": "b3", "target": "b4", "signal": "VBAT"},
        {"source": "b4", "target": "b5", "signal": "PWM"},
        {"source": "b5", "target": "b7", "signal": "LED power"},
        {"source": "b7", "target": "b6", "signal": "LED power"},
    ],
    bom=bom,
    tolerances=["General ISO 2768-m", "Magnet pockets ±0.1 mm", "Head/stem air gap 0.3 ± 0.1 mm"],
    cad_files=[
        {"format": "glb", "url": f"/files/{PID}/d1.glb", "description": "Full product — materials (viewer model of direction d1)", "size_bytes": (PREBUILT / "d1.glb").stat().st_size},
        {"format": "step", "url": f"/files/{PID}/enclosure.step", "description": "Moulded parts (DFM) — Enclosure B-rep (build123d): moulded head housing + base shell, 1.5° draft, M2.5 bosses — open in any CAD tool", "size_bytes": (PREBUILT / "enclosure.step").stat().st_size},
        {"format": "stl", "url": f"/files/{PID}/enclosure.stl", "description": "Moulded parts (DFM) — Enclosure mesh for 3D-printed prototypes", "size_bytes": (PREBUILT / "enclosure.stl").stat().st_size},
        {"format": "glb", "url": f"/files/{PID}/enclosure.glb", "description": "Moulded parts (DFM) — Enclosure model for the 3D viewer", "size_bytes": (PREBUILT / "enclosure.glb").stat().st_size},
    ],
)

# ----------------------------------------------------------------------------- stage 4

# Real measured output on the committed CAD (head housing p1 = the moulded, textured part; pull along +Z).
MEASURED = [
    {**i.model_dump(mode="json"), "id": f"m{k}"}
    for k, i in enumerate(measure(PREBUILT / "enclosure.step", (0, 0, 1), finish=PARTS[0]["finish"], material=PARTS[0]["material"], part_id="p1"), 1)
]
dfm_issues = [
    *MEASURED,
    {"id": "i4", "severity": "major", "category": "tolerance", "method": "ai_reviewed", "part_id": "p3", "description": "Magnetic head/stem coupling needs a controlled air gap; anodising adds ~20 µm per side.", "fix": "Specify 0.3 ± 0.1 mm air gap after finishing and mask pogo contact area before anodising.", "rule_citation": "Type II anodising build-up ~50% outward growth — MIL-A-8625 guidance", "measurement": None, "resolved": False, "resolution": None},
    {"id": "i5", "severity": "critical", "category": "assembly", "method": "ai_reviewed", "part_id": "p4", "description": "18650 cell sits against the LED driver area; heat and pinch risk during assembly.", "fix": "Add a cell cradle rib with 2 mm clearance and a thermal barrier; cell protection circuit mandatory.", "rule_citation": "IEC 62133-2 cell protection and thermal abuse clauses", "measurement": None, "resolved": False, "resolution": None},
]

certifications = [
    {"market": "US", "standard": "FCC Part 15B (unintentional radiator)", "applies_because": "MCU clock + PWM LED driver", "required": True, "cost_est": usd(2500, src="Accredited lab quote range, demo assumption"), "lead_time_weeks": lv(4, "weeks", "estimate", "Typical lab queue")},
    {"market": "EU", "standard": "CE — EMC 2014/30/EU, RoHS, EN 62471 photobiological safety", "applies_because": "Electronic lighting product sold in the EU", "required": True, "cost_est": usd(3000, src="Accredited lab quote range, demo assumption"), "lead_time_weeks": lv(5, "weeks", "estimate", "Typical lab queue")},
    {"market": "Global", "standard": "UN38.3 (battery transport) + IEC 62133-2", "applies_because": "Contains a Li-ion 18650 cell", "required": True, "cost_est": usd(1800, src="IEC 62133-2 test at pack level; UN38.3 summary from cell supplier"), "lead_time_weeks": lv(4, "weeks", "estimate", "Typical lab queue")},
]

dfm = base(
    stage=4,
    issues=dfm_issues,
    component_risks=[
        {"bom_item_id": "e6", "part": "Li-ion cell 18650 3000 mAh", "level": "high", "reasons": ["Counterfeit/unbranded cell risk", "UN38.3 report required", "Air-freight restrictions"], "alternatives": ["Tier-1 branded 18650 with UN38.3 + IEC 62133-2 reports"], "stock": None, "lead_time_weeks": lv(6, "weeks", "estimate", "Branded cell lead time")},
        {"bom_item_id": "e5", "part": "Touch-dimming MCU", "level": "medium", "reasons": ["Part not selected"], "alternatives": ["Pick from LCSC basic parts to avoid extended-part fees"], "stock": None, "lead_time_weeks": None},
        {"bom_item_id": "e2", "part": "TP4056", "level": "low", "reasons": ["Multi-source"], "alternatives": ["TP4056-MS (C7473158)"], "stock": lv(288672, "units", "sourced", lcsc_src("C725790", "stock")), "lead_time_weeks": None},
    ],
    certifications=certifications,
    assumptions=[ASSUMPTIONS[9]],
)

# ----------------------------------------------------------------------------- stage 5 (costs)

VF = 0.92
TIERS = [500, 2000, 10000]
REF_Q = 2000
ASSEMBLY_500 = 3.10
TARGET_USD = round(89 * EUR_USD, 2)
# Landed-cost inputs from the LIVE code (api/costs/landed.py): CBP-precedent HTS, Drewry-derived sea freight,
# broker/3PL, platform fee, V-Trust QC — the cached example computes exactly what the live stages would.
LIVE = LiveCosts("desk_lamp", {"id": PID, "name": brief["product_name"], "mode": "idea", "prompt": brief["prompt"], "example": "desk_lamp"}, brief, spec)
_h = LIVE.hts  # the assumption register quotes the same (live) HTS line as stage 11
for _a in ASSUMPTIONS:
    if _a["id"] == "a6":
        _a.update(text=f"HTS {_h.code}: general duty {_h.general_rate.value:g}% ({_h.description[:120]})", label=_h.general_rate.label, source=_h.general_rate.source_or_assumption[:400])
    elif _a["id"] in ("a11", "a13") and "Section 301" in _a["text"]:
        _a.update(text=f"Section 301 China {_h.section_301_rate.value:g}% on HTS {_h.code}", label=_h.section_301_rate.label, source=_h.section_301_rate.source_or_assumption[:400])
SAMPLES = 600.0

cost_lines, bom_by_cat = [], {"electronic": 0.0, "mechanical": 0.0, "packaging": 0.0}
for b in bom:
    price = b["unit_cost_est"]["value"]
    ext = price * b["qty"]
    bom_by_cat[b["category"]] += ext
    cost_lines.append({
        "bom_item_id": b["id"], "part": b["part"], "qty_per_unit": b["qty"], "unit_price": b["unit_cost_est"], "lcsc_pn": b["lcsc_pn"],
        "stock": None, "extended": lv(round(ext, 4), "USD", "estimate", (f"LCSC unit price (Sourced) × estimated quantity: {b['qty']} × {price}" if b["unit_cost_est"]["label"] == "sourced" else f"{b['qty']} × {price}")),
    })
BOM_500 = bom_by_cat["electronic"] + bom_by_cat["mechanical"]
PKG_500 = bom_by_cat["packaging"]

tooling = [
    {"name": "Head housing mold (1-cavity P20)", "process": "injection_molding", "cost": usd(3500, src=ASSUMPTIONS[8]["source"])},
    {"name": "Diffuser mold (1-cavity)", "process": "injection_molding", "cost": usd(1800, src=ASSUMPTIONS[8]["source"])},
    {"name": "Base shell mold (1-cavity P20)", "process": "injection_molding", "cost": usd(3000, src=ASSUMPTIONS[8]["source"])},
    {"name": "Extrusion die (stem profile)", "process": "extrusion", "cost": usd(600, src="Typical small-profile die")},
    {"name": "Weight plate stamping die", "process": "sheet_metal", "cost": usd(1200, src="Single-stage blanking die")},
]
TOOLING = sum(t["cost"]["value"] for t in tooling)
CERT = sum(c["cost_est"]["value"] for c in certifications)


def unit_cost_at(k: int) -> tuple[float, float, float, float]:
    f = VF**k
    b, a, p = BOM_500 * f, ASSEMBLY_500 * f, PKG_500 * f
    return round(b, 2), round(a, 2), round(p, 2), round(b + a + p, 2)


def landed_per_unit(fob: float, q: int, tooling_total: float, fob_label: str = "estimate", fob_note: str = "Unit cost at tier") -> list[tuple[str, float, str, str]]:
    return LIVE.rows(fob, q, tooling_total, fob_label, fob_note)


tiers = []
for k, q in enumerate(TIERS):
    b, a, p, u = unit_cost_at(k)
    landed = sum(x[1] for x in landed_per_unit(u, q, TOOLING))
    tiers.append({
        "quantity": q,
        "bom_cost": usd(b, src=f"BOM at 500 × {VF}^{k}"),
        "assembly_cost": usd(a, src=ASSUMPTIONS[2]["text"]),
        "packaging_cost": usd(p, src="Packaging BOM lines"),
        "unit_cost": usd(u, src="BOM + assembly + packaging (ex-works)"),
        "tooling_amortisation": usd(TOOLING / q, src=f"${TOOLING:,.0f} / {q}"),
        "margin_pct": lv(round((TARGET_USD - landed) / TARGET_USD * 100, 1), "pct", "estimate", f"(${TARGET_USD} target − ${landed:.2f} landed estimate) / target"),
    })

U_REF = unit_cost_at(1)[3]
first_order = U_REF * REF_Q
ref_landed = landed_per_unit(U_REF, REF_Q, TOOLING)
LC = LIVE.cash(U_REF, REF_Q)
QC_COST = round(LC["qc"], 2)
cash_components = [
    ("Tooling", TOOLING, "estimate", "Sum of tooling lines"),
    ("Certification", CERT, "estimate", "FCC + CE + IEC 62133-2"),
    ("Samples (T0, T1, golden)", SAMPLES, "estimate", "3 sample rounds incl. express shipping"),
    ("First production order (2,000 × FOB)", first_order, "estimate", f"2,000 × ${U_REF}"),
    ("Pre-shipment inspection", QC_COST, "estimate", f"V-Trust rate (Sourced) × estimated man-days: $268/man-day (V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26) × {landed_mod.qc_man_days(REF_Q)} man-days"),
    ("Freight + insurance", LC["freight"], "estimate", f"{LIVE.mode(REF_Q).replace('_', ' ').upper()} per stage 11 (Drewry-derived) + insurance, × 2,000"),
    ("Duties (HTS + Section 301)", LC["duties"], "estimate", f"2,000 × FOB × (HTS {LIVE.hts.code} {LIVE.hts.general_rate.value:g}% + Section 301 {LIVE.hts.section_301_rate.value:g}%) — rates {LIVE.hts.general_rate.label}/{LIVE.hts.section_301_rate.label}, see stage 11"),
    ("Broker, port, 3PL", LC["broker3pl"], "estimate", "Customs entry $350/shipment + port + 3PL per unit × 2,000"),
    ("Platform fee", LC["platform"], "estimate", "7% of FOB (benchmark 5-10%, Dragon Sourcing)"),
]
cash_components = [(n, round(v, 2), l, s) for n, v, l, s in cash_components]
TOTAL_CASH = round(sum(v for _, v, _, _ in cash_components), 2)
variable_landed = sum(x[1] for x in ref_landed if not x[0].startswith(("Pre-shipment", "Tooling")))  # excl. QC and tooling amortisation
breakeven = (TOOLING + CERT + SAMPLES + QC_COST) / (TARGET_USD - variable_landed)

costs = base(
    stage=5,
    currency="USD",
    bom_lines=cost_lines,
    volume_factor=lv(VF, "ratio", "estimate", ASSUMPTIONS[1]["text"]),
    tiers=tiers,
    tooling=tooling,
    tooling_total=usd(TOOLING, src="Sum of tooling lines"),
    certification_total=usd(CERT, src="Sum of certification estimates"),
    reference_quantity=REF_Q,
    total_cash_needed=usd(TOTAL_CASH, src="Sum of cash_breakdown"),
    cash_breakdown=[{"name": n, "amount": usd(v, l, s) if l != "sourced" else lv(v, "USD", l, s)} for n, v, l, s in cash_components],
    target_retail_price=usd(TARGET_USD, src=f"€89 × {EUR_USD}"),
    breakeven_units=lv(round(breakeven), "units", "estimate", "(tooling + certification + samples + QC) / (target price − variable landed cost)"),
    assumptions=[ASSUMPTIONS[i] for i in (0, 1, 2, 4, 5, 8, 10)],
)

# ----------------------------------------------------------------------------- stage 6

production = base(
    stage=6,
    steps=[
        {"part_id": "p1", "part_name": "Head housing", "process": "injection_molding", "reason": "Textured cosmetic PC/ABS part at 2k+ volume; mold pays back vs CNC above ~300 units", "region": "Dongguan, Guangdong", "lead_time_days": lv(35, "days", "estimate", "T0 mold lead time")},
        {"part_id": "p2", "part_name": "Diffuser", "process": "injection_molding", "reason": "Thin optical PC part, uniform wall", "region": "Dongguan, Guangdong", "lead_time_days": lv(30, "days", "estimate", "T0 mold lead time")},
        {"part_id": "p3", "part_name": "Stem", "process": "extrusion", "reason": "Constant 16 mm profile; extrusion + cut + anodise is cheapest", "region": "Foshan, Guangdong", "lead_time_days": lv(20, "days", "estimate", "Die + first extrusion run")},
        {"part_id": "p4", "part_name": "Base shell", "process": "injection_molding", "reason": "Same resin and supplier as head housing", "region": "Dongguan, Guangdong", "lead_time_days": lv(35, "days", "estimate", "T0 mold lead time")},
        {"part_id": "p5", "part_name": "Weight plate", "process": "sheet_metal", "reason": "Flat 3 mm blank; stamping is fastest and cheapest", "region": "Dongguan, Guangdong", "lead_time_days": lv(15, "days", "estimate", "Die + first run")},
        {"part_id": "p6", "part_name": "PCBA", "process": "pcba", "reason": "SMT on LCSC parts; turnkey PCBA", "region": "Shenzhen, Guangdong", "lead_time_days": lv(12, "days", "estimate", "Turnkey PCBA incl. parts")},
    ],
    assembly_notes=["Final assembly, charge test and burn-in (2 h) at the molding supplier", "Cells shipped by sea only (UN3481, packed with equipment)"],
    total_lead_time_days=lv(63, "days", "estimate", "Critical path: molds (35) + T1 (14) + mass production (28) − overlap"),
)

# ----------------------------------------------------------------------------- network (fictional)

FACTORIES = [
    {"id": "f_orchid", "name": "Orchid Line Electronics (fictional)", "region": "Zhongshan, Guangdong", "archetype": "balanced", "personality": "Balanced: fair first quote, concedes on price if volume is firm, protects lead time.",
     "capacity": {"processes": ["injection_molding", "pcba", "assembly"], "materials": ["PC/ABS", "PC", "ABS"], "moq": 1000, "certifications": ["ISO 9001", "BSCI"], "lead_time_days": 35, "monthly_capacity": 40000, "current_load_pct": 62, "label": "fictional"},
     "audit_notes": ["Lighting specialist, in-house SMT line", "2 prior US crowdfunding projects shipped"], "past_performance": {"orders_completed": 48, "on_time_rate_pct": 88, "defect_rate_pct": 1.4, "label": "fictional"}, "label": "fictional", "fictional": True},
    {"id": "f_silverfern", "name": "Silverfern Lighting Works (fictional)", "region": "Shenzhen, Guangdong", "archetype": "fast/expensive", "personality": "Fast and premium: low MOQ, short lead time, rarely moves on price.",
     "capacity": {"processes": ["injection_molding", "cnc", "pcba", "assembly"], "materials": ["PC/ABS", "PC", "Aluminium 6063"], "moq": 500, "certifications": ["ISO 9001", "ISO 14001"], "lead_time_days": 25, "monthly_capacity": 20000, "current_load_pct": 78, "label": "fictional"},
     "audit_notes": ["Prototype-to-production shop", "Strong in anodised aluminium"], "past_performance": {"orders_completed": 71, "on_time_rate_pct": 94, "defect_rate_pct": 0.9, "label": "fictional"}, "label": "fictional", "fictional": True},
    {"id": "f_kestrel", "name": "Kestrel Bay Manufacturing (fictional)", "region": "Dongguan, Guangdong", "archetype": "cheap/slow", "personality": "Cheapest, high MOQ, long lead time, outsources finishing.",
     "capacity": {"processes": ["injection_molding", "sheet_metal", "assembly"], "materials": ["PC/ABS", "ABS", "SPCC steel"], "moq": 2000, "certifications": ["ISO 9001"], "lead_time_days": 45, "monthly_capacity": 80000, "current_load_pct": 55, "label": "fictional"},
     "audit_notes": ["High-volume consumer goods", "Anodising outsourced"], "past_performance": {"orders_completed": 120, "on_time_rate_pct": 76, "defect_rate_pct": 2.3, "label": "fictional"}, "label": "fictional", "fictional": True},
    {"id": "f_basalt", "name": "Basalt Precision Metal (fictional)", "region": "Suzhou, Jiangsu", "archetype": "specialist (CNC metal)", "personality": "Metal specialist; declines plastic-heavy projects.",
     "capacity": {"processes": ["cnc", "die_casting", "sheet_metal"], "materials": ["Aluminium 6061", "Zinc alloy", "Stainless steel"], "moq": 300, "certifications": ["ISO 9001", "IATF 16949"], "lead_time_days": 30, "monthly_capacity": 15000, "current_load_pct": 70, "label": "fictional"},
     "audit_notes": ["Automotive-grade QA"], "past_performance": {"orders_completed": 35, "on_time_rate_pct": 91, "defect_rate_pct": 0.7, "label": "fictional"}, "label": "fictional", "fictional": True},
]

matching = base(
    stage=7,
    factory_pack_id="fp_desk_lamp_v1",
    queries=[
        {"process": "injection_molding", "material": "PC/ABS", "quantity": 2000, "certifications_required": ["ISO 9001"], "deadline": "2027-01-05"},
        {"process": "pcba", "material": "FR-4", "quantity": 2000, "certifications_required": [], "deadline": "2027-01-05"},
    ],
    shortlist=[
        {"rank": 1, "factory_id": "f_orchid", "factory_name": FACTORIES[0]["name"], "score": lv(86, "score/100", "fictional", "Scored on demo data"),
         "score_breakdown": [
             {"criterion": "process_fit", "score": 1.0, "weight": 0.35, "note": "Molding + SMT + assembly under one roof"},
             {"criterion": "moq", "score": 1.0, "weight": 0.15, "note": "MOQ 1,000 ≤ 2,000"},
             {"criterion": "certifications", "score": 1.0, "weight": 0.15, "note": "ISO 9001 + BSCI"},
             {"criterion": "load", "score": 0.7, "weight": 0.15, "note": "62% loaded"},
             {"criterion": "lead_time", "score": 0.5, "weight": 0.2, "note": "35 days"}],
         "reasons": ["Only candidate doing molding, PCBA and assembly in-house", "Lighting track record", "Capacity available (62% load)"]},
        {"rank": 2, "factory_id": "f_silverfern", "factory_name": FACTORIES[1]["name"], "score": lv(78, "score/100", "fictional", "Scored on demo data"),
         "score_breakdown": [
             {"criterion": "process_fit", "score": 1.0, "weight": 0.35, "note": "Molding + CNC + PCBA"},
             {"criterion": "moq", "score": 1.0, "weight": 0.15, "note": "MOQ 500"},
             {"criterion": "certifications", "score": 1.0, "weight": 0.15, "note": "ISO 9001 + 14001"},
             {"criterion": "load", "score": 0.3, "weight": 0.15, "note": "78% loaded"},
             {"criterion": "lead_time", "score": 0.9, "weight": 0.2, "note": "25 days"}],
         "reasons": ["Fastest lead time", "In-house anodising", "Busy: 78% load"]},
        {"rank": 3, "factory_id": "f_kestrel", "factory_name": FACTORIES[2]["name"], "score": lv(71, "score/100", "fictional", "Scored on demo data"),
         "score_breakdown": [
             {"criterion": "process_fit", "score": 0.6, "weight": 0.35, "note": "No PCBA in-house"},
             {"criterion": "moq", "score": 1.0, "weight": 0.15, "note": "MOQ 2,000 = order size"},
             {"criterion": "certifications", "score": 0.7, "weight": 0.15, "note": "ISO 9001 only"},
             {"criterion": "load", "score": 0.8, "weight": 0.15, "note": "55% loaded"},
             {"criterion": "lead_time", "score": 0.2, "weight": 0.2, "note": "45 days"}],
         "reasons": ["Lowest expected price", "Long lead time", "PCBA must be subcontracted"]},
    ],
)

# ----------------------------------------------------------------------------- stage 8

def q_tiers(mult: float) -> list[dict]:
    return [{"quantity": t["quantity"], "unit_price_usd": round(t["unit_cost"]["value"] * mult, 2)} for t in tiers]


rfqs = [{"id": f"rfq_{f}", "project_id": PID, "factory_id": f"f_{f}", "factory_pack_id": "fp_desk_lamp_v1", "quantities": TIERS, "status": "quoted", "created_at": T0.isoformat(), "label": "fictional"} for f in ("orchid", "silverfern", "kestrel")]
rfqs[0]["status"] = "accepted"
quotes = [
    {"id": "qt_orchid_v1", "rfq_id": "rfq_orchid", "factory_id": "f_orchid", "version": 1, "tiers": q_tiers(1.10), "tooling_usd": 9900, "moq": 1000, "lead_time_days": 35, "payment_terms": "30% deposit / 70% before shipment", "exceptions": [], "status": "superseded", "created_at": T0.isoformat(), "label": "fictional"},
    {"id": "qt_silverfern_v1", "rfq_id": "rfq_silverfern", "factory_id": "f_silverfern", "version": 1, "tiers": q_tiers(1.22), "tooling_usd": 11500, "moq": 500, "lead_time_days": 25, "payment_terms": "50% deposit / 50% before shipment", "exceptions": ["Price valid 15 days"], "status": "rejected", "created_at": T0.isoformat(), "label": "fictional"},
    {"id": "qt_kestrel_v1", "rfq_id": "rfq_kestrel", "factory_id": "f_kestrel", "version": 1, "tiers": q_tiers(0.98), "tooling_usd": 8800, "moq": 2000, "lead_time_days": 45, "payment_terms": "30% deposit / 70% before shipment", "exceptions": ["Anodising outsourced (+5 days)", "PCBA subcontracted"], "status": "rejected", "created_at": T0.isoformat(), "label": "fictional"},
    {"id": "qt_orchid_v2", "rfq_id": "rfq_orchid", "factory_id": "f_orchid", "version": 2, "tiers": q_tiers(1.04), "tooling_usd": 9400, "moq": 1000, "lead_time_days": 35, "payment_terms": "30% deposit / 70% before shipment", "exceptions": [], "status": "accepted", "created_at": T0.isoformat(), "label": "fictional"},
]
FINAL_FOB = next(t["unit_price_usd"] for t in quotes[3]["tiers"] if t["quantity"] == REF_Q)
FINAL_TOOLING = 9400.0


def turn(i, rfq, fac, spk, msg, cn=None, qid=None, changes=None, why=None):
    return {"id": f"t{i}", "rfq_id": rfq, "factory_id": fac, "turn": i, "speaker": spk, "message": msg, "message_cn": cn, "quote_id": qid, "proposed_changes": changes or {}, "rationale": why, "created_at": (T0 + timedelta(minutes=i)).isoformat(), "label": "fictional"}


o1 = quotes[0]["tiers"][1]["unit_price_usd"]
transcript = [
    turn(1, "rfq_orchid", "f_orchid", "platform_agent", "RFQ sent with Factory Pack fp_desk_lamp_v1: 500 / 2,000 / 10,000 units, US + EU certifications.", "已发送询价及工厂资料包 fp_desk_lamp_v1：500 / 2,000 / 10,000 台，需美国及欧盟认证。"),
    turn(2, "rfq_silverfern", "f_silverfern", "platform_agent", "RFQ sent with Factory Pack fp_desk_lamp_v1.", "已发送询价及工厂资料包 fp_desk_lamp_v1。"),
    turn(3, "rfq_kestrel", "f_kestrel", "platform_agent", "RFQ sent with Factory Pack fp_desk_lamp_v1.", "已发送询价及工厂资料包 fp_desk_lamp_v1。"),
    turn(4, "rfq_orchid", "f_orchid", "factory_agent", f"Quote v1: ${o1} at 2,000, tooling $9,900, 35 days, 30/70.", qid="qt_orchid_v1"),
    turn(5, "rfq_silverfern", "f_silverfern", "factory_agent", f"Quote: ${quotes[1]['tiers'][1]['unit_price_usd']} at 2,000, tooling $11,500, 25 days, 50/50.", qid="qt_silverfern_v1"),
    turn(6, "rfq_kestrel", "f_kestrel", "factory_agent", f"Quote: ${quotes[2]['tiers'][1]['unit_price_usd']} at 2,000, tooling $8,800, 45 days. PCBA subcontracted.", qid="qt_kestrel_v1"),
    turn(7, "rfq_orchid", "f_orchid", "platform_agent", f"Counter: firm 2,000-unit PO if unit price moves to ${round(o1 * 0.92, 2)} and tooling to $9,000. Kestrel is cheaper but subcontracts PCBA.", "还价：若单价降至相应水平、模具费降至9,000美元，我们将确认2,000台订单。", qid="qt_orchid_v1", changes={"unit_price_2000": round(o1 * 0.92, 2), "tooling_usd": 9000}, why="Orchid has the best process fit; use Kestrel's price as anchor."),
    turn(8, "rfq_orchid", "f_orchid", "factory_agent", f"Revised v2: ${FINAL_FOB} at 2,000, tooling $9,400, lead time unchanged at 35 days.", qid="qt_orchid_v2"),
    turn(9, "rfq_orchid", "f_orchid", "platform_agent", "Recommendation sent to founder: accept Orchid v2.", why="Best total landed cost after risk: in-house PCBA, 88% on-time, 30/70 terms."),
    turn(10, "rfq_orchid", "f_orchid", "user", "Approved."),
]

negotiation = base(
    stage=8,
    rfqs=rfqs,
    quotes=quotes,
    transcript=transcript,
    recommendation={"factory_id": "f_orchid", "quote_id": "qt_orchid_v2", "rationale": "Best process fit (molding + PCBA + assembly in-house), 30/70 terms, 5.5% below its first quote; Kestrel is cheaper per unit but subcontracts PCBA and ships 10 days later."},
    user_approved=True,
    final_terms={"factory_id": "f_orchid", "quote_id": "qt_orchid_v2", "quantity": REF_Q, "unit_price": usd(FINAL_FOB, "fictional", "Negotiated quote v2 — demo data"), "tooling": usd(FINAL_TOOLING, "fictional", "Negotiated quote v2 — demo data"), "moq": 1000, "lead_time_days": lv(35, "days", "fictional", "Quote v2 — demo data"), "payment_terms": "30% deposit / 70% before shipment"},
)

# ----------------------------------------------------------------------------- stage 9

D = date(2026, 10, 5)


def ms(i, name, kind, start, days, deps=(), pay=None, notes=None):
    s = D + timedelta(days=start)
    return {"id": i, "name": name, "kind": kind, "start_date": s.isoformat(), "end_date": (s + timedelta(days=days)).isoformat(), "duration_days": lv(days, "days", "estimate", "Planner default from quote lead times"), "depends_on": list(deps), "payment": pay, "notes": notes}


cash = {n: v for n, v, _, _ in cash_components}
milestones = [
    ms("m1", "PO + tooling kickoff", "deposit", 0, 1, pay=usd(cash["Tooling"] * 0.5, src="50% tooling at kickoff")),
    ms("m2", "Tooling T0 + first shots", "tooling_t0", 1, 35, ["m1"]),
    ms("m3", "T1 corrections", "tooling_t1", 36, 14, ["m2"], pay=usd(cash["Tooling"] * 0.5, src="50% tooling at T1 approval")),
    ms("m4", "Golden sample approval", "golden_sample", 50, 7, ["m3"], pay=usd(cash["Samples (T0, T1, golden)"], src="Sample rounds + express shipping")),
    ms("m5", "Certification testing (FCC, CE, IEC 62133-2)", "certification", 50, 28, ["m3"], pay=usd(cash["Certification"], src="Lab fees")),
    ms("m6", "Mass production (2,000 units)", "mass_production", 57, 28, ["m4"], pay=usd(cash["First production order (2,000 × FOB)"] * 0.3, src="30% deposit")),
    ms("m7", "Pre-shipment inspection", "pre_shipment_inspection", 85, 2, ["m6"], pay=lv(QC_COST, "USD", "estimate", "V-Trust rate (Sourced) × estimated man-days: 2 man-days × $268/man-day (V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26)")),
    ms("m8", "Balance + sea shipment", "shipment", 87, 32, ["m7"], pay=usd(cash["First production order (2,000 × FOB)"] * 0.7, src="70% balance before shipment")),
    ms("m9", "Delivered to US 3PL", "delivered", 119, 3, ["m8"]),
]
tooling_stage = base(
    stage=9,
    milestones=milestones,
    payment_schedule=[
        {"milestone_id": "m1", "description": "50% tooling", "pct_of_order": None, "amount": milestones[0]["payment"], "due_date": milestones[0]["start_date"]},
        {"milestone_id": "m3", "description": "50% tooling at T1 approval", "pct_of_order": None, "amount": milestones[2]["payment"], "due_date": milestones[2]["end_date"]},
        {"milestone_id": "m6", "description": "30% production deposit", "pct_of_order": 30, "amount": milestones[5]["payment"], "due_date": milestones[5]["start_date"]},
        {"milestone_id": "m8", "description": "70% balance before shipment", "pct_of_order": 70, "amount": milestones[7]["payment"], "due_date": milestones[7]["start_date"]},
    ],
)

# ----------------------------------------------------------------------------- stage 10

qc = base(
    stage=10,
    standard="ISO 2859-1 (ANSI/ASQ Z1.4)",
    inspection_level="General II",
    lot_size=REF_Q,
    sample_size=lv(125, "units", "estimate", "Per ISO 2859-1 table (edition not verified): code letter K for lot 1,201-3,200, level General II"),
    defects=[
        {"id": "c1", "severity": "critical", "description": "Cell swelling, exposed cell, or missing protection circuit", "spec_ref": "BOM e6 / DFM i5 / IEC 62133-2", "check_method": "Visual + over-discharge test on 5 units", "aql": 0},
        {"id": "c2", "severity": "critical", "description": "Charging over 4.25 V or port overheating (> 60 °C)", "spec_ref": "Electronics block b2 (TP4056)", "check_method": "Charge test with USB meter, 30 min", "aql": 0},
        {"id": "j1", "severity": "major", "description": "Head does not hold on stem / air gap out of 0.3 ± 0.1 mm", "spec_ref": "Tolerance: head/stem air gap", "check_method": "Feeler gauge + pull test", "aql": 2.5},
        {"id": "j2", "severity": "major", "description": "LED flicker or dead LED segment", "spec_ref": "Part p6 / LED bar b6", "check_method": "Power-on at 3 dimming levels", "aql": 2.5},
        {"id": "j3", "severity": "major", "description": "Anodising colour ΔE > 1.5 vs golden sample", "spec_ref": "Part p3 finish", "check_method": "Colorimeter vs golden sample", "aql": 2.5},
        {"id": "n1", "severity": "minor", "description": "Sink marks or flow lines on head housing", "spec_ref": "Part p1 / DFM m3 (measured wall)", "check_method": "Visual at 50 cm, D65 light", "aql": 4.0},
        {"id": "n2", "severity": "minor", "description": "Box print misregistration", "spec_ref": "Packaging k1", "check_method": "Visual", "aql": 4.0},
    ],
    inspection_man_days=lv(2, "man-days", "estimate", "125 samples + functional tests"),
    man_day_rate=lv(268, "USD", "sourced", "V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26"),
    inspection_cost=lv(QC_COST, "USD", "estimate", "V-Trust rate (Sourced) × estimated man-days: 2 man-days × $268/man-day (V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26)"),
    assumptions=[ASSUMPTIONS[3]],
)

# ----------------------------------------------------------------------------- stage 11

logistics = None  # live handler, computed below once every upstream stage exists

# ----------------------------------------------------------------------------- stage 12

financing = None  # live handler, computed below


# ----------------------------------------------------------------------------- stage 13

brand = base(
    stage=13,
    name_options=[
        {"name": "Magwick", "rationale": "Magnet + wick: the light head snaps on and off; coined, short, ownable. Trademark search needed before use."},
        {"name": "Orlune Column", "rationale": "Coined word evoking a small moon of light on a column; easy to spell. Trademark search needed before use."},
        {"name": "Pivra", "rationale": "Short coined name suggesting pivot and light; playful. Trademark search needed before use."},
    ],
    chosen_name=None,
    packaging={"box_type": "Rigid 2-piece box with moulded pulp insert", "dimensions": dims(360, 130, 70, "Product + 10 mm clearance"), "materials": ["1200 g greyboard", "FSC paper wrap", "Moulded pulp"], "printing": "1-colour black + spot UV logo", "contents": ["Lamp base + stem", "Magnetic head", "USB-C cable 1 m", "Quick start card"], "unit_cost": usd(0.90, src="Packaging BOM line k1")},
    landing_copy={"headline": "Light that follows you.", "subheadline": "A desk lamp whose head snaps off and goes where you go. 10 hours, one USB-C cable.", "bullets": ["Magnetic head detaches in one hand", "3 colour temperatures, touch dimming", "Anodised aluminium, weighted base"], "cta": "Reserve yours — €89"},
    shopify_listing={"channel": "shopify", "title": "Magwick — Magnetic Rechargeable Desk Lamp", "description": "Minimal aluminium desk lamp with a detachable magnetic LED head. USB-C rechargeable, up to 10 hours.", "bullets": ["Detachable magnetic head", "Up to 10 h battery", "3 colour temperatures"], "price": lv(89, "EUR", "estimate", "Founder target"), "keywords": ["desk lamp", "magnetic lamp", "rechargeable lamp"]},
    amazon_listing={"channel": "amazon", "title": "Magwick Magnetic Desk Lamp, Rechargeable LED Desk Light with Detachable Head, 3 Colour Modes, USB-C", "description": "Cordless LED desk lamp with a detachable magnetic head for reading, working and travel.", "bullets": ["DETACHABLE HEAD — snaps on and off magnetically", "10-HOUR BATTERY — USB-C charging", "3 COLOUR MODES — touch dimming", "PREMIUM BUILD — anodised aluminium"], "price": usd(TARGET_USD, src=f"€89 × {EUR_USD}"), "keywords": ["desk lamp", "rechargeable", "magnetic", "LED"]},
)

# ----------------------------------------------------------------------------- Factory Pack

factory_pack = {
    "id": "fp_desk_lamp_v1", "project_id": PID, "version": 1, "created_at": T0.isoformat(), "fallback": False,
    "product_name": brief["product_name"],
    "product_summary": brief["one_liner"] + " Target: 2,000 units first run, US + EU.",
    "product_summary_cn": "极简无线台灯，LED灯头通过磁吸固定在铝制灯杆上，可拆下作为便携灯使用。首批2,000台，目标市场：美国和欧盟。",
    "target_markets": brief["target_markets"],
    "spec": {"overall_dimensions": spec["overall_dimensions"], "weight": spec["weight"], "parts": PARTS, "tolerances": spec["tolerances"]},
    "cad_files": spec["cad_files"],
    "bom": bom,
    "dfm_alerts": dfm_issues,
    "certifications": certifications,
    "target_quantities": TIERS,
    "cost_estimate": tiers,
    "questions": [
        {"id": "fq1", "en": "Can you hold ±0.1 mm on the magnet pockets of the PC/ABS head housing?", "cn": "PC/ABS灯头外壳的磁铁槽能否保证±0.1 mm公差？"},
        {"id": "fq2", "en": "Please confirm the 18650 cell supplier and share its UN38.3 test summary and IEC 62133-2 report.", "cn": "请确认18650电芯供应商，并提供UN38.3测试摘要及IEC 62133-2报告。"},
        {"id": "fq3", "en": "What draft angle do you recommend on the MT-11010 textured faces?", "cn": "对于MT-11010纹理面，贵司建议的拔模角度是多少？"},
        {"id": "fq4", "en": "Is anodising of the aluminium stem done in-house, and what colour tolerance (ΔE) can you hold?", "cn": "铝灯杆的阳极氧化是否在厂内完成？可控制的色差(ΔE)是多少？"},
        {"id": "fq5", "en": "Quote tooling as single-cavity P20 steel with 100k shot life, and give the 2-cavity option.", "cn": "请按单腔P20钢模具（寿命10万模次）报价，并提供双腔方案价格。"},
    ],
    "assumption_register": ASSUMPTIONS,
}

project = {"id": PID, "name": "Magnetic Rechargeable Desk Lamp", "mode": "idea", "prompt": brief["prompt"], "pasted_bom": None, "example": "desk_lamp", "status": "active", "created_at": T0.isoformat(), "stage_status": {}}

_UP = {1: brief, 3: spec, 4: dfm, 5: costs, 6: production, 7: matching, 8: negotiation, 9: tooling_stage, 10: qc}
logistics = live_stage(11, project, _UP) | {"generated_at": T0.isoformat()}
financing = live_stage(12, project, {**_UP, 11: logistics}) | {"generated_at": T0.isoformat()}
FINAL_LANDED, est_landed = logistics["landed_cost_per_unit"]["value"], round(sum(x[1] for x in ref_landed), 2)
delta_pct = (FINAL_LANDED - est_landed) / est_landed * 100
cum = financing["total_cash"]["value"]
# stage 12 follows the approved stage 8 quote: equal to stage 5, or an explicit reconciliation note
assert logistics["reconciles_with_stage5"] and (financing["matches_stage5_total"] or financing["reconciliation_note"]), (logistics["reconciliation_note"], cum, TOTAL_CASH)

STAGES = {1: brief, 2: design, 3: spec, 4: dfm, 5: costs, 6: production, 7: matching, 8: negotiation, 9: tooling_stage, 10: qc, 11: logistics, 12: financing, 13: brand}


def dump(path: Path, model_cls, data) -> None:
    obj = model_cls.model_validate(data)  # validate before writing
    path.write_text(json.dumps(obj.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    NET.mkdir(exist_ok=True)
    dump(OUT / "project.json", A.Project, project)
    for n, data in STAGES.items():
        dump(OUT / f"{n:02d}_{A.STAGE_NAMES[n]}.json", A.ARTIFACT_MODELS[n], data)
    dump(OUT / "factory_pack.json", A.FactoryPack, factory_pack)
    factories = [A.Factory.model_validate(f).model_dump(mode="json") for f in FACTORIES]
    (NET / "factories.json").write_text(json.dumps(factories, indent=2, ensure_ascii=False) + "\n")
    rfq_views = [
        A.RFQWithQuotes.model_validate({"rfq": r, "product_name": brief["product_name"], "quotes": [q for q in quotes if q["rfq_id"] == r["id"]]}).model_dump(mode="json")
        for r in rfqs
    ]
    (NET / "rfqs.json").write_text(json.dumps(rfq_views, indent=2, ensure_ascii=False) + "\n")
    print(f"total cash {TOTAL_CASH} · curve {cum:.2f} · landed est {est_landed} vs final {FINAL_LANDED} ({delta_pct:+.1f}%) · breakeven {breakeven:.0f}")


if __name__ == "__main__":
    main()
