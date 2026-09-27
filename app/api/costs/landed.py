"""Landed cost per unit (PRD §11) and stage 11 (Logistics). Owner: W3.

    landed_cost(fob_unit, qty, mode, hts, section_122=False, **opts) -> (components, total)

Python computes every number. Sea FCL freight = Drewry WCI lane rate (Sourced, data/freight_wci.json) ÷ units per 40ft (Estimate); LCL/air/express and
insurance stay Fictional demo rates. Duty rates come from the committed USITC HTS cache (Sourced) for the code of the closest
CBP CROSS precedent (data/cross/); Section 301 is Sourced only when a cached ruling cites the 9903.88.xx heading for that code.
"""

from __future__ import annotations

import json
import logging
import math
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from api.stages.registry import StageContext, stage_handler
from contracts.artifacts import (
    Assumption,
    FreightOption,
    HTSLine,
    LabeledValue,
    LandedCostComponent,
    LogisticsArtifact,
)

from . import freight as wci_freight
from . import hts as hts_cache
from . import precedent as cross
from ._common import VTRUST_SOURCE, label_of, lv, usd, weakest

log = logging.getLogger("costs.landed")

HTS_FILE = Path(__file__).resolve().parent / "data" / "hts.json"
Mode = str
MODES = ("sea_lcl", "sea_fcl", "air", "express")

# Fictional demo rates (freight is simulated in this product, PRD §16). USD per chargeable kg, transit days door-to-3PL.
FREIGHT = {
    "sea_lcl": (1.00, 32),
    "sea_fcl": (0.60, 35),
    "air": (4.00, 8),
    "express": (8.00, 5),
}
AIR_USD_PER_KG = 6.00  # Estimate: typical China→US air cargo range $4-8/kg
AIR_KG_PER_M3 = 167.0  # IATA volumetric weight
AIR_MIN_SHIPMENT = 150.0
EXPRESS_FACTOR = 1.8
INSURANCE_PCT = 0.3
PACKED_WEIGHT_FACTOR = 1.25  # packaged weight = product weight × 1.25
SECTION_122_PCT = 10.0
PLATFORM_FEE_PCT = 7.0  # benchmark 5-10 % (Dragon Sourcing)
QC_MAN_DAY_USD = 268.0  # V-Trust
BROKER_PER_SHIPMENT = 350.0
PORT_PER_UNIT = 0.05
TPL_PER_UNIT = 0.60

DRAGON = "https://www.dragonsourcing.com/top-10-cost-insights-for-hiring-a-china-sourcing-agent/"
VTRUST = "https://www.v-trust.com/en/our-network"


# --------------------------------------------------------------------------- HTS


class _HTSGuess(BaseModel):
    code: str
    description: str
    general_rate_pct: float
    rationale: str


def _hts_data() -> dict:
    return json.loads(HTS_FILE.read_text())


def hts_key_for(example: str | None, text: str) -> str | None:
    data = _hts_data()
    if example in data["lines"]:
        return example
    low = text.lower()
    for key, words in data["keywords"].items():
        if any(w in low for w in words):
            return key
    return None


def hts_line(key: str) -> HTSLine:
    d = _hts_data()["lines"][key]
    return HTSLine(
        code=d["code"],
        description=d["description"],
        general_rate=lv(d["general_rate_pct"], "pct", d["general_label"], d["general_source"], nd=2),
        section_301_rate=lv(d["section_301_rate_pct"], "pct", d["section_301_label"], d["section_301_source"], nd=2),
        source_url=d["source_url"],
    )


