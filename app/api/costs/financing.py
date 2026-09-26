"""Stage 12 — Financing: cash-out curve per milestone that sums to the stage 5 total. Owner: W3.

    cash_curve(milestones, costs) -> list[CashPoint]
    check_cash(curve, costs)      -> list[str]   (empty = consistent)
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from api.stages.registry import StageContext, stage_handler
from contracts.artifacts import (
    Assumption,
    CashPoint,
    CostsArtifact,
    FinancingArtifact,
    FinancingOption,
    LandedCostComponent,
    Milestone,
    MilestoneKind,
)

from ._common import lv, usd

K = MilestoneKind
# cost line prefix → [(share, milestone kind, fallback kinds)]
ALLOCATION: list[tuple[str, list[tuple[float, str, tuple[str, ...]]]]] = [
    ("Tooling", [(0.5, "tooling_start", ()), (0.5, "tooling_t1", ("tooling_t0", "golden_sample"))]),
    ("Certification", [(1.0, "certification", ("golden_sample", "tooling_t1"))]),
    ("Samples", [(1.0, "golden_sample", ("tooling_t1", "tooling_t0"))]),
    ("First production order", [(0.3, "mass_production", ("deposit",)), (0.7, "pre_shipment_inspection", ("shipment", "mass_production"))]),
    ("Pre-shipment inspection", [(1.0, "pre_shipment_inspection", ("shipment", "mass_production"))]),
    ("Freight", [(1.0, "shipment", ("pre_shipment_inspection", "delivered"))]),
    ("Duties", [(1.0, "shipment", ("delivered", "pre_shipment_inspection"))]),
    ("Broker", [(1.0, "delivered", ("shipment", "pre_shipment_inspection"))]),
    ("Platform", [(1.0, "shipment", ("delivered", "pre_shipment_inspection"))]),
]
PAY_AT_START = {"deposit", "tooling_t0", "mass_production"}


def standard_milestones(base: date) -> list[Milestone]:
    """Fallback schedule when stage 9 is missing: T0 → T1 → golden sample → certification → mass production → shipment."""
    plan = [
        ("s1", "Tooling kick-off (T0)", K.tooling_t0, 0, 35, "Standard schedule: 5 weeks to T0 samples"),
        ("s2", "Tooling revision (T1)", K.tooling_t1, 35, 56, "Standard schedule: 3 weeks for T1"),
        ("s3", "Golden sample approved", K.golden_sample, 56, 63, "Standard schedule"),
        ("s4", "Certification", K.certification, 56, 84, "Standard schedule: labs in parallel with golden sample"),
        ("s5", "Production deposit", K.deposit, 84, 87, "Standard schedule: 30% deposit"),
        ("s6", "Mass production", K.mass_production, 87, 122, "Standard schedule: 5 weeks"),
        ("s7", "Pre-shipment inspection", K.pre_shipment_inspection, 122, 125, "Standard schedule"),
        ("s8", "Shipment", K.shipment, 125, 130, "Standard schedule"),
        ("s9", "Delivered to 3PL", K.delivered, 130, 162, "Standard schedule: sea LCL ~32 days"),
    ]
    out = []
    for i, (mid, name, kind, a, b, note) in enumerate(plan):
        out.append(
            Milestone(
                id=mid, name=name, kind=kind, start_date=base + timedelta(days=a), end_date=base + timedelta(days=b),
                duration_days=lv(b - a, "days", "estimate", note, nd=0), depends_on=[plan[i - 1][0]] if i else [], notes=note,
            )
        )
    return out


def _kind(m: Milestone) -> str:
    return str(getattr(m.kind, "value", m.kind))


def _pick(ms: list[Milestone], kind: str, fallbacks: tuple[str, ...]) -> Milestone:
    if kind == "tooling_start":  # PO + tooling kick-off: the earliest of the deposit / T0 milestones
        early = [m for m in ms if _kind(m) in ("deposit", "tooling_t0")]
        return min(early, key=lambda m: m.start_date) if early else ms[0]
    for k in (kind, *fallbacks):
        found = [m for m in ms if _kind(m) == k]
        if found:
            return found[0]
    return ms[-1] if kind in ("delivered", "shipment", "pre_shipment_inspection") else ms[0]


def _pay_date(m: Milestone) -> date:
    return m.start_date if _kind(m) in PAY_AT_START else m.end_date


def cash_curve(milestones: list[Milestone], costs: CostsArtifact, deposit_pct: float = 30.0) -> list[CashPoint]:
    """Allocate every stage 5 cash_breakdown line to a milestone; the curve total is exactly total_cash_needed.

    `deposit_pct` splits the first production order (deposit at mass production, balance before shipment); it
    comes from the approved/recommended quote's payment terms via stage 9 (30 when unknown)."""
    if not milestones:
        raise ValueError("no milestones")
    ms = sorted(milestones, key=lambda m: (m.end_date, m.start_date))
    total_cents = round(costs.total_cash_needed.value * 100)
    events: list[tuple[date, int, str, str, int]] = []  # date, order, milestone_id, description, cents
    order = 0
    for comp in costs.cash_breakdown:
        cents = round(comp.amount.value * 100)
        rule = next((r for p, r in ALLOCATION if comp.name.startswith(p)), [(1.0, "delivered", ())])
        if comp.name.startswith("First production order"):
            dep = min(max(deposit_pct, 0.0), 100.0) / 100
            rule = [(dep, rule[0][1], rule[0][2]), (1 - dep, rule[1][1], rule[1][2])]
        left = cents
        for j, (share, kind, fb) in enumerate(rule):
            m = _pick(ms, kind, fb)
            c = left if j == len(rule) - 1 else round(cents * share)
            left -= c
            label = f"{comp.name}" + (f" — {share:.0%}" if len(rule) > 1 else "") + f" @ {m.name}"
            if c:
                events.append((_pay_date(m), order, m.id, label, c))
                order += 1
    drift = total_cents - sum(e[4] for e in events)  # rounding of the breakdown vs its total
    if drift and events:
        d, o, mid, desc, c = events[-1]
        events[-1] = (d, o, mid, desc, c + drift)
    events.sort(key=lambda e: (e[0], e[1]))
    curve, cum = [], 0
    for d, _, mid, desc, c in events:
        cum += c
        curve.append(
            CashPoint(
                date=d, milestone_id=mid, description=desc,
                cash_out=usd(c / 100, "estimate", "Stage 5 cash breakdown, allocated to the milestone"),
                cumulative=usd(cum / 100, "estimate", "Running total"),
            )
        )
    return curve


