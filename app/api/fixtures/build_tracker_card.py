"""Hand-authored source of the tracker card fixture set (PRD Appendix A, prompt 2 — the "simple electronic accessory").

Written as Python so every figure is computed once and stays consistent across stages
(stage 5 total cash = stage 12 cash curve; stage 11 landed cost reconciles with stage 5).
Regenerate the JSON files:  uv run python -m api.fixtures.build_tracker_card

Honesty notes:
- The 8 electronic BOM lines marked `sourced` carry REAL LCSC prices and stock: jlcsearch (tscircuit) query on
  2026-09-26, price break for the order quantity at the 500-unit tier. Everything else is an `estimate` with its assumption.
- DFM 'measured' findings are the real output of api/dfm/measure.py on the committed CAD
  (api/cad/prebuilt/demo_tracker_card/enclosure.step = direction d3, the card slab), recomputed on every run.
  Freight, factories, quotes = fictional demo data (factory ids reused from network/factories.json).
- HTS 8517.62.00.90 general rate Free is Sourced (USITC, api/costs/data/hts.json); Section 301 stays an Estimate
  (confirm with a customs broker). Certification costs and the lithium primary-cell price are estimates.
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

HERE = Path(__file__).parent
OUT = HERE / "tracker_card"
NET = HERE / "network"
PID = "demo_tracker_card"
T0 = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
LCSC_SRC = "LCSC price via jlcsearch, 2026-09-26"


def lcsc_src(pn: str | None, what: str = "price") -> str:
    """Sourced LCSC value: jlcsearch query date + the product page URL."""
    return f"LCSC {what} via jlcsearch, snapshot 2026-09-26, https://www.lcsc.com/product-detail/{pn}.html"
HTS = json.loads((HERE.parent / "costs" / "data" / "hts.json").read_text())["lines"]["tracker_card"]
PREBUILT = HERE.parent / "cad" / "prebuilt" / PID


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


# ----------------------------------------------------------------------------- factories (ids reused from the network fixtures)

_fac = {f["id"]: f for f in json.loads((NET / "factories.json").read_text())}
_ids = [i for i in ("f_silverfern", "f_orchid", "f_kestrel") if i in _fac] or list(_fac)[:3]
assert len(_ids) >= 3, "network/factories.json needs at least 3 factories"
FA, FB, FC = _ids[:3]  # ranked 1, 2, 3 for this product
NAME = {i: _fac[i]["name"] for i in (FA, FB, FC)}
CAP = {i: _fac[i]["capacity"] for i in (FA, FB, FC)}
SHORT = {i: i.removeprefix("f_") for i in (FA, FB, FC)}

# ----------------------------------------------------------------------------- assumptions register

TARGET_USD = 24.99
VF = 0.92
TIERS = [500, 2000, 10000]
REF_Q = 2000
ASSEMBLY_500 = 0.85

ASSUMPTIONS = [
    {"id": "a1", "text": f"Founder target retail price ${TARGET_USD} (comparable wallet trackers retail in the $20-35 range, not verified)", "label": "estimate", "source": None, "stage": 1},
    {"id": "a2", "text": "Volume curve: unit cost × 0.92 per tier step (500 → 2,000 → 10,000)", "label": "estimate", "source": "Demo assumption (PRD §11)", "stage": 5},
    {"id": "a3", "text": "Final assembly (ultrasonic weld, cell attach, flash + RF test) $0.85 per unit at 500", "label": "estimate", "source": None, "stage": 5},
    {"id": "a4", "text": "Pre-shipment inspection $268 per man-day", "label": "sourced", "source": "V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26", "stage": 10},
    {"id": "a5", "text": "Platform/agent fee 7% of FOB (benchmark 5-10%)", "label": "estimate", "source": "Dragon Sourcing benchmark 5-10%", "stage": 11},
    {"id": "a6", "text": f"HTS {HTS['code']} (Bluetooth data transmission apparatus): general rate Free", "label": "sourced", "source": f"{HTS['general_source']} — {HTS['source_url']}", "stage": 11},
    {"id": "a7", "text": "IEEPA duties not collected since 24/02/2026; de minimis suspended; Section 122 surcharge off (toggle)", "label": "sourced", "source": "CBP CSMS 67834313 (https://content.govdelivery.com/accounts/USDHSCBP/bulletins/40b11c9); Federal Register 24/06/2026", "stage": 11},
    {"id": "a8", "text": "Sea LCL Shenzhen → Los Angeles, $0.12/unit (minimum-charge dominated), 32 days door to 3PL", "label": "fictional", "source": "demo data", "stage": 11},
    {"id": "a9", "text": "Thin-wall PC single-cavity molds $3,000-4,500 each (small-mold range $1,000-3,000 plus thin-wall premium)", "label": "estimate", "source": "Zetar Mold 2026 range $1,000-3,000 (vendor, medium) + thin-wall premium assumption", "stage": 5},
    {"id": "a10", "text": "Measured DFM checks assume a straight two-half tool pulling along ±Z (split line in the XY plane)", "label": "estimate", "source": "api/dfm/measure.py on api/cad/prebuilt/demo_tracker_card/enclosure.step", "stage": 4},
    {"id": "a11", "text": "Certification costs (FCC 15C, CE RED, Bluetooth SIG listing, UN38.3) are lab-quote ranges, not quotes", "label": "estimate", "source": None, "stage": 4},
    {"id": "a13", "text": f"Section 301 China {HTS['section_301_rate_pct']:g}% on HTS {HTS['code']} — confirm classification and list coverage with a customs broker", "label": "estimate", "source": HTS["section_301_source"], "stage": 11},
    {"id": "a12", "text": "Thin lithium primary cell (3 V pouch, non-replaceable) $0.60 at 2k MOQ, branded supplier with UN38.3 report", "label": "estimate", "source": None, "stage": 5},
]
AS = {a["id"]: a for a in ASSUMPTIONS}

# ----------------------------------------------------------------------------- stage 1

brief = base(
    stage=1,
    mode="idea",
    prompt="Bluetooth tracker card for wallets",
    product_name="Bluetooth Tracker Card for Wallets",
    one_liner="A wallet-card-sized Bluetooth tracker that rings your phone (and that your phone can ring), powered by a sealed thin primary cell for about two years.",
    category="ble_accessory",
    target_markets=["US", "EU"],
    target_retail_price=lv(TARGET_USD, "USD", "estimate", AS["a1"]["text"]),
    target_volumes=TIERS,
    key_features=["Wallet-card footprint, under 3 mm thick", "Bluetooth Low Energy 5: ring the card from the phone, ring the phone from the card", "Sealed thin lithium primary cell, no charging", "Physical button and status LED", "Piezo buzzer with acoustic port"],
    constraints=["Retail $24.99", "Must slide into a wallet card slot", "FCC Part 15C intentional radiator (US first)", "Lithium cell: UN38.3 transport test summary required"],
    has_battery=True,
    wireless=["BLE"],
    pasted_bom=[],
    clarifying_questions=[
        {"id": "q1", "topic": "markets", "question": "Which markets at launch?", "options": ["US", "EU", "UK"], "answer": "US + EU", "skipped": False},
        {"id": "q2", "topic": "volume", "question": "First production run size?", "options": ["500", "2,000", "10,000"], "answer": "2,000", "skipped": False},
        {"id": "q3", "topic": "target_price", "question": "Confirm target retail price?", "options": ["$19.99", "$24.99", "$29.99"], "answer": "$24.99", "skipped": False},
        {"id": "q4", "topic": "battery", "question": "Sealed disposable cell or rechargeable thin LiPo?", "options": ["Sealed primary cell", "Rechargeable LiPo"], "answer": "Sealed primary cell", "skipped": False},
        {"id": "q5", "topic": "wireless", "question": "BLE ring only, or also UWB precision finding?", "options": ["BLE only", "BLE + UWB"], "answer": None, "skipped": True},
    ],
    assumptions=[AS["a1"]],
)

# ----------------------------------------------------------------------------- stage 2

design = base(
    stage=2,
    directions=[
        {"id": "d1", "name": "Tag", "description": "Soft rounded tag with a keyring loop option — easier antenna layout, but too thick for a card slot.", "shape": "Rounded box, R10 corners", "material": "Polycarbonate (UL94 V-0)", "finish": "Matte VDI 24 texture, warm white", "dimensions": dims(60.0, 40.0, 14.0), "cad_parameters": {"family": 0, "length": 60, "width": 40, "height": 14, "fillet": 10, "edge_fillet": 2.5, "wall": 2.0}, "render_url": f"/files/{PID}/d1.png", "glb_url": f"/files/{PID}/d1.glb"},
        {"id": "d2", "name": "Puck", "description": "42 mm round puck for bags and keys; coin-cell friendly, not wallet-thin.", "shape": "Disc", "material": "Polycarbonate (UL94 V-0)", "finish": "Soft-touch paint, graphite", "dimensions": dims(42.0, 42.0, 11.0), "cad_parameters": {"family": 1, "length": 42, "width": 42, "height": 11, "edge_fillet": 2.5, "wall": 2.0}, "render_url": f"/files/{PID}/d2.png", "glb_url": f"/files/{PID}/d2.glb"},
        {"id": "d3", "name": "Card", "description": "Flat ID-1 footprint card, 2.8 mm thick, two ultrasonic-welded 0.5 mm polycarbonate shells, button on the short edge.", "shape": "Rounded rectangle slab, R3.5 corners", "material": "Polycarbonate (UL94 V-0)", "finish": "Matte VDI 24 texture, black", "dimensions": dims(85.6, 54.0, 2.8), "cad_parameters": {"family": 2, "length": 85.6, "width": 54.0, "height": 2.8, "fillet": 3.5, "edge_fillet": 0.3, "wall": 0.5, "draft_deg": 1.0, "boss_count": 0}, "render_url": f"/files/{PID}/d3.png", "glb_url": f"/files/{PID}/d3.glb"},
    ],
    chosen_direction_id="d3",
    assumptions=[
        {"id": "a2_render", "label": "estimate", "text": "AI concept render — illustrative, not the CAD", "source": None, "stage": 2},
        {"id": "a2_hero", "label": "estimate", "text": f"Rendered from the CAD: /files/{PID}/hero_d1.png, /files/{PID}/hero_d2.png, /files/{PID}/hero_d3.png", "source": None, "stage": 2},
    ],
)

# ----------------------------------------------------------------------------- stage 3 (spec + BOM)

BOM_RAW = [
    # id, part, category, qty, unit price, label, source, lcsc, stock, risk, alternative
    ("e1", "BLE 5 SoC nRF52810 (WLCSP-33, 2.5×2.5 mm)", "electronic", 1, 1.5745, "sourced", LCSC_SRC, "C3606661", 13709, ("medium", ["Single source (Nordic)", "WLCSP 0.4 mm pitch assembly", "LCSC stock 13.7k"]), "nRF52810 QFN-32 (C519278, stock 1,322) at higher thickness"),
    ("e2", "Crystal 32.768 kHz SMD3215", "electronic", 1, 0.1034, "sourced", LCSC_SRC, "C32346", 444985, ("low", ["Stock 445k", "Multi-source"]), "Any 32.768 kHz 9 pF SMD3215"),
    ("e3", "Crystal 32 MHz SMD2016", "electronic", 1, 0.0668, "sourced", LCSC_SRC, "C718072", 60898, ("low", ["Stock 61k", "Multi-source"]), "XL7EL89COI-111YLC-32M (C2965584)"),
    ("e4", "2.4 GHz chip antenna 3.2×1.6 mm", "electronic", 1, 0.0894, "sourced", LCSC_SRC, "C127629", 77484, ("low", ["Stock 77k", "Detuning by nearby metal to validate"]), "Printed PCB antenna (no BOM cost, larger keep-out)"),
    ("e5", "Tactile switch SMD 4.6×1.8 mm", "electronic", 1, 0.0196, "sourced", LCSC_SRC, "C393942", 444478, ("low", ["Stock 444k"]), "SH-1806SA-A3DW-04 (C22383476)"),
    ("e6", "Status LED 0402 white", "electronic", 1, 0.0087, "sourced", LCSC_SRC, "C20613596", 602590, ("low", ["Stock 603k"]), "XL-1005UGC green (C965793)"),
    ("e7", "MLCC 100 nF 0402 (decoupling)", "electronic", 6, 0.0047, "sourced", LCSC_SRC, "C1525", 16407331, ("low", ["LCSC basic part", "Stock 16.4M"]), "CL05B104KB54PNC (C307331)"),
    ("e8", "MLCC 1 µF 0402", "electronic", 2, 0.0122, "sourced", LCSC_SRC, "C52923", 4519174, ("low", ["LCSC basic part", "Stock 4.5M"]), "TCC0402X5R105M6R3AT (C2887021)"),
    ("e9", "Antenna matching + RF passives 0402 (6 pcs)", "electronic", 1, 0.03, "estimate", "Six 0402 RF passives (C/L) at ~$0.005 each; values set at RF tuning", None, None, None),
    ("e10", "Piezo disc buzzer Ø12 mm, 0.22 mm brass plate", "electronic", 1, 0.10, "estimate", "Catalogue piezo element, 10k pcs; thin SMD variant not selected", None, ("medium", ["Loudness inside sealed shells not validated"]), "Thin SMD magnetic transducer, higher cost"),
    ("e11", "Thin lithium primary pouch cell 3 V, ~1 mm", "electronic", 1, 0.60, "estimate", AS["a12"]["text"], None, ("high", ["Sealed lithium cell: UN38.3 report required", "Counterfeit/unbranded cell risk", "Air-freight restrictions (UN3090/3091)"]), "Rechargeable thin LiPo + charge IC (adds cost, IEC 62133-2, USB/Qi charge access)"),
    ("e12", "Control PCB 4-layer 0.6 mm ENIG", "electronic", 1, 0.45, "estimate", "Bare PCB, 2k pcs, 90×55 mm panel share", None, ("low", []), None),
    ("m1", "Top shell, PC, 0.5 mm wall, textured", "mechanical", 1, 0.14, "estimate", "Part weight 2.6 g × resin + cycle cost", None, None, None),
    ("m2", "Bottom shell, PC, 0.5 mm wall", "mechanical", 1, 0.14, "estimate", "Part weight 2.6 g × resin + cycle cost", None, None, None),
    ("m3", "Printed PET graphic overlay", "mechanical", 1, 0.06, "estimate", "Die-cut 85 × 54 mm, 1-colour print, PSA back", None, None, None),
    ("m4", "Acoustic mesh + adhesive ring", "mechanical", 1, 0.02, "estimate", "Die-cut, 5 mm", None, None, None),
    ("m5", "Cell tab foil + adhesive tape", "mechanical", 1, 0.03, "estimate", "Nickel tab + Kapton", None, None, None),
    ("k1", "Folding carton (blister-free) 95×62×6 mm", "packaging", 1, 0.18, "estimate", "Paperboard 350 g, 1-colour print", None, None, None),
    ("k2", "Quick-start card", "packaging", 1, 0.03, "estimate", "Single-sheet insert", None, None, None),
]

bom = []
stock_by_id: dict[str, int] = {}
for row in BOM_RAW:
    if len(row) == 10:  # unsourced lines have no LCSC stock
        row = row[:8] + (None,) + row[8:]
    bid, part, cat, qty, price, label, src, lcsc, stock, risk, alt = row
    src = lcsc_src(lcsc) if label == "sourced" else src
    if stock is not None:
        stock_by_id[bid] = stock
    bom.append({
        "id": bid, "part": part, "category": cat, "qty": qty,
        "description": "Real LCSC price at the ≥500-unit break, snapshot 2026-09-26" if label == "sourced" else None,
        "manufacturer_pn": None, "lcsc_pn": lcsc,
        "unit_cost_est": lv(price, "USD", label, src),
        "risk": {"level": risk[0], "reasons": risk[1]} if risk else None,
        "alternative": alt,
    })

PARTS = [
    {"id": "p1", "name": "Top shell", "material": "Polycarbonate (UL94 V-0)", "finish": "VDI 24 matte texture, black", "process_hint": "injection_molding", "tolerance": "±0.05 mm on weld ridge, 2.8 ± 0.15 mm stack", "dimensions": dims(85.6, 54.0, 1.4), "wall_thickness": mm(0.5), "quantity": 1},
    {"id": "p2", "name": "Bottom shell", "material": "Polycarbonate (UL94 V-0)", "finish": "VDI 24 matte texture, black", "process_hint": "injection_molding", "tolerance": "±0.05 mm on weld groove", "dimensions": dims(85.6, 54.0, 1.4), "wall_thickness": mm(0.5), "quantity": 1},
    {"id": "p3", "name": "PCBA (BLE SoC + antenna)", "material": "FR-4 4-layer 0.6 mm", "finish": "ENIG, lead-free reflow", "process_hint": "pcba", "tolerance": "PCB thickness 0.6 ± 0.06 mm", "dimensions": dims(44.0, 48.0, 1.0), "wall_thickness": None, "quantity": 1},
    {"id": "p4", "name": "Thin lithium primary cell", "material": "Li-MnO2 pouch, foil", "finish": "Laminate", "process_hint": "assembly", "tolerance": "Thickness 1.0 ± 0.1 mm", "dimensions": dims(40.0, 30.0, 1.0), "wall_thickness": None, "quantity": 1},
    {"id": "p5", "name": "Graphic overlay", "material": "PET 0.05 mm + PSA", "finish": "1-colour print", "process_hint": "other", "tolerance": "±0.3 mm registration", "dimensions": dims(84.0, 52.0, 0.1), "wall_thickness": None, "quantity": 1},
]

spec = base(
    stage=3,
    product_name="Bluetooth Tracker Card for Wallets",
    direction_id="d3",
    overall_dimensions=_measured_dims("d3.glb"),
    weight=lv(11, "g", "estimate", "Shells 2×2.6 g + PCBA 2 g + cell 3 g + overlay/misc 0.8 g"),
    parts=PARTS,
    electronics_blocks=[
        {"id": "b1", "name": "BLE SoC (nRF52810)", "function": "BLE 5 radio, application logic, buzzer PWM"},
        {"id": "b2", "name": "Chip antenna", "function": "2.4 GHz radiation, matched to 50 Ω"},
        {"id": "b3", "name": "Primary cell 3 V", "function": "Sealed energy storage, no regulator (SoC runs 1.7-3.6 V)"},
        {"id": "b4", "name": "Piezo buzzer", "function": "Audible ring via GPIO PWM"},
        {"id": "b5", "name": "Button", "function": "Ring phone / pairing"},
        {"id": "b6", "name": "Status LED", "function": "Pairing and battery indication"},
        {"id": "b7", "name": "Crystals 32 MHz + 32.768 kHz", "function": "RF clock + low-power timekeeping"},
    ],
    electronics_edges=[
        {"source": "b3", "target": "b1", "signal": "VBAT 3 V"},
        {"source": "b7", "target": "b1", "signal": "Clocks"},
        {"source": "b1", "target": "b2", "signal": "RF 2.4 GHz"},
        {"source": "b1", "target": "b4", "signal": "PWM"},
        {"source": "b5", "target": "b1", "signal": "GPIO wake"},
        {"source": "b1", "target": "b6", "signal": "GPIO"},
    ],
    bom=bom,
    tolerances=["General ISO 2768-f on shells", "Stack thickness 2.8 ± 0.15 mm after welding", "Weld ridge/groove ±0.05 mm"],
    cad_files=[
        {"format": "glb", "url": f"/files/{PID}/d3.glb", "description": "Full product — materials (viewer model of direction d3)", "size_bytes": (PREBUILT / "d3.glb").stat().st_size},
        {"format": "step", "url": f"/files/{PID}/enclosure.step", "description": "Moulded parts (DFM) — Card enclosure B-rep (build123d): top + bottom shell 85.6 × 54 × 2.8 mm, 0.5 mm wall, 1° draft — open in any CAD tool", "size_bytes": (PREBUILT / "enclosure.step").stat().st_size},
        {"format": "stl", "url": f"/files/{PID}/enclosure.stl", "description": "Moulded parts (DFM) — Card enclosure mesh for 3D-printed prototypes", "size_bytes": (PREBUILT / "enclosure.stl").stat().st_size},
        {"format": "glb", "url": f"/files/{PID}/enclosure.glb", "description": "Moulded parts (DFM) — Card enclosure model for the 3D viewer", "size_bytes": (PREBUILT / "enclosure.glb").stat().st_size},
    ],
)

# ----------------------------------------------------------------------------- stage 4

# Real measured output on the committed CAD (top shell p1: textured polycarbonate, pull along +Z).
MEASURED = [
    {**i.model_dump(mode="json"), "id": f"m{k}"}
    for k, i in enumerate(measure(PREBUILT / "enclosure.step", (0, 0, 1), finish=PARTS[0]["finish"], material=PARTS[0]["material"], part_id="p1"), 1)
]
dfm_issues = [
    *MEASURED,
    {"id": "i4", "severity": "critical", "category": "assembly", "method": "ai_reviewed", "part_id": "p4", "description": "Ultrasonic welding of the shells puts heat and vibration next to a sealed lithium pouch cell; puncture or short-circuit risk.", "fix": "Keep the cell ≥3 mm from the weld line (validate with the cell supplier), add a cell pocket rib, and run a weld-energy test with a dummy cell.", "rule_citation": "IEC 60086-4 (lithium battery safety) and cell supplier handling guideline — to be confirmed with supplier datasheet", "measurement": None, "resolved": False, "resolution": None},
    {"id": "i5", "severity": "major", "category": "other", "method": "ai_reviewed", "part_id": "p3", "description": "Chip antenna detunes near metal (RFID-shield cards, metal wallets) and near the cell foil; range may drop in a real wallet.", "fix": "Keep a ground-free keep-out under the antenna, place it at the short edge away from the cell, tune matching in a wallet with typical cards.", "rule_citation": "Chip antenna vendor layout guideline (ground keep-out) — RF design practice", "measurement": None, "resolved": False, "resolution": None},
    {"id": "i6", "severity": "major", "category": "tolerance", "method": "ai_reviewed", "part_id": "p1", "description": "Stack tolerance of shells + PCB + cell + weld collapse can push total thickness above the wallet-slot limit.", "fix": "Specify 2.8 ± 0.15 mm after welding, define weld collapse (0.15 mm) and add a thickness check in QC.", "rule_citation": "Ultrasonic welding energy-director design guide (collapse 0.1-0.2 mm) — Branson/Emerson plastics joining handbook", "measurement": None, "resolved": False, "resolution": None},
    {"id": "i7", "severity": "minor", "category": "assembly", "method": "ai_reviewed", "part_id": "p2", "description": "Sealed shells attenuate the piezo buzzer; the card may be too quiet to find.", "fix": "Add a 1.5 mm sound port over the buzzer with acoustic mesh (BOM m4) and test SPL on the golden sample.", "rule_citation": "Piezo sounder acoustic-port practice — buzzer vendor application notes", "measurement": None, "resolved": False, "resolution": None},
]

certifications = [
    {"market": "US", "standard": "FCC Part 15C (intentional radiator, 2.4 GHz BLE) + 15B", "applies_because": "Chip-down BLE radio, no pre-certified module", "required": True, "cost_est": usd(4500, src="Accredited lab quote range, demo assumption"), "lead_time_weeks": lv(5, "weeks", "estimate", "Typical lab queue")},
    {"market": "EU", "standard": "CE — RED 2014/53/EU (EN 300 328, EN 301 489, EN 62368-1), RoHS", "applies_because": "Radio equipment sold in the EU", "required": True, "cost_est": usd(5500, src="Accredited lab quote range, demo assumption"), "lead_time_weeks": lv(6, "weeks", "estimate", "Typical lab queue")},
    {"market": "Global", "standard": "Bluetooth SIG qualification / listing (Declaration ID)", "applies_because": "Product is marketed as a Bluetooth device", "required": True, "cost_est": usd(3000, src="Fee depends on SIG membership tier; assumption incl. listing help"), "lead_time_weeks": lv(2, "weeks", "estimate", "Listing after test reports")},
    {"market": "Global", "standard": "UN38.3 (lithium transport) summary + IEC 60086-4", "applies_because": "Contains a sealed lithium metal (primary) cell", "required": True, "cost_est": usd(1200, src="Cell-level test summary from the cell supplier; assumption"), "lead_time_weeks": lv(4, "weeks", "estimate", "Cell supplier test queue")},
    {"market": "US", "standard": "16 CFR 1263 (Reese's Law, button/coin cells) — verify applicability", "applies_because": "Applies to consumer products with a button or coin cell; our cell is a sealed flat pouch — to confirm with counsel/lab", "required": False, "cost_est": usd(0, src="No test cost if the pouch cell is out of scope; assumption"), "lead_time_weeks": lv(1, "weeks", "estimate", "Applicability review")},
]

dfm = base(
    stage=4,
    issues=dfm_issues,
    component_risks=[
        {"bom_item_id": "e11", "part": "Thin lithium primary pouch cell 3 V", "level": "high", "reasons": ["UN38.3 report required", "Counterfeit/unbranded cell risk", "Air-freight restrictions (UN3090/3091)"], "alternatives": ["Branded thin primary cell with UN38.3 + IEC 60086-4 reports", "Rechargeable thin LiPo (adds charge IC, IEC 62133-2)"], "stock": None, "lead_time_weeks": lv(6, "weeks", "estimate", "Branded cell lead time")},
        {"bom_item_id": "e1", "part": "BLE 5 SoC nRF52810 (WLCSP-33)", "level": "medium", "reasons": ["Single source (Nordic)", "WLCSP 0.4 mm pitch assembly", "Stock 13.7k vs 2k order"], "alternatives": ["nRF52810 QFN-32 (C519278, stock 1,322) at higher thickness", "nRF52805 WLCSP (C3606954, stock 1)"], "stock": lv(13709, "units", "sourced", lcsc_src("C3606661", "stock")), "lead_time_weeks": None},
        {"bom_item_id": "e10", "part": "Piezo disc buzzer", "level": "medium", "reasons": ["Loudness in sealed shells not validated"], "alternatives": ["Thin SMD magnetic transducer"], "stock": None, "lead_time_weeks": None},
        {"bom_item_id": "e4", "part": "2.4 GHz chip antenna", "level": "low", "reasons": ["Stock 77k", "Detuning to validate in wallet"], "alternatives": ["Printed PCB antenna"], "stock": lv(77484, "units", "sourced", lcsc_src("C127629", "stock")), "lead_time_weeks": None},
    ],
    certifications=certifications,
    assumptions=[AS["a10"], AS["a11"]],
)

# ----------------------------------------------------------------------------- stage 5 (costs)

# Landed-cost inputs from the LIVE code (api/costs/landed.py): CBP-precedent HTS, Drewry-derived sea freight,
# broker/3PL, platform fee, V-Trust QC — the cached example computes exactly what the live stages would.
LIVE = LiveCosts("tracker_card", {"id": PID, "name": brief["product_name"], "mode": "idea", "prompt": brief["prompt"], "example": "tracker_card"}, brief, spec)
_h = LIVE.hts  # the assumption register quotes the same (live) HTS line as stage 11
for _a in ASSUMPTIONS:
    if _a["id"] == "a6":
        _a.update(text=f"HTS {_h.code}: general duty {_h.general_rate.value:g}% ({_h.description[:120]})", label=_h.general_rate.label, source=_h.general_rate.source_or_assumption[:400])
    elif _a["id"] in ("a11", "a13") and "Section 301" in _a["text"]:
        _a.update(text=f"Section 301 China {_h.section_301_rate.value:g}% on HTS {_h.code}", label=_h.section_301_rate.label, source=_h.section_301_rate.source_or_assumption[:400])
SAMPLES = 450.0

cost_lines, bom_by_cat = [], {"electronic": 0.0, "mechanical": 0.0, "packaging": 0.0}
for b in bom:
    price = b["unit_cost_est"]["value"]
    ext = price * b["qty"]
    bom_by_cat[b["category"]] += ext
    cost_lines.append({
        "bom_item_id": b["id"], "part": b["part"], "qty_per_unit": b["qty"], "unit_price": b["unit_cost_est"], "lcsc_pn": b["lcsc_pn"],
        "stock": lv(stock_by_id[b["id"]], "units", "sourced", lcsc_src(b["lcsc_pn"], "stock")) if b["id"] in stock_by_id else None,
        "extended": lv(round(ext, 4), "USD", "estimate", (f"LCSC unit price (Sourced) × estimated quantity: {b['qty']} × {price}" if b["unit_cost_est"]["label"] == "sourced" else f"{b['qty']} × {price}")),
    })
BOM_500 = bom_by_cat["electronic"] + bom_by_cat["mechanical"]
PKG_500 = bom_by_cat["packaging"]

tooling = [
    {"name": "Top shell mold (1-cavity, thin-wall PC)", "process": "injection_molding", "cost": usd(3800, src=AS["a9"]["source"])},
    {"name": "Bottom shell mold (1-cavity, thin-wall PC)", "process": "injection_molding", "cost": usd(3800, src=AS["a9"]["source"])},
    {"name": "Ultrasonic weld fixture", "process": "assembly", "cost": usd(500, src="Aluminium nest + horn tuning, demo assumption")},
    {"name": "BLE RF test + programming jig", "process": "assembly", "cost": usd(1400, src="Pogo-pin jig + shield box, demo assumption")},
    {"name": "Overlay die-cut tool", "process": "other", "cost": usd(250, src="Steel-rule die, demo assumption")},
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
        "assembly_cost": usd(a, src=AS["a3"]["text"]),
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
    ("Certification", CERT, "estimate", "FCC 15C + CE RED + Bluetooth SIG + UN38.3"),
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
    volume_factor=lv(VF, "ratio", "estimate", AS["a2"]["text"]),
    tiers=tiers,
    tooling=tooling,
    tooling_total=usd(TOOLING, src="Sum of tooling lines"),
    certification_total=usd(CERT, src="Sum of certification estimates"),
    reference_quantity=REF_Q,
    total_cash_needed=usd(TOTAL_CASH, src="Sum of cash_breakdown"),
    cash_breakdown=[{"name": n, "amount": lv(v, "USD", l, s)} for n, v, l, s in cash_components],
    target_retail_price=usd(TARGET_USD, src=AS["a1"]["text"]),
    breakeven_units=lv(round(breakeven), "units", "estimate", "(tooling + certification + samples + QC) / (target price − variable landed cost)"),
    assumptions=[AS[i] for i in ("a1", "a2", "a3", "a5", "a6", "a9", "a12", "a13")],
)

# ----------------------------------------------------------------------------- stage 6

production = base(
    stage=6,
    steps=[
        {"part_id": "p1", "part_name": "Top shell", "process": "injection_molding", "reason": "Thin-wall textured PC part at 2k+ volume; mold pays back vs CNC above ~100 units", "region": "Shenzhen, Guangdong", "lead_time_days": lv(28, "days", "estimate", "T0 mold lead time (thin-wall)")},
        {"part_id": "p2", "part_name": "Bottom shell", "process": "injection_molding", "reason": "Same resin, same molder, same mold base as the top shell", "region": "Shenzhen, Guangdong", "lead_time_days": lv(28, "days", "estimate", "T0 mold lead time (thin-wall)")},
        {"part_id": "p3", "part_name": "PCBA", "process": "pcba", "reason": "SMT with WLCSP SoC on LCSC parts; turnkey PCBA with in-line RF test", "region": "Shenzhen, Guangdong", "lead_time_days": lv(14, "days", "estimate", "Turnkey PCBA incl. parts")},
        {"part_id": "p4", "part_name": "Cell integration + ultrasonic welding", "process": "assembly", "reason": "Cell attach, buzzer bond and weld in one cell of the assembly line with a 100% functional RF check", "region": "Shenzhen, Guangdong", "lead_time_days": lv(21, "days", "estimate", "Mass production run for 2,000 units")},
        {"part_id": "p5", "part_name": "Graphic overlay", "process": "other", "reason": "Die-cut printed PET from a label converter", "region": "Dongguan, Guangdong", "lead_time_days": lv(10, "days", "estimate", "Print + die-cut")},
    ],
    assembly_notes=["100% RF/BLE functional test and firmware flash on the jig", "Cells shipped by sea only (UN3090 packed with equipment, UN38.3 summary on file)", "Ultrasonic weld energy validated on golden sample before mass production"],
    total_lead_time_days=lv(59, "days", "estimate", "Critical path: molds (28) + T1 (10) + mass production (21)"),
)

# ----------------------------------------------------------------------------- stage 7 (fictional network)

def crit(score, weight, note, name):
    return {"criterion": name, "score": score, "weight": weight, "note": note}


matching = base(
    stage=7,
    factory_pack_id="fp_tracker_card_v1",
    queries=[
        {"process": "injection_molding", "material": "PC", "quantity": REF_Q, "certifications_required": ["ISO 9001"], "deadline": "2027-01-15"},
        {"process": "pcba", "material": "FR-4", "quantity": REF_Q, "certifications_required": [], "deadline": "2027-01-15"},
    ],
    shortlist=[
        {"rank": 1, "factory_id": FA, "factory_name": NAME[FA], "score": lv(84, "score/100", "fictional", "Scored on demo data"),
         "score_breakdown": [crit(1.0, 0.35, "Molding + PCBA + assembly", "process_fit"), crit(1.0, 0.15, f"MOQ {CAP[FA]['moq']} ≤ 2,000", "moq"), crit(1.0, 0.15, "ISO 9001 held", "certifications"), crit(0.3, 0.15, f"{CAP[FA]['current_load_pct']:.0f}% loaded", "load"), crit(0.9, 0.2, f"{CAP[FA]['lead_time_days']} days", "lead_time")],
         "reasons": ["Prototype-to-production shop, thin-wall molding + SMT in one site", "Lowest MOQ and shortest lead time", "Busy: high load"]},
        {"rank": 2, "factory_id": FB, "factory_name": NAME[FB], "score": lv(80, "score/100", "fictional", "Scored on demo data"),
         "score_breakdown": [crit(1.0, 0.35, "Molding + PCBA + assembly", "process_fit"), crit(1.0, 0.15, f"MOQ {CAP[FB]['moq']} ≤ 2,000", "moq"), crit(1.0, 0.15, "ISO 9001 + BSCI", "certifications"), crit(0.7, 0.15, f"{CAP[FB]['current_load_pct']:.0f}% loaded", "load"), crit(0.5, 0.2, f"{CAP[FB]['lead_time_days']} days", "lead_time")],
         "reasons": ["Balanced quote behaviour", "In-house SMT line", "Longer lead time than rank 1"]},
        {"rank": 3, "factory_id": FC, "factory_name": NAME[FC], "score": lv(66, "score/100", "fictional", "Scored on demo data"),
         "score_breakdown": [crit(0.5, 0.35, "No PCBA in-house; thin-wall PC experience unknown", "process_fit"), crit(1.0, 0.15, f"MOQ {CAP[FC]['moq']} = order size", "moq"), crit(0.7, 0.15, "ISO 9001 only", "certifications"), crit(0.8, 0.15, f"{CAP[FC]['current_load_pct']:.0f}% loaded", "load"), crit(0.2, 0.2, f"{CAP[FC]['lead_time_days']} days", "lead_time")],
         "reasons": ["Lowest expected price", "PCBA must be subcontracted", "Long lead time"]},
    ],
)

# ----------------------------------------------------------------------------- stage 8


def q_tiers(mult: float) -> list[dict]:
    return [{"quantity": t["quantity"], "unit_price_usd": round(t["unit_cost"]["value"] * mult, 2)} for t in tiers]


rfqs = [{"id": f"rfq_tc_{SHORT[f]}", "project_id": PID, "factory_id": f, "factory_pack_id": "fp_tracker_card_v1", "quantities": TIERS, "status": "quoted", "created_at": T0.isoformat(), "label": "fictional"} for f in (FA, FB, FC)]
rfqs[0]["status"] = "accepted"
quotes = [
    {"id": f"qt_tc_{SHORT[FA]}_v1", "rfq_id": rfqs[0]["id"], "factory_id": FA, "version": 1, "tiers": q_tiers(1.15), "tooling_usd": 10400, "moq": CAP[FA]["moq"], "lead_time_days": CAP[FA]["lead_time_days"], "payment_terms": "50% deposit / 50% before shipment", "exceptions": ["Price valid 15 days"], "status": "superseded", "created_at": T0.isoformat(), "label": "fictional"},
    {"id": f"qt_tc_{SHORT[FB]}_v1", "rfq_id": rfqs[1]["id"], "factory_id": FB, "version": 1, "tiers": q_tiers(1.08), "tooling_usd": 9800, "moq": CAP[FB]["moq"], "lead_time_days": CAP[FB]["lead_time_days"], "payment_terms": "30% deposit / 70% before shipment", "exceptions": [], "status": "rejected", "created_at": T0.isoformat(), "label": "fictional"},
    {"id": f"qt_tc_{SHORT[FC]}_v1", "rfq_id": rfqs[2]["id"], "factory_id": FC, "version": 1, "tiers": q_tiers(0.97), "tooling_usd": 8600, "moq": CAP[FC]["moq"], "lead_time_days": CAP[FC]["lead_time_days"], "payment_terms": "30% deposit / 70% before shipment", "exceptions": ["PCBA subcontracted", "Thin-wall PC not yet run at this flow length"], "status": "rejected", "created_at": T0.isoformat(), "label": "fictional"},
    {"id": f"qt_tc_{SHORT[FA]}_v2", "rfq_id": rfqs[0]["id"], "factory_id": FA, "version": 2, "tiers": q_tiers(1.05), "tooling_usd": 9600, "moq": CAP[FA]["moq"], "lead_time_days": CAP[FA]["lead_time_days"], "payment_terms": "30% deposit / 70% before shipment", "exceptions": ["Price valid 15 days"], "status": "accepted", "created_at": T0.isoformat(), "label": "fictional"},
]
FINAL_FOB = next(t["unit_price_usd"] for t in quotes[3]["tiers"] if t["quantity"] == REF_Q)
FINAL_TOOLING = 9600.0


def turn(i, rfq, fac, spk, msg, cn=None, qid=None, changes=None, why=None):
    return {"id": f"t{i}", "rfq_id": rfq, "factory_id": fac, "turn": i, "speaker": spk, "message": msg, "message_cn": cn, "quote_id": qid, "proposed_changes": changes or {}, "rationale": why, "created_at": (T0 + timedelta(minutes=i)).isoformat(), "label": "fictional"}


a1 = quotes[0]["tiers"][1]["unit_price_usd"]
transcript = [
    turn(1, rfqs[0]["id"], FA, "platform_agent", "RFQ sent with Factory Pack fp_tracker_card_v1: 500 / 2,000 / 10,000 units, FCC + CE, thin-wall PC shells.", "已发送询价及工厂资料包 fp_tracker_card_v1：500 / 2,000 / 10,000 张，需FCC及CE认证，薄壁PC外壳。"),
    turn(2, rfqs[1]["id"], FB, "platform_agent", "RFQ sent with Factory Pack fp_tracker_card_v1.", "已发送询价及工厂资料包 fp_tracker_card_v1。"),
    turn(3, rfqs[2]["id"], FC, "platform_agent", "RFQ sent with Factory Pack fp_tracker_card_v1.", "已发送询价及工厂资料包 fp_tracker_card_v1。"),
    turn(4, rfqs[0]["id"], FA, "factory_agent", f"Quote v1: ${a1} at 2,000, tooling $10,400, {CAP[FA]['lead_time_days']} days, 50/50.", qid=quotes[0]["id"]),
    turn(5, rfqs[1]["id"], FB, "factory_agent", f"Quote: ${quotes[1]['tiers'][1]['unit_price_usd']} at 2,000, tooling $9,800, {CAP[FB]['lead_time_days']} days, 30/70.", qid=quotes[1]["id"]),
    turn(6, rfqs[2]["id"], FC, "factory_agent", f"Quote: ${quotes[2]['tiers'][1]['unit_price_usd']} at 2,000, tooling $8,600, {CAP[FC]['lead_time_days']} days. PCBA subcontracted; no thin-wall PC reference at 0.5 mm.", qid=quotes[2]["id"]),
    turn(7, rfqs[0]["id"], FA, "platform_agent", f"Counter: firm 2,000-unit PO and 30/70 terms if unit price moves to ${round(a1 * 0.91, 2)} and tooling to $9,600.", "还价：若单价降至相应水平、模具费9,600美元并采用30/70付款，我们确认2,000张订单。", qid=quotes[0]["id"], changes={"unit_price_2000": round(a1 * 0.91, 2), "tooling_usd": 9600, "payment_terms": "30/70"}, why="Best process fit and shortest lead time; use the other quotes as anchors and remove the 50% deposit."),
    turn(8, rfqs[0]["id"], FA, "factory_agent", f"Revised v2: ${FINAL_FOB} at 2,000, tooling $9,600, lead time {CAP[FA]['lead_time_days']} days, 30/70.", qid=quotes[3]["id"]),
    turn(9, rfqs[0]["id"], FA, "platform_agent", "Recommendation sent to founder: accept v2.", why="Only candidate with thin-wall molding, SMT and RF test on one site, shortest lead time; price about 8% above the cheapest quote."),
    turn(10, rfqs[0]["id"], FA, "user", "Approved."),
]

negotiation = base(
    stage=8,
    rfqs=rfqs,
    quotes=quotes,
    transcript=transcript,
    recommendation={"factory_id": FA, "quote_id": quotes[3]["id"], "rationale": f"Best process fit (thin-wall molding + SMT + RF test in one site) and the shortest lead time; v2 is 8.7% below its first quote. {NAME[FC]} is cheaper but subcontracts PCBA and has no thin-wall reference."},
    user_approved=True,
    final_terms={"factory_id": FA, "quote_id": quotes[3]["id"], "quantity": REF_Q, "unit_price": usd(FINAL_FOB, "fictional", "Negotiated quote v2 — demo data"), "tooling": usd(FINAL_TOOLING, "fictional", "Negotiated quote v2 — demo data"), "moq": CAP[FA]["moq"], "lead_time_days": lv(CAP[FA]["lead_time_days"], "days", "fictional", "Quote v2 — demo data"), "payment_terms": "30% deposit / 70% before shipment"},
)

# ----------------------------------------------------------------------------- stage 9

D = date(2026, 10, 5)


def ms(i, name, kind, start, days, deps=(), pay=None, notes=None):
    s = D + timedelta(days=start)
    return {"id": i, "name": name, "kind": kind, "start_date": s.isoformat(), "end_date": (s + timedelta(days=days)).isoformat(), "duration_days": lv(days, "days", "estimate", "Planner default from quote lead times"), "depends_on": list(deps), "payment": pay, "notes": notes}


cash = {n: v for n, v, _, _ in cash_components}
milestones = [
    ms("m1", "PO + tooling kickoff", "deposit", 0, 1, pay=usd(cash["Tooling"] * 0.5, src="50% tooling at kickoff")),
    ms("m2", "Tooling T0 + first shots", "tooling_t0", 1, 28, ["m1"]),
    ms("m3", "T1 corrections", "tooling_t1", 29, 10, ["m2"], pay=usd(cash["Tooling"] * 0.5, src="50% tooling at T1 approval")),
    ms("m4", "Golden sample approval (weld, RF, buzzer SPL)", "golden_sample", 39, 7, ["m3"], pay=usd(cash["Samples (T0, T1, golden)"], src="Sample rounds + express shipping")),
    ms("m5", "Certification testing (FCC 15C, CE RED, BT SIG, UN38.3)", "certification", 39, 42, ["m3"], pay=usd(cash["Certification"], src="Lab fees")),
    ms("m6", "Mass production (2,000 units)", "mass_production", 46, 21, ["m4"], pay=usd(cash["First production order (2,000 × FOB)"] * 0.3, src="30% deposit")),
    ms("m7", "Pre-shipment inspection", "pre_shipment_inspection", 79, 2, ["m6"], pay=lv(QC_COST, "USD", "estimate", "V-Trust rate (Sourced) × estimated man-days: 2 man-days × $268/man-day (V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26)")),
    ms("m8", "Balance + sea shipment", "shipment", 81, 30, ["m7", "m5"], pay=usd(cash["First production order (2,000 × FOB)"] * 0.7, src="70% balance before shipment")),
    ms("m9", "Delivered to US 3PL", "delivered", 111, 3, ["m8"]),
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
        {"id": "c1", "severity": "critical", "description": "Cell swelling, punctured pouch, or cell melted by weld heat", "spec_ref": "BOM e11 / DFM i4 / IEC 60086-4", "check_method": "Visual + X-ray on 5 units, weld-line temperature check", "aql": 0},
        {"id": "c2", "severity": "critical", "description": "Card does not advertise / cannot pair, or radio out of FCC channel/power limits", "spec_ref": "Electronics block b1 (nRF52810) / FCC Part 15C", "check_method": "BLE functional test on 100% at end of line + conducted power spot check", "aql": 0},
        {"id": "j1", "severity": "major", "description": "Total thickness outside 2.8 ± 0.15 mm or shells not welded closed", "spec_ref": "Tolerance: stack thickness 2.8 ± 0.15 mm", "check_method": "Caliper on 5 points + pull test", "aql": 2.5},
        {"id": "j2", "severity": "major", "description": "Buzzer below target loudness or silent", "spec_ref": "Part e10 / DFM i7", "check_method": "SPL meter at 10 cm vs golden sample", "aql": 2.5},
        {"id": "j3", "severity": "major", "description": "Button stuck or no wake-up", "spec_ref": "Electronics block b5", "check_method": "50 presses on the jig", "aql": 2.5},
        {"id": "n1", "severity": "minor", "description": "Flow lines, sink marks or shell warpage on visible face", "spec_ref": "Part p1 / DFM m3 (measured 0.5 mm wall)", "check_method": "Visual at 50 cm, D65 light + flatness on plate", "aql": 4.0},
        {"id": "n2", "severity": "minor", "description": "Overlay misregistration or bubbles", "spec_ref": "Part p5", "check_method": "Visual", "aql": 4.0},
    ],
    inspection_man_days=lv(2, "man-days", "estimate", "125 samples + RF and weld checks"),
    man_day_rate=lv(268, "USD", "sourced", "V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26"),
    inspection_cost=lv(QC_COST, "USD", "estimate", "V-Trust rate (Sourced) × estimated man-days: 2 man-days × $268/man-day (V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26)"),
    assumptions=[AS["a4"]],
)

# ----------------------------------------------------------------------------- stage 11

logistics = None  # live handler, computed below once every upstream stage exists

# ----------------------------------------------------------------------------- stage 12

financing = None  # live handler, computed below


# ----------------------------------------------------------------------------- stage 13

brand = base(
    stage=13,
    name_options=[
        {"name": "Plinq", "rationale": "Coined, short and ownable; sounds like the ping that finds your wallet. Trademark search needed before use."},
        {"name": "Slipfind", "rationale": "Slips in, finds it; descriptive and searchable. Trademark search needed before use."},
        {"name": "Cardwing", "rationale": "A card that flies back to you; playful. Trademark search needed before use."},
    ],
    chosen_name=None,
    packaging={"box_type": "Paperboard folding carton with tuck flap", "dimensions": dims(95, 62, 6, "Product + 8 mm clearance"), "materials": ["350 g paperboard", "Soy-ink print"], "printing": "1-colour black + matte varnish", "contents": ["Tracker card", "Quick-start card"], "unit_cost": usd(0.18, src="Packaging BOM line k1")},
    landing_copy={"headline": "Never lose your wallet again.", "subheadline": "A card-thin Bluetooth tracker that slides in next to your cards and rings your phone in one press.", "bullets": ["Fits any wallet card slot", "Ring your phone from the card, ring the card from your phone", "Sealed cell, nothing to charge"], "cta": "Reserve yours — $24.99"},
    shopify_listing={"channel": "shopify", "title": "Plinq — Bluetooth Tracker Card for Wallets", "description": "Wallet-card Bluetooth tracker with a sealed battery. Ring it from your phone, ring your phone from the card.", "bullets": ["Wallet-card size", "Bluetooth 5 ring", "No charging"], "price": lv(TARGET_USD, "USD", "estimate", AS["a1"]["text"]), "keywords": ["wallet tracker", "bluetooth tracker card", "item finder"]},
    amazon_listing={"channel": "amazon", "title": "Plinq Wallet Tracker Card, Bluetooth Item Finder, Ultra-Thin Card Fits Any Wallet", "description": "Ultra-thin Bluetooth tracker card for wallets, passport sleeves and card holders.", "bullets": ["WALLET-CARD SIZE — slides in with your cards", "BLUETOOTH RING — find your wallet from your phone", "PHONE FINDER — press the button to ring your phone", "SEALED BATTERY — no charging"], "price": usd(TARGET_USD, src=AS["a1"]["text"]), "keywords": ["wallet tracker", "tracker card", "item finder", "bluetooth"]},
)

# ----------------------------------------------------------------------------- Factory Pack

factory_pack = {
    "id": "fp_tracker_card_v1", "project_id": PID, "version": 1, "created_at": T0.isoformat(), "fallback": False,
    "product_name": brief["product_name"],
    "product_summary": brief["one_liner"] + " Target: 2,000 units first run, US + EU.",
    "product_summary_cn": "钱包卡片大小的蓝牙防丢追踪卡，可通过手机响铃寻卡，也可按键让手机响铃，采用密封薄型一次性锂电池，无需充电。首批2,000张，目标市场：美国和欧盟。",
    "target_markets": brief["target_markets"],
    "spec": {"overall_dimensions": spec["overall_dimensions"], "weight": spec["weight"], "parts": PARTS, "tolerances": spec["tolerances"]},
    "cad_files": spec["cad_files"],
    "bom": bom,
    "dfm_alerts": dfm_issues,
    "certifications": certifications,
    "target_quantities": TIERS,
    "cost_estimate": tiers,
    "questions": [
        {"id": "fq1", "en": "Can you mold 0.5 mm nominal-wall PC shells over an 85.6 mm flow length? Please share mold-flow results or similar references.", "cn": "贵司能否注塑名义壁厚0.5 mm、流长85.6 mm的PC外壳？请提供模流分析或类似案例。"},
        {"id": "fq2", "en": "Please confirm the thin lithium primary cell supplier and share its UN38.3 test summary and IEC 60086-4 report.", "cn": "请确认薄型锂一次电池供应商，并提供UN38.3测试摘要及IEC 60086-4报告。"},
        {"id": "fq3", "en": "For the ultrasonic weld: what energy-director design and cell keep-out do you recommend, and can you hold 2.8 ± 0.15 mm total thickness?", "cn": "超声波焊接方面：贵司建议的熔接线设计和电芯避让距离是多少？能否保证总厚度2.8 ± 0.15 mm？"},
        {"id": "fq4", "en": "Does your SMT line handle 0.4 mm-pitch WLCSP, and can you run BLE RF test and firmware flashing on a jig at end of line? Cost per unit?", "cn": "贵司SMT产线能否贴装0.4 mm间距的WLCSP？能否在线尾用治具完成蓝牙射频测试和固件烧录？单件成本是多少？"},
        {"id": "fq5", "en": "Quote tooling as single-cavity for both shells, stating steel grade and expected shot life, plus the 2-cavity option.", "cn": "请按两个外壳各单腔模具报价，注明钢材牌号和预期模次寿命，并提供双腔方案价格。"},
    ],
    "assumption_register": ASSUMPTIONS,
}

project = {"id": PID, "name": "Bluetooth Tracker Card for Wallets", "mode": "idea", "prompt": brief["prompt"], "pasted_bom": None, "example": "tracker_card", "status": "active", "created_at": T0.isoformat(), "stage_status": {}}

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
    dump(OUT / "project.json", A.Project, project)
    for n, data in STAGES.items():
        dump(OUT / f"{n:02d}_{A.STAGE_NAMES[n]}.json", A.ARTIFACT_MODELS[n], data)
    dump(OUT / "factory_pack.json", A.FactoryPack, factory_pack)
    print(f"total cash {TOTAL_CASH} · curve {cum:.2f} · landed est {est_landed} vs final {FINAL_LANDED} ({delta_pct:+.1f}%) · breakeven {breakeven:.0f} · unit@500/2k/10k {[unit_cost_at(k)[3] for k in range(3)]}")


if __name__ == "__main__":
    main()