def estimate_hts(product_text: str) -> HTSLine:
    """Other products: the LLM suggests a heading (Estimate) when configured, else a placeholder to be confirmed."""
    from api import llm

    tbc = "to be confirmed by a customs broker"
    if llm.is_configured("fast"):
        try:
            g = llm.complete_json(
                "fast",
                f"Suggest the most likely 8-10 digit US HTS code for this product imported from China. Product: {product_text}",
                _HTSGuess,
            )
            return HTSLine(
                code=g.code,
                description=g.description,
                general_rate=lv(g.general_rate_pct, "pct", "estimate", f"LLM-suggested rate for heading {g.code}: {g.rationale[:160]} — {tbc}"),
                section_301_rate=lv(25.0, "pct", "estimate", f"Assumed 25% (Section 301 Lists 1-3) — {tbc}"),
                source_url="https://hts.usitc.gov/",
            )
        except Exception as e:  # noqa: BLE001
            log.info("HTS LLM suggestion failed, using placeholder: %s", e)
    return HTSLine(
        code="TBD",
        description="Heading not identified — placeholder rates",
        general_rate=lv(3.0, "pct", "estimate", f"Placeholder general duty 3%: heading unknown, {tbc}"),
        section_301_rate=lv(25.0, "pct", "estimate", f"Assumed 25% (Section 301 Lists 1-3) — {tbc}"),
        source_url="https://hts.usitc.gov/",
    )


TBC = "to be confirmed by a customs broker"


def hts_from_precedent(p: cross.Precedent) -> HTSLine | None:
    """HTS line for the code cited by a CBP ruling: MFN from the cached USITC schedule, Section 301 from the cited 9903.88.xx."""
    d = hts_cache.duty_for(p.hts, p.s301_heading)
    if d is None or d["mfn_pct"] is None:
        return None
    where = f"USITC HTS {d['code']} general rate {d['mfn_text']}, {d['source_url']}, fetched {d['fetched_on']}"
    if d["compound"]:
        general = lv(d["mfn_pct"], "pct", "estimate", f"{where}. Compound/specific duty: only the ad valorem part ({d['mfn_pct']:g}%) is modelled — {TBC}", nd=2)
    else:
        general = lv(d["mfn_pct"], "pct", "sourced", where, nd=2)
    if d["s301_rate"] is not None:
        s301 = lv(
            d["s301_rate"], "pct", "sourced",
            f"Section 301 China, heading {d['s301_heading']} (+{d['s301_rate']:g}%): USITC HTS, {hts_cache.s301_for(d['s301_heading'])['source_url']}, fetched {d['fetched_on']}; "
            f"heading cited with HTS {p.hts} in CBP ruling {p.s301_ruling} ({p.s301_ruling_date}). Coverage on the entry date {TBC}", nd=2,
        )
    else:
        s301 = lv(25.0, "pct", "estimate", f"Assumed 25% (Section 301 Lists 1-3): no cached CBP ruling cites a 9903.88.xx heading for HTS {p.hts} — {TBC}", nd=2)
    desc = f"{d['description']} — precedent {p.label}: {p.subject}"
    return HTSLine(code=d["code"], description=desc[:300], general_rate=general, section_301_rate=s301, source_url=d["source_url"])


def precedent_text(p: cross.Precedent) -> str:
    return (f"Assumed HTS {p.hts} — precedent: CBP ruling {p.ruling} ({p.ruling_date}), {p.url}. "
            "Not a binding classification; confirm with a customs broker.")


def resolve_hts(ctx: StageContext | None, example: str | None = None, text: str = "") -> tuple[HTSLine, cross.Precedent | None]:
    """(HTS line, CBP precedent it comes from). Order: closest cached CROSS precedent → hand-set example line → stage 5's
    estimated heading → LLM/placeholder estimate."""
    if ctx is not None:
        example = example or ctx.project.example
        brief = ctx.artifact(1)
        text = text or " ".join(filter(None, [ctx.project.prompt, getattr(brief, "category", ""), getattr(brief, "product_name", "")]))
    prec = cross.find_precedent(example, text)
    if prec is not None and (line := hts_from_precedent(prec)) is not None:
        return line, prec
    key = hts_key_for(example, text)
    if key:
        return hts_line(key), None
    if ctx is not None and ctx.stage != 5 and (prior := _hts_from_stage5(ctx.artifact(5))) is not None:
        return prior, None  # same (estimated) heading as the investment stage: stage 11 must reconcile with stage 5
    return _estimate_cached(text).model_copy(deep=True), None