def check_cash(curve: list[CashPoint], costs: CostsArtifact) -> list[str]:
    """Consistency problems of a cash curve vs stage 5 costs (empty list = consistent)."""
    issues: list[str] = []
    if not curve:
        return ["cash curve is empty"]
    total = costs.total_cash_needed.value
    s = round(sum(p.cash_out.value for p in curve), 2)
    if abs(s - total) > 0.01:
        issues.append(f"cash curve sums to {s:,.2f} but stage 5 total_cash_needed is {total:,.2f}")
    if abs(curve[-1].cumulative.value - s) > 0.01:
        issues.append("last cumulative value differs from the sum of cash-out points")
    run = 0.0
    for i, p in enumerate(curve):
        run += p.cash_out.value
        if p.cash_out.value < 0:
            issues.append(f"negative cash-out at point {i} ({p.description})")
        if abs(p.cumulative.value - run) > 0.01:
            issues.append(f"cumulative at point {i} is {p.cumulative.value:,.2f}, expected {run:,.2f}")
        if i and p.date < curve[i - 1].date:
            issues.append(f"dates not chronological at point {i}")
    dep = [p.date for p in curve if p.description.startswith("First production order")]
    tool = [p.date for p in curve if p.description.startswith("Tooling")]
    if dep and tool and min(dep) < min(tool):
        issues.append("production deposit is scheduled before the first tooling payment")
    return issues


