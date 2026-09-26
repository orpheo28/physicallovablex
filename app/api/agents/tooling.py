"""Stage 9 — Tooling + samples milestone plan. Owner: W4.

Pure code (generated_by = "code"): dates and money are formulas, not LLM text.
Lead-time source, in order: stage 8 final_terms → stage 8 recommended quote → stage 6 plan → defaults.
Payments: tooling 50% at kickoff / 50% at T1 approval, production order 30% deposit / 70% before shipment.
A Python date check runs on the result; any warning is stored as an assumption ("Date check: ...").
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from contracts.artifacts import (
    Label,
    LabeledValue,
    Milestone,
    MilestoneKind,
    PaymentScheduleItem,
    ToolingArtifact,
)

from api.agents import _planning as plan
from api.agents._common import AssumptionLog, estimate, lv
from api.stages.registry import StageContext, stage_handler

log = logging.getLogger("agents.tooling")

SAMPLES_COST_USD = 600.0  # sample rounds + express shipping (assumption, same as the cached example)
MAN_DAY_RATE_USD = 268.0
DEFAULT_CERT_DAYS = 28
DEFAULT_DEPOSIT_PCT = 30.0


@dataclass
class Terms:
    """What stage 8 (or stage 5) tells us about the order. Fictional when it comes from the simulated network."""

    origin: str  # human-readable source
    fictional: bool
    quantity: int
    unit_price: float | None
    tooling: float | None
    lead_days: int | None
    payment_terms: str | None


def _terms_from_negotiation(neg: Any, fallback_qty: int) -> Terms | None:
    if neg is None:
        return None
    ft = getattr(neg, "final_terms", None)
    if ft is not None:
        return Terms(f"final terms {ft.quote_id}", True, int(ft.quantity), float(ft.unit_price.value), float(ft.tooling.value),
                     int(ft.lead_time_days.value), ft.payment_terms)  # fmt: skip
    rec = getattr(neg, "recommendation", None)
    quote = next((q for q in getattr(neg, "quotes", []) if rec is not None and q.id == rec.quote_id), None)
    if quote is None:
        return None
    tiers = sorted(quote.tiers, key=lambda t: abs(t.quantity - fallback_qty))
    price = tiers[0].unit_price_usd if tiers else None
    qty = tiers[0].quantity if tiers else fallback_qty
    return Terms(f"recommended quote {quote.id}", True, int(qty), price, float(quote.tooling_usd), int(quote.lead_time_days), quote.payment_terms)


def _deposit_pct(payment_terms: str | None) -> float:
    """Deposit share of the production order from the quote's terms ("40% deposit / 60% …", "40/60", "T/T 40% advance")."""
    t = payment_terms or ""
    m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%\s*(?:t/t\s*)?(?:deposit|down|advance|upfront|prepay)", t, re.I) or re.search(
        r"(?:deposit|down|advance|upfront|prepay)\w*\s*(?:of\s*)?(\d{1,2}(?:\.\d+)?)\s*%", t, re.I)
    if m is None and (split := re.search(r"\b(\d{1,2})\s*%?\s*/\s*(\d{1,2})\s*%?", t)) and int(split[1]) + int(split[2]) == 100:
        m = split
    if m is None:
        m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%", t)  # first percentage = the upfront share by convention
    return float(m.group(1)) if m and 0 < float(m.group(1)) < 100 else DEFAULT_DEPOSIT_PCT


def check_dates(milestones: list[Milestone], schedule: list[PaymentScheduleItem]) -> list[str]:
    """Python consistency check of the plan. Returns human-readable warnings (empty = consistent)."""
    warnings: list[str] = []
    by_id = {m.id: m for m in milestones}
    prev_start: date | None = None
    for m in milestones:
        if m.end_date < m.start_date:
            warnings.append(f"{m.id} ends before it starts")
        if int(m.duration_days.value) != (m.end_date - m.start_date).days:
            warnings.append(f"{m.id} duration {m.duration_days.value:g} d ≠ dates ({(m.end_date - m.start_date).days} d)")
        for dep in m.depends_on:
            d = by_id.get(dep)
            if d is None:
                warnings.append(f"{m.id} depends on unknown milestone {dep}")
            elif m.start_date < d.end_date:
                warnings.append(f"{m.id} starts {m.start_date} before {dep} ends {d.end_date}")
        if prev_start and m.start_date < prev_start:
            warnings.append(f"{m.id} starts before the previous milestone starts (order not monotonic)")
        prev_start = m.start_date
    due = [p.due_date for p in schedule]
    if due != sorted(due):
        warnings.append("payment schedule due dates are not in chronological order")
    for p in schedule:
        if p.milestone_id not in by_id:
            warnings.append(f"payment for unknown milestone {p.milestone_id}")
    return warnings