def hts_for(ctx: StageContext | None, example: str | None = None, text: str = "") -> HTSLine:
    return resolve_hts(ctx, example, text)[0]


_STAGE5_HTS = re.compile(r"HTS (\S+) \(general ([\d.]+)%, Section 301 ([\d.]+)%\)")


def _hts_from_stage5(costs) -> HTSLine | None:
    """The estimated HTS line stage 5 used (recorded in its assumptions), so stage 11 does not re-guess another heading."""
    for a in getattr(costs, "assumptions", None) or []:
        m = _STAGE5_HTS.search(a.text)
        if m and m.group(1) != "TBD":
            tbc = "to be confirmed by a customs broker"
            return HTSLine(
                code=m.group(1), description="Heading estimated at stage 5 (investment)",
                general_rate=lv(float(m.group(2)), "pct", "estimate", f"Same heading and rate as stage 5 (LLM-suggested) — {tbc}"),
                section_301_rate=lv(float(m.group(3)), "pct", "estimate", f"Assumed Section 301 rate of stage 5 — {tbc}"),
                source_url="https://hts.usitc.gov/",
            )
    return None


@lru_cache(maxsize=256)
def _estimate_cached(text: str) -> HTSLine:
    return estimate_hts(text)


# --------------------------------------------------------------------------- landed cost


def _c(name: str, v: LabeledValue) -> LandedCostComponent:
    return LandedCostComponent(name=name, amount=v)


def freight_detail(mode: str, weight_kg: float, volume_m3: float | None = None, lane: str | None = None, qty: int | None = None) -> tuple[float, str, str]:
    """(USD per unit, label, note). Sea modes with a known packed volume are derived from the Drewry lane rate (Estimate);
    air / express and sea without volume use the Fictional demo rates."""
    src = f"derived from Drewry WCI {wci_freight.as_of_text(wci_freight.wci()['as_of'])}"
    if mode == "sea_fcl" and volume_m3 and qty and (r := wci_freight.fcl_per_unit(lane, volume_m3, qty)):
        per, kind, n = r
        rate = wci_freight.lane_rate(lane)[0] * (1 if kind == "40ft" else wci_freight.FEU20_RATE_FACTOR)
        return per, "estimate", (f"{src}: {n} × {kind} container at ${rate:,.0f} (lane rate {wci_freight.citation(lane).split(': ', 1)[1]}"
                                 f"{'; 20ft = 0.55 × 40ft, 33 m³, Estimate' if kind == '20ft' else ''}) ÷ {qty:,} units; {volume_m3:.4f} m³ packed unit (Estimate)")
    if mode == "sea_lcl" and volume_m3 and qty and (r := wci_freight.lcl_per_unit(lane, volume_m3, qty)):
        per, chg, per_m3 = r
        return per, "estimate", (f"{src}: ${per_m3:,.0f}/m³ (lane rate ÷ {wci_freight.FEU_USABLE_M3:g} m³ × LCL premium {wci_freight.LCL_PREMIUM:g}, Estimate) "
                                 f"× {chg:,.1f} m³ chargeable (min {wci_freight.LCL_MIN_M3:g} m³) ÷ {qty:,} units")
    if mode in ("air", "express") and volume_m3 and qty:
        gross, vol_kg = weight_kg * PACKED_WEIGHT_FACTOR, volume_m3 * AIR_KG_PER_M3
        chargeable = max(gross, vol_kg)
        air = max(chargeable * qty * AIR_USD_PER_KG, AIR_MIN_SHIPMENT) / qty
        per = air * (EXPRESS_FACTOR if mode == "express" else 1.0)
        return per, "estimate", (
            f"chargeable {chargeable:.3f} kg/unit = max(gross {gross:.3f} kg, {volume_m3:.4f} m³ × {AIR_KG_PER_M3:g}) × ${AIR_USD_PER_KG:.2f}/kg, "
            f"min ${AIR_MIN_SHIPMENT:.0f} per shipment" + (f", express = {EXPRESS_FACTOR:g}× air" if mode == "express" else "")
            + " — typical China→US air cargo rate range $4-8/kg, to be confirmed by a forwarder")
    rate = FREIGHT[mode][0]
    return rate * weight_kg * PACKED_WEIGHT_FACTOR, "fictional", f"demo freight rate ${rate:.2f}/kg × {weight_kg * PACKED_WEIGHT_FACTOR:.2f} kg packed — demo data"