def options(costs: CostsArtifact) -> list[FinancingOption]:
    total = costs.total_cash_needed.value
    price = costs.target_retail_price.value
    ref = costs.reference_quantity
    first_order = next((c.amount.value for c in costs.cash_breakdown if c.name.startswith("First production order")), 0.0)
    pre_units = math.ceil(total / (price * 0.965)) if price else 0
    goal = math.ceil(total / 0.92 / 100) * 100
    est = "estimate"
    return [
        FinancingOption(
            kind="preorders", name="Preorders / waitlist deposits",
            description=f"Presell about {pre_units:,} units at the target price ${price:,.2f} (net of ~3.5% card fees) to cover the ${total:,.0f} total cash need; refunds if the golden sample slips.",
            cost=lv(3.5, "pct", est, "Assumed card-processing fee ~3.5% of preorder value; check your payment provider"),
            pros=["Validates demand before tooling", "No dilution, no interest", "Preorder cash lands before the production deposit"],
            cons=["Delivery promise creates refund and legal exposure", "Slipping dates hurt trust", f"Needs an audience: {pre_units:,} buyers ≈ {pre_units / ref:.0%} of the {ref:,}-unit first order"],
        ),
        FinancingOption(
            kind="crowdfunding", name="Crowdfunding campaign",
            description=f"Reward-based campaign with a goal around ${goal:,} so that ~8% platform + processing fees still leave ${total:,.0f}.",
            cost=lv(8.0, "pct", est, "Assumed 5% platform fee + ~3% payment processing; verify on the chosen platform"),
            pros=["Marketing and financing in one", "Market proof for later investors", "Backers fund tooling early"],
            cons=["All-or-nothing risk", "Public roadmap; copycats", "Fulfilment obligations start before mass production is proven"],
        ),
        FinancingOption(
            kind="inventory_financing", name="Inventory / purchase-order financing",
            description=f"Lender advances the ~${first_order:,.0f} first production order against confirmed POs or preorders; repaid from sales.",
            cost=lv(15.0, "pct", est, "Assumed 12-20% annualised cost; quotes vary widely"),
            pros=["Preserves equity", "Scales with the order size"],
            cons=["Needs revenue history or confirmed POs", "Does not cover tooling or certification", "Personal guarantees are common for first-time founders"],
        ),
        FinancingOption(
            kind="revenue_based", name="Revenue-based financing",
            description="Advance repaid as a fixed share of monthly revenue until a cap; better for the second production run than the first.",
            cost=lv(9.0, "pct", est, "Assumed flat fee 6-12% of the advance"),
            pros=["No dilution", "Repayment tracks sales"],
            cons=["Needs existing revenue", "Repayment share squeezes reorder cash"],
        ),
        FinancingOption(
            kind="equity", name="Angel / pre-seed round",
            description=f"Raise about ${math.ceil(total * 1.3 / 1000) * 1000:,} (total cash + 30% buffer for slips and re-tooling).",
            cost=None,
            pros=["Buffer for re-tooling and delays", "Advice and factory introductions"],
            cons=["Dilution", "Slow to close for pre-revenue hardware", "Investors expect a distribution plan"],
        ),
        FinancingOption(
            kind="other", name="Negotiate factory terms",
            description="Ask for tooling amortised into the unit price (mold cost spread over the first orders) and 30/70 payment terms instead of 50/50; each step lowers the cash needed up front.",
            cost=lv(0.0, "pct", est, "Trade-off: a higher unit price in exchange for less upfront cash"),
            pros=["No third party", "Reduces the peak cash need"],
            cons=["Higher unit price", "Factory lock-in until the mold is paid", "Negotiation leverage depends on volume"],
        ),
    ]


def production_deposit_pct(tooling) -> float:
    """Deposit % of the first production order as scheduled by stage 9 (quote payment terms), else 30."""
    for item in getattr(tooling, "payment_schedule", None) or []:
        ms = next((m for m in tooling.milestones if m.id == item.milestone_id), None)
        if ms is not None and _kind(ms) == "mass_production" and item.pct_of_order:
            return float(item.pct_of_order)
    return 30.0