def _start_date(ctx: StageContext) -> date:
    raw = (ctx.inputs or {}).get("start_date")
    if raw:
        try:
            return date.fromisoformat(str(raw))
        except ValueError:
            pass
    return plan.next_monday(date.today())


@stage_handler(9)
def run_tooling(ctx: StageContext) -> ToolingArtifact:
    brief, dfm, costs, prod, neg = ctx.artifact(1), ctx.artifact(4), ctx.artifact(5), ctx.artifact(6), ctx.artifact(8)
    log_ = AssumptionLog(9)

    ref_qty = int(getattr(costs, "reference_quantity", 0) or 0)
    if not ref_qty:
        vols = getattr(brief, "target_volumes", None) or []
        ref_qty = int(vols[len(vols) // 2]) if vols else plan.DEFAULT_LOT
    terms = _terms_from_negotiation(neg, ref_qty)
    qty = terms.quantity if terms else ref_qty

    # lead times
    pairs = [(getattr(s.process, "value", s.process), int(s.lead_time_days.value)) for s in getattr(prod, "steps", [])]
    if terms and terms.lead_days:
        t0 = terms.lead_days
        t0_src, t0_label = f"Lead time of {terms.origin} — demo data", Label.fictional
        log_.add(f"Quote lead time ({t0} d) is used as the tooling T0 duration; T1, golden sample and mass production use planning assumptions.")
    elif pairs:
        t0 = plan.tooling_lead_days(pairs)
        t0_src, t0_label = "Slowest tooled part in the stage 6 production plan", Label.estimate
    else:
        t0 = plan.LEAD_TIME_DAYS["injection_molding"]
        t0_src, t0_label = "Default injection-mold lead time (no stage 6 or 8 available)", Label.estimate
        log_.add("Stages 6 and 8 were not available: default lead times used.")
    t1 = plan.t1_days(pairs) if pairs else plan.T1_DAYS
    golden = plan.GOLDEN_SAMPLE_DAYS
    mass = plan.mass_days(qty)

    certs = [c for c in getattr(dfm, "certifications", []) if c.required]
    cert_days = int(max((c.lead_time_weeks.value for c in certs), default=DEFAULT_CERT_DAYS / 7) * 7)
    cert_fees = sum(c.cost_est.value for c in certs) or (float(costs.certification_total.value) if costs is not None else 0.0)

    letter, n = plan.sample_size(qty)
    psi_days = plan.inspection_man_days(n)

    S = _start_date(ctx)
    assumption_dur = "Planning assumption"
    dur = lambda d, src=assumption_dur, label=Label.estimate: lv(d, "days", label, src)  # noqa: E731

    def ms(mid: str, name: str, kind: MilestoneKind, start: date, days: int, deps: list[str], duration: LabeledValue,
           payment: LabeledValue | None = None, notes: str | None = None) -> Milestone:  # fmt: skip
        return Milestone(id=mid, name=name, kind=kind, start_date=start, end_date=start + timedelta(days=days),
                         duration_days=duration, depends_on=deps, payment=payment, notes=notes)  # fmt: skip

    # money
    tooling = terms.tooling if terms and terms.tooling is not None else (float(costs.tooling_total.value) if costs is not None else None)
    tool_label = Label.fictional if terms and terms.tooling is not None else Label.estimate
    tool_src = f"tooling of {terms.origin} — demo data" if tool_label == Label.fictional and terms else "Stage 5 tooling total"
    unit = terms.unit_price if terms and terms.unit_price else None
    order_label, order_src = Label.estimate, ""
    if terms and unit:
        order_label, order_src = Label.fictional, f"unit price of {terms.origin} × {qty:,} units — demo data"
    if unit is None and costs is not None:
        tier = next((t for t in costs.tiers if t.quantity == qty), None) or min(costs.tiers, key=lambda t: abs(t.quantity - qty))
        unit, order_label = float(tier.unit_cost.value), Label.estimate
        order_src = f"Stage 5 ex-works unit cost at {tier.quantity:,} units × {qty:,} units"
    order = round(unit * qty, 2) if unit else None
    dep_pct = _deposit_pct(terms.payment_terms if terms else None)
    if order is None:
        log_.add("No unit price or stage 5 cost available: production payments are not scheduled.")
    if tooling is None:
        log_.add("No tooling cost available: tooling payments are not scheduled.")

    def money(value: float, label: Label, src: str) -> LabeledValue:
        return lv(round(value, 2), "USD", label, src)

    m1 = ms("m1", "PO + tooling kickoff", MilestoneKind.deposit, S, 1, [], dur(1),
            money(tooling / 2, tool_label, f"50% of {tool_src}") if tooling else None)  # fmt: skip
    m2 = ms("m2", "Tooling T0 + first shots", MilestoneKind.tooling_t0, m1.end_date, t0, ["m1"], dur(t0, t0_src, t0_label))
    m3 = ms("m3", "T1 corrections", MilestoneKind.tooling_t1, m2.end_date, t1, ["m2"], dur(t1),
            money(tooling / 2, tool_label, f"50% of {tool_src} at T1 approval") if tooling else None)  # fmt: skip
    m4 = ms("m4", "Golden sample approval", MilestoneKind.golden_sample, m3.end_date, golden, ["m3"], dur(golden),
            estimate(SAMPLES_COST_USD, "USD", "Sample rounds + express shipping, assumption"))  # fmt: skip
    m5 = ms("m5", "Certification testing", MilestoneKind.certification, m3.end_date, cert_days, ["m3"], dur(cert_days, "Longest required lab lead time (stage 4 certifications)" if certs else assumption_dur),
            estimate(cert_fees, "USD", "Sum of required certification estimates (stage 4/5)") if cert_fees else None,
            "; ".join(c.standard for c in certs) or None)  # fmt: skip
    dep_amt = round(order * dep_pct / 100, 2) if order else None
    m6 = ms("m6", f"Mass production ({qty:,} units)", MilestoneKind.mass_production, m4.end_date, mass, ["m4"],
            dur(mass, f"{qty:,} units at {plan.UNITS_PER_DAY} units/day, assumption"),
            money(dep_amt, order_label, f"{dep_pct:g}% deposit of {order_src}") if dep_amt else None)  # fmt: skip
    m7_start = max(m6.end_date, m5.end_date)
    m7 = ms("m7", "Pre-shipment inspection", MilestoneKind.pre_shipment_inspection, m7_start, psi_days, ["m6", "m5"],
            dur(psi_days, f"{n} samples (ISO 2859-1 code {letter}) at {plan.PSI_UNITS_PER_MAN_DAY} units per man-day, assumption"),
            money(psi_days * MAN_DAY_RATE_USD, Label.estimate, f"V-Trust rate (Sourced) × estimated man-days: {psi_days} man-days × ${MAN_DAY_RATE_USD:g}/man-day (V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26)"))  # fmt: skip
    m8 = ms("m8", "Balance + sea shipment", MilestoneKind.shipment, m7.end_date, plan.TRANSIT_SEA_DAYS, ["m7"],
            dur(plan.TRANSIT_SEA_DAYS, "Sea freight transit assumption; refined at stage 11"),
            money(order - dep_amt, order_label, f"{100 - dep_pct:g}% balance before shipment of {order_src}") if order and dep_amt is not None else None)  # fmt: skip
    m9 = ms("m9", "Delivered to destination 3PL", MilestoneKind.delivered, m8.end_date, plan.DELIVERY_DAYS, ["m8"], dur(plan.DELIVERY_DAYS))
    milestones = [m1, m2, m3, m4, m5, m6, m7, m8, m9]

    def item(m: Milestone, desc: str, due: date, pct: float | None = None) -> PaymentScheduleItem | None:
        return PaymentScheduleItem(milestone_id=m.id, description=desc, pct_of_order=pct, amount=m.payment, due_date=due) if m.payment else None  # type: ignore[arg-type]

    schedule = [
        s for s in (
            item(m1, "50% tooling at kickoff", m1.start_date),
            item(m3, "50% tooling at T1 approval", m3.end_date),
            item(m4, "Sample rounds + express shipping", m4.start_date),
            item(m5, "Certification lab fees", m5.start_date),
            item(m6, f"{dep_pct:g}% production deposit", m6.start_date, dep_pct),
            item(m7, "Pre-shipment inspection", m7.start_date),
            item(m8, f"{100 - dep_pct:g}% balance before shipment", m8.start_date, 100 - dep_pct),
        ) if s
    ]  # fmt: skip
    schedule.sort(key=lambda p: p.due_date)

    warnings = check_dates(milestones, schedule)
    if prod is not None and prod.generated_by != "fixture" and not prod.fallback:  # cached examples use another overlap rule
        planned, actual = int(prod.total_lead_time_days.value), (m6.end_date - m2.start_date).days
        if planned != actual:
            warnings.append(f"lead time differs from the stage 6 plan by {actual - planned:+d} d (stage 6: {planned} d, this plan: {actual} d)" + (" — the negotiated quote governs" if terms else ""))
    for w in warnings:
        log_.add(f"Date check: {w}")
    log_.add(f"Kickoff date {S} (next Monday after today unless start_date is passed in inputs); durations are planning assumptions except the quote lead time.")
    log_.add("Sample rounds cost is an assumption; production payments follow the 30/70 term (deposit / before shipment) unless the quote states another deposit.")

    return ToolingArtifact(project_id=ctx.project.id, generated_by="code", assumptions=log_.items, milestones=milestones, payment_schedule=schedule)