def freight_per_unit(mode: str, weight_kg: float, volume_m3: float | None = None, lane: str | None = None, qty: int | None = None) -> float:
    return freight_detail(mode, weight_kg, volume_m3, lane, qty)[0]


def qc_man_days(qty: int) -> int:
    return max(1, math.ceil(qty / 1500))


def landed_cost(
    fob_unit: float,
    qty: int,
    mode: Mode = "sea_lcl",
    hts: HTSLine | None = None,
    section_122: bool = False,
    **opts,
) -> tuple[list[LandedCostComponent], LabeledValue]:
    """Per-unit landed cost components + total.

    opts: fob_label ('estimate'|'fictional'|'sourced'), fob_note, weight_kg (0.5), volume_m3 (packed unit volume, enables the
    Drewry-based sea FCL rate), lane (Drewry lane, default Shanghai-Los Angeles), tooling_total (0), qc_days (auto),
    include_tooling (True). Duties are levied on FOB (transaction value).
    """
    if qty <= 0 or fob_unit < 0:
        raise ValueError("qty must be > 0 and fob_unit >= 0")
    if mode not in FREIGHT:
        raise ValueError(f"unknown freight mode {mode}")
    fob_label = opts.get("fob_label", "estimate")
    fob_note = opts.get("fob_note", "Stage 5 ex-works unit cost")
    weight = float(opts.get("weight_kg", 0.5))
    tooling_total = float(opts.get("tooling_total", 0.0))
    qc_days = int(opts.get("qc_days", qc_man_days(qty)))
    comps: list[LandedCostComponent] = []

    comps.append(_c("FOB unit price", usd(fob_unit, fob_label, fob_note)))
    fr, fr_label, fr_note = freight_detail(mode, weight, opts.get("volume_m3"), opts.get("lane"), qty)
    comps.append(_c(f"Freight ({mode.replace('_', ' ').upper()})", usd(fr, fr_label, fr_note)))
    comps.append(_c(f"Insurance ({INSURANCE_PCT}% of FOB)", usd(fob_unit * INSURANCE_PCT / 100, "fictional", f"demo insurance rate {INSURANCE_PCT}% of FOB — demo data", nd=3)))

    base_label = "estimate"  # duty = real rate × an estimated or demo FOB
    if hts is not None:
        gr, s301 = hts.general_rate, hts.section_301_rate
        comps.append(_c(f"Duty HTS {hts.code} ({gr.value:g}%)", usd(fob_unit * gr.value / 100, weakest(label_of(gr), base_label), f"{gr.value:g}% × FOB. {gr.source_or_assumption}")))
        comps.append(_c(f"Section 301 ({s301.value:g}%)", usd(fob_unit * s301.value / 100, weakest(label_of(s301), base_label), f"{s301.value:g}% × FOB. {s301.source_or_assumption}")))
    comps.append(_c("IEEPA surcharges (0%)", usd(0.0, "sourced", "IEEPA duties not collected since 2026-02-24 (CBP CSMS 67834313, https://content.govdelivery.com/accounts/USDHSCBP/bulletins/40b11c9), 2026-02-22")))
    s122 = fob_unit * SECTION_122_PCT / 100 if section_122 else 0.0
    comps.append(
        _c(
            f"Section 122 surcharge ({SECTION_122_PCT:g}%{'' if section_122 else ', toggle off'})",
            usd(s122, "estimate", "10% temporary surcharge announced Feb 2026 for 150 days (CBP CSMS 67844987); current status to verify — user toggle"),
        )
    )
    broker = BROKER_PER_SHIPMENT / qty + PORT_PER_UNIT
    comps.append(_c("Broker + port fees", usd(broker, "estimate", f"Customs entry/ISF ${BROKER_PER_SHIPMENT:.0f} per shipment ÷ {qty} + ${PORT_PER_UNIT:.2f}/unit port fees")))
    comps.append(_c("3PL receiving + storage (1 month)", usd(TPL_PER_UNIT, "estimate", "US 3PL rate card average, assumption")))
    comps.append(_c(f"Platform / agent fee ({PLATFORM_FEE_PCT:g}% of FOB)", usd(fob_unit * PLATFORM_FEE_PCT / 100, "estimate", f"Sourcing agent / platform benchmark 5-10% of order (Dragon Sourcing, {DRAGON}), 7% assumed")))
    comps.append(_c("Pre-shipment inspection", usd(QC_MAN_DAY_USD * qc_days / qty, "estimate", f"V-Trust rate (Sourced) × estimated man-days: ${QC_MAN_DAY_USD:.0f}/man-day ({VTRUST_SOURCE}) × {qc_days} man-days ÷ {qty} units")))
    if opts.get("include_tooling", True):
        comps.append(_c("Tooling amortisation", usd(tooling_total / qty, "estimate", f"${tooling_total:,.0f} tooling ÷ {qty} units")))

    total = round(sum(c.amount.value for c in comps), 2)
    return comps, usd(total, "estimate", "Sum of landed cost components")