def negotiated_budget(ctx: StageContext, costs: CostsArtifact) -> tuple[CostsArtifact, str | None]:
    """Stage 5's cash breakdown with the approved stage-8 quote applied (unit price, tooling; freight, duties, platform
    fee and QC recomputed on the negotiated FOB). Returns (budget, why) — why is None when no quote is approved."""
    from . import engine, landed

    neg = ctx.artifact(8)
    ft = getattr(neg, "final_terms", None) if neg is not None else None
    if ft is None:
        return costs, None
    fob, qty, tool = float(ft.unit_price.value), int(ft.quantity), float(ft.tooling.value)
    hts = landed.hts_for(ctx)
    fo = engine.freight_opts(ctx)
    comps, _ = landed.landed_cost(fob, qty, landed.choose_mode(qty, **fo), hts, False, include_tooling=False, **fo)
    g = landed.cash_components(comps, qty)
    demo = f"approved quote {ft.quote_id} — demo data"
    new: list[LandedCostComponent] = []
    for c in costs.cash_breakdown:
        n = c.name
        if n.startswith("Tooling"):
            v, lab, note = tool, "fictional", f"Tooling of the {demo}"
        elif n.startswith("First production order"):
            v, lab, note = fob * qty, "fictional", f"{qty:,} × ${fob:.2f} ({demo})"
            n = f"First production order ({qty:,} × negotiated FOB)"
        elif n.startswith("Freight"):
            v, lab, note = g["freight"], "estimate", "Recomputed on the negotiated FOB (insurance) and the same freight basis as stage 11"
        elif n.startswith("Duties"):
            v, lab, note = g["duties"], "estimate", f"Recomputed on the negotiated FOB: HTS {hts.code} + Section 301"
        elif n.startswith("Platform"):
            v, lab, note = g["platform"], "estimate", "7% of the negotiated FOB"
        else:
            new.append(c)
            continue
        new.append(LandedCostComponent(name=n, amount=usd(round(v, 2), lab, note)))
    total = round(sum(c.amount.value for c in new), 2)
    budget = costs.model_copy(update={"cash_breakdown": new, "total_cash_needed": usd(total, "estimate", "Stage 5 budget with the approved quote applied")})
    u5 = next((t.unit_cost.value for t in costs.tiers if t.quantity == qty), None)
    why = (f"the negotiated quote {ft.quote_id} replaced the estimate: FOB ${fob:.2f}"
           + (f" vs ${u5:.2f}" if u5 is not None else "") + f" × {qty:,}, tooling ${tool:,.0f} vs ${costs.tooling_total.value:,.0f}, "
           f"payment terms {ft.payment_terms}")
    return budget, why


@stage_handler(12)
def run_financing(ctx: StageContext) -> FinancingArtifact:
    from . import engine

    costs = ctx.artifact(5) or engine.build_costs(ctx)
    tooling = ctx.artifact(9)
    ms = list(tooling.milestones) if tooling is not None and tooling.milestones else []
    base = ctx.project.created_at.date()
    source = "stage 9 milestones" if ms else "standard T0/T1/golden/mass-production schedule (no stage 9)"
    if not ms:
        ms = standard_milestones(base)
    deposit = production_deposit_pct(tooling)
    budget, why = negotiated_budget(ctx, costs)  # approved stage-8 quote replaces the estimate when present
    curve = cash_curve(ms, budget, deposit)
    problems = check_cash(curve, budget)
    if problems:
        raise ValueError("; ".join(problems))
    total = costs.total_cash_needed.value
    s = round(sum(p.cash_out.value for p in curve), 2)
    diff = round(s - total, 2)
    reconciliation = None if abs(diff) <= 0.01 else (
        f"Differs from stage 5 by ${diff:+,.0f} (${s:,.0f} vs ${total:,.0f}) because " + (why or "the cash breakdown changed"))
    peak_note = f"Peak cash need ${curve[-1].cumulative.value:,.0f}; {sum(p.cash_out.value for p in curve if p.date <= curve[0].date + timedelta(days=60)):,.0f} of it falls in the first 60 days."
    return FinancingArtifact(
        project_id=ctx.project.id,
        generated_by="code",
        assumptions=[
            Assumption(id="a1", text=f"Dates from {source}; amounts from the stage 5 cash breakdown{' with the approved stage 8 quote applied (unit price, tooling; duties, platform fee, insurance recomputed)' if why else ''} (tooling 50/50 at T0/T1, samples at golden sample, {deposit:g}% deposit + {100 - deposit:g}% before shipment (payment terms of stage 9), logistics at shipment/delivery)", label="estimate", source=None, stage=12),
            Assumption(id="a2", text=peak_note, label="estimate", source=None, stage=12),
            Assumption(id="a3", text="Financing costs are typical ranges, not quotes: verify with each provider", label="estimate", source=None, stage=12),
        ],
        cash_curve=curve,
        total_cash=usd(s, "estimate", "Sum of the cash curve" + (" (approved quote applied)" if why else " = stage 5 total_cash_needed")),
        matches_stage5_total=abs(diff) <= 0.01,
        options=options(budget),
        stage5_total=usd(total, "estimate", "Stage 5 total cash needed (budget reference)"),
        reconciliation_note=reconciliation,
    )