def cash_components(comps: list[LandedCostComponent], qty: int) -> dict[str, float]:
    """Group per-unit landed components into first-order cash lines (× qty), excluding FOB and tooling."""
    g = {"freight": 0.0, "duties": 0.0, "broker3pl": 0.0, "platform": 0.0, "qc": 0.0}
    for c in comps:
        n, v = c.name, c.amount.value * qty
        if n.startswith(("Freight", "Insurance")):
            g["freight"] += v
        elif n.startswith(("Duty", "Section", "IEEPA")):
            g["duties"] += v
        elif n.startswith(("Broker", "3PL")):
            g["broker3pl"] += v
        elif n.startswith("Platform"):
            g["platform"] += v
        elif n.startswith("Pre-shipment"):
            g["qc"] += v
    return g


# --------------------------------------------------------------------------- stage 11


def _quote_unit_price(quote, qty: int) -> float:
    tiers = sorted(quote.tiers, key=lambda t: t.quantity)
    price = tiers[0].unit_price_usd
    for t in tiers:
        if qty >= t.quantity:
            price = t.unit_price_usd
    return price


def fob_basis(ctx: StageContext, costs) -> tuple[float, int, float, str, str, str]:
    """(fob, qty, tooling_total, label, note, source) from stage 8 final terms / recommended quote, else stage 5."""
    neg = ctx.artifact(8)
    if neg is not None:
        ft = getattr(neg, "final_terms", None)
        if ft is not None:
            return ft.unit_price.value, int(ft.quantity), ft.tooling.value, "fictional", f"Approved final terms, quote {ft.quote_id} — demo data", "stage8_final_terms"
        rec = getattr(neg, "recommendation", None)
        quote = next((q for q in neg.quotes if rec and q.id == rec.quote_id), None)
        if quote is not None:
            qty = costs.reference_quantity
            return _quote_unit_price(quote, qty), qty, quote.tooling_usd, "fictional", f"Recommended quote {quote.id} v{quote.version} at {qty} units — demo data", "stage8_recommended_quote"
    tier = next((t for t in costs.tiers if t.quantity == costs.reference_quantity), costs.tiers[len(costs.tiers) // 2])
    return tier.unit_cost.value, tier.quantity, costs.tooling_total.value, "estimate", f"Stage 5 ex-works unit cost at {tier.quantity} units", "stage5"


def choose_mode(qty: int, override: str | None = None, volume_m3: float | None = None, lane: str | None = None, **_) -> str:
    """Cheaper of sea LCL and FCL from the Drewry-derived costs; without a packed volume the old 8,000-unit rule."""
    if override in FREIGHT:
        return override  # type: ignore[return-value]
    if volume_m3 and (m := wci_freight.cheaper_sea_mode(lane, volume_m3, qty)):
        return m
    return "sea_lcl" if qty < 8000 else "sea_fcl"


@stage_handler(11)
def run_logistics(ctx: StageContext) -> LogisticsArtifact:
    from . import engine  # local import: engine imports this module

    costs = ctx.artifact(5) or engine.build_costs(ctx)
    if costs.unit_basis == "per_installation":  # W21c: site install — no import, no freight leg
        from api.costs.site import site_logistics

        return site_logistics(ctx, costs)
    hts, prec = resolve_hts(ctx)
    s122 = bool(ctx.inputs.get("section_122", False))
    fob, qty, tooling, fob_label, fob_note, fob_src = fob_basis(ctx, costs)
    fo = engine.freight_opts(ctx)
    mode = choose_mode(qty, ctx.inputs.get("mode"), **fo)
    weight, lane = fo["weight_kg"], fo["lane"]

    comps, total = landed_cost(fob, qty, mode, hts, s122, fob_label=fob_label, fob_note=fob_note, tooling_total=tooling, **fo)
    options = []
    for m in MODES:
        per, lab, note = freight_detail(m, weight, fo["volume_m3"], lane, qty)
        if lab == "fictional":
            note = "demo data"
        if m in ("air", "express") and engine.has_battery(ctx):
            note += " — Li-ion air restrictions apply"
        options.append(FreightOption(
            mode=m,  # type: ignore[arg-type]
            transit_days=lv(FREIGHT[m][1], "days", "fictional", "demo data", nd=0),
            cost_per_unit=usd(per, lab, note, nd=3),
        ))

    # reconcile with stage 5 landed estimate at the same quantity
    t5 = next((t for t in costs.tiers if t.quantity == qty), None)
    ex5 = t5.unit_cost.value if t5 else engine.CostModel.from_ctx(ctx).unit_cost(qty).unit
    _, l5 = landed_cost(ex5, qty, choose_mode(qty, **fo), hts, False, tooling_total=costs.tooling_total.value, **fo)
    delta = (total.value - l5.value) / l5.value * 100 if l5.value else 0.0
    why = []
    if abs(fob - ex5) > 0.005:
        why.append(f"FOB ${fob:.2f} vs stage 5 ${ex5:.2f} ({fob_src})")
    if abs(tooling - costs.tooling_total.value) > 0.5:
        why.append(f"tooling ${tooling:,.0f} vs ${costs.tooling_total.value:,.0f}")
    if s122:
        why.append("Section 122 toggle on (+10% of FOB)")
    if mode != choose_mode(qty, **fo):
        why.append(f"freight mode {mode} chosen by the user vs {choose_mode(qty, **fo)} assumed in stage 5")
    ok = abs(delta) <= 10.0 or bool(why)  # every input that differs from stage 5 is listed, so the gap is explained
    note = f"Landed ${total.value:.2f} vs stage 5 estimate ${l5.value:.2f} at {qty:,} units ({delta:+.1f}%)" + (": " + "; ".join(why) if why else "") + "."
    if abs(delta) > 10.0:
        note += " Gap above 10% is fully explained by the drivers listed; review them before committing."

    assumptions = [
        Assumption(id="a1", text=f"HTS {hts.code}: {hts.general_rate.source_or_assumption}", label=hts.general_rate.label, source=hts.source_url, stage=11),
        Assumption(id="a2", text=hts.section_301_rate.source_or_assumption, label=hts.section_301_rate.label, source=hts.source_url, stage=11),
        Assumption(id="a3", text="IEEPA duties not collected since 24/02/2026; de minimis suspended; Section 122 is a user toggle (status to verify)", label="sourced", source="CBP CSMS 67834313 (https://content.govdelivery.com/accounts/USDHSCBP/bulletins/40b11c9); CBP CSMS 67844987; Federal Register 2026-06-24", stage=11),
        Assumption(id="a4", text=(f"Freight {mode.replace('_', ' ')}: ${FREIGHT[mode][0]:.2f}/kg, {FREIGHT[mode][1]} days — simulated rates"
                                  if mode not in ("sea_lcl", "sea_fcl") or fo["volume_m3"] is None else f"Freight {mode.replace('_', ' ')}: {FREIGHT[mode][1]} days transit (simulated); cost per unit derived from the Drewry lane rate, see a8-a10"),
                   label="fictional", source="demo data", stage=11),
        Assumption(id="a5", text="Platform/agent fee 7% of FOB (benchmark 5-10%)", label="estimate", source=DRAGON, stage=11),
        Assumption(id="a6", text=f"FOB basis: {fob_note}", label=fob_label, source=fob_src, stage=11),
    ]
    if prec is not None:
        assumptions.append(Assumption(id="a7", text=precedent_text(prec), label="sourced", source=prec.url, stage=11))
    else:
        assumptions.append(Assumption(id="a7", text=f"No CBP CROSS precedent in the cached set for this product: HTS {hts.code} and its rates are an estimate — {TBC}", label="estimate", source="https://rulings.cbp.gov/", stage=11))
    if (lr := wci_freight.lane_rate(lane)) is not None:
        assumptions.append(Assumption(id="a8", text=f"Sea container rate {wci_freight.citation(lane)} (Drewry-assessed spot benchmark, snapshot; the quote you get will differ)", label="sourced", source=lr[3], stage=11))
        if fo["volume_m3"]:
            upf = wci_freight.units_per_feu(fo["volume_m3"])
            assumptions.append(Assumption(
                id="a9", label="estimate", source="demo assumption", stage=11,
                text=(f"Sea freight derived from the Drewry lane rate, cheaper of LCL and FCL chosen automatically: packed unit {fo['volume_m3']:.4f} m³ "
                      f"(bounding box × {wci_freight.PACK_VOLUME_FACTOR:g} packaging, min {wci_freight.MIN_PACKED_M3 * 1000:g} L) = {upf:,} units per 40ft ({wci_freight.FEU_USABLE_M3:g} m³ usable); "
                      f"20ft container ≈ {wci_freight.FEU20_RATE_FACTOR} × the 40ft rate, {wci_freight.FEU20_M3:g} m³. Air = max(gross kg, m³ × {AIR_KG_PER_M3:g}) × ${AIR_USD_PER_KG:.2f}/kg, min ${AIR_MIN_SHIPMENT:.0f} per shipment; express = {EXPRESS_FACTOR:g}× air (Estimate: typical China→US air cargo range $4-8/kg, to be confirmed by a forwarder); air and express are never auto-chosen"),
            ))
            assumptions.append(Assumption(
                id="a10", label="estimate", source=lr[3], stage=11,
                text=(f"LCL consolidation premium vs FCL, typical 1.3–2.0×: {wci_freight.LCL_PREMIUM:g}× applied to lane rate ÷ {wci_freight.FEU_USABLE_M3:g} m³, "
                      f"minimum charge {wci_freight.LCL_MIN_M3:g} m³ per shipment (derived from Drewry WCI {wci_freight.as_of_text()})"),
            ))
    return LogisticsArtifact(
        project_id=ctx.project.id,
        generated_by="code",
        assumptions=assumptions,
        incoterm="FOB",
        destination=("New York, NY → US 3PL" if lane == wci_freight.EAST_COAST_LANE else "Los Angeles, CA → US 3PL"),
        quantity=qty,
        freight_options=options,
        chosen_mode=mode,  # type: ignore[arg-type]
        hts=hts,
        section_122_applied=s122,
        landed_cost_breakdown=comps,
        landed_cost_per_unit=total,
        reconciles_with_stage5=ok,
        reconciliation_note=note,
    )
