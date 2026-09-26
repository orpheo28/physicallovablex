"""Deterministic negotiation policy (W5). Private module: not auto-imported, used by the stage 7/8 handlers.

It is both the scripted path (no LLM key) and the guard-rail for the LLM path: LLM numbers are clamped
around what this policy computes, so a model can phrase and nudge, never invent prices.
All numbers produced here are Fictional — demo data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from contracts.artifacts import Factory, ProcessType, Quote, QuoteTier

TERMS_30_70 = "30% deposit / 70% before shipment"


@dataclass(frozen=True)
class Persona:
    key: str
    price_mult: float  # first quote vs stage-5 anchor
    tooling_mult: float
    terms: str
    concession: float  # max total unit-price concession vs its first quote
    lead_give: int  # days it can shave on request
    moq_flex: float  # share of MOQ it can drop on request
    fallback_terms: str  # what it offers when asked for 30/70 and refuses it


PERSONAS: list[tuple[str, Persona]] = [
    ("workshop", Persona("workshop", 0.93, 0.80, "50% deposit / 50% before shipment", 0.04, 2, 1.0, "50% deposit / 50% before shipment")),
    ("cheap", Persona("cheap/slow", 0.96, 0.88, TERMS_30_70, 0.03, 0, 0.0, TERMS_30_70)),
    ("fast", Persona("fast/expensive", 1.18, 1.12, "50% deposit / 50% before shipment", 0.015, 5, 0.5, "40% deposit / 60% before shipment")),
    ("premium", Persona("premium", 1.14, 1.10, "40% deposit / 60% before shipment", 0.02, 3, 0.25, "40% deposit / 60% before shipment")),
    ("specialist", Persona("specialist", 1.06, 0.95, TERMS_30_70, 0.035, 3, 0.25, TERMS_30_70)),
    ("balanced", Persona("balanced", 1.08, 1.0, TERMS_30_70, 0.055, 3, 0.5, TERMS_30_70)),
]


def persona_for(factory: Factory) -> Persona:
    a = factory.archetype.lower()
    for key, p in PERSONAS:
        if key in a:
            return p
    return PERSONAS[-1][1]


def deposit_pct(terms: str) -> int:
    m = re.search(r"(\d+)\s*%", terms)
    return int(m.group(1)) if m else 30


def price_at(tiers: list[QuoteTier], qty: int) -> float:
    """Unit price of the largest tier ≤ qty (else the smallest tier)."""
    ts = sorted(tiers, key=lambda t: t.quantity)
    best = ts[0]
    for t in ts:
        if t.quantity <= qty:
            best = t
    return best.unit_price_usd


def round_to(x: float, step: float) -> float:
    return round(round(x / step) * step, 2)


# --------------------------------------------------------------------------- first quote


@dataclass
class QuoteTerms:
    tiers: dict[int, float]
    tooling_usd: float
    moq: int
    lead_time_days: int
    payment_terms: str
    exceptions: list[str]


def missing_processes(factory: Factory, needed: list[ProcessType | str]) -> list[str]:
    have = set(factory.capacity.processes)
    return [str(getattr(p, "value", p)) for p in needed if getattr(p, "value", p) not in have]


def initial_quote(factory: Factory, anchors: dict[int, float], anchor_tooling: float, needed: list, ref_qty: int) -> QuoteTerms:
    p = persona_for(factory)
    missing = missing_processes(factory, needed)
    sub = 1 + 0.03 * len(missing)
    tiers = {q: round(v * p.price_mult * sub, 2) for q, v in sorted(anchors.items())}
    exceptions = [f"{m.replace('_', ' ')} subcontracted to a partner shop" for m in missing]
    moq = factory.capacity.moq
    if moq > ref_qty:
        exceptions.append(f"MOQ {moq:,} is above the {ref_qty:,}-unit reference order")
    lead = factory.capacity.lead_time_days + (5 if factory.capacity.current_load_pct > 75 else 0) + 3 * len(missing)
    return QuoteTerms(
        tiers=tiers,
        tooling_usd=round_to(anchor_tooling * p.tooling_mult, 50),
        moq=moq,
        lead_time_days=lead,
        payment_terms=p.terms,
        exceptions=exceptions,
    )


def clamp_llm_quote(base: QuoteTerms, prices: list[float], tooling: float, lead: int, terms: str, exceptions: list[str]) -> QuoteTerms:
    """Keep an LLM factory agent within ±12 % of the policy price, ±15 % tooling, ±7 days."""
    qs = sorted(base.tiers)
    out: dict[int, float] = {}
    prev = None
    for i, q in enumerate(qs):
        b = base.tiers[q]
        v = prices[i] if i < len(prices) and prices[i] and prices[i] > 0 else b
        v = min(max(v, b * 0.88), b * 1.12)
        if prev is not None:
            v = min(v, prev)  # never more expensive at higher volume
        out[q] = round(v, 2)
        prev = out[q]
    return QuoteTerms(
        tiers=out,
        tooling_usd=round_to(min(max(tooling or base.tooling_usd, base.tooling_usd * 0.85), base.tooling_usd * 1.15), 50),
        moq=base.moq,
        lead_time_days=int(min(max(lead or base.lead_time_days, base.lead_time_days - 7), base.lead_time_days + 7)),
        payment_terms=terms.strip() or base.payment_terms,
        exceptions=base.exceptions + [e for e in exceptions if e and e not in base.exceptions][:2],
    )


# --------------------------------------------------------------------------- scoring / recommendation


def effective_unit(q: Quote, ref_qty: int) -> float:
    return price_at(q.tiers, ref_qty) + q.tooling_usd / max(ref_qty, 1)


def risk_factor(factory: Factory, q: Quote) -> float:
    pp = factory.past_performance
    on_time = pp.on_time_rate_pct if (pp.orders_completed and pp.on_time_rate_pct is not None) else 60.0
    defects = pp.defect_rate_pct if pp.defect_rate_pct is not None else 2.0  # no data yet: assume a typical 2 %
    r = (100 - on_time) / 100 * 0.5 + defects / 100 * 2
    r += 0.03 * sum("subcontracted" in e for e in q.exceptions)
    r += 0.02 if deposit_pct(q.payment_terms) > 30 else 0
    r += 0.002 * max(0, q.lead_time_days - 25)
    return round(r, 4)


def value_score(factory: Factory, q: Quote, ref_qty: int) -> float:
    """Risk-adjusted effective unit cost (lower is better)."""
    return round(effective_unit(q, ref_qty) * (1 + risk_factor(factory, q)), 4)


def pick(latest: list[Quote], factories: dict[str, Factory], ref_qty: int) -> Quote:
    return sorted(latest, key=lambda q: (value_score(factories[q.factory_id], q, ref_qty), q.factory_id))[0]


# --------------------------------------------------------------------------- counters


@dataclass
class Counter:
    changes: dict
    rationale: str
    message: str


def counter_for(q: Quote, latest: list[Quote], factories: dict[str, Factory], ref_qty: int, round_no: int) -> Counter:
    """Platform agent ask: close the price gap to the cheapest competitor (−3 … −8 %, −2 % in round 2),
    tooling −10 %, MOQ down to the reference order, lead time −5 days if slow, 30/70 terms."""
    others = [o for o in latest if o.factory_id != q.factory_id]
    my_price = price_at(q.tiers, ref_qty)
    cheapest = min((price_at(o.tiers, ref_qty) for o in others), default=my_price)
    fastest = min((o.lead_time_days for o in others), default=q.lead_time_days)
    if round_no == 1:
        gap = (cheapest / my_price - 1) * 100
        pct = round(min(-3.0, max(-8.0, gap)), 1)
    else:
        pct = -2.0
    changes: dict = {"unit_price_pct": pct}
    parts = [f"unit price {pct:+.1f}% (to ${my_price * (1 + pct / 100):.2f} at {ref_qty:,})"]
    tooling = round_to(q.tooling_usd * (0.9 if round_no == 1 else 0.96), 50)
    if tooling < q.tooling_usd:
        changes["tooling_usd"] = tooling
        parts.append(f"tooling ${tooling:,.0f}")
    if q.moq > ref_qty:
        changes["moq"] = ref_qty
        parts.append(f"MOQ {ref_qty:,}")
    if q.lead_time_days > fastest + 5:
        changes["lead_time_days"] = q.lead_time_days - 5
        parts.append(f"lead time {q.lead_time_days - 5} days")
    if deposit_pct(q.payment_terms) != 30:
        changes["payment_terms"] = TERMS_30_70
        parts.append("30/70 payment terms")
    name = factories[q.factory_id].name
    rationale = (
        f"Cheapest competing quote is ${cheapest:.2f} at {ref_qty:,} units; {name} is at ${my_price:.2f}. "
        f"Fastest competitor ships in {fastest} days. Policy: price, tooling, MOQ ≤ first order, 30/70 terms."
    )
    verb = "Counter" if round_no == 1 else "Final ask"
    message = f"{verb}: firm {ref_qty:,}-unit PO if we get " + ", ".join(parts) + "."
    return Counter(changes=changes, rationale=rationale, message=message)


def respond(factory: Factory, first: Quote, current: Quote, ask: dict) -> QuoteTerms:
    """Factory agent reply to a counter: concede up to its personality limits, measured from its first quote."""
    p = persona_for(factory)
    pct = float(ask.get("unit_price_pct", 0))
    tiers = {}
    for t in current.tiers:
        floor = price_at(first.tiers, t.quantity) * (1 - p.concession)
        asked = t.unit_price_usd * (1 + pct / 100)
        tiers[t.quantity] = round(max(asked, floor), 2)
    tooling = current.tooling_usd
    if "tooling_usd" in ask:
        tooling = round_to(max(float(ask["tooling_usd"]), first.tooling_usd * (1 - p.concession * 1.5)), 50)
    moq = current.moq
    if "moq" in ask:
        moq = int(max(int(ask["moq"]), round_to(first.moq * (1 - p.moq_flex), 100)))
    lead = current.lead_time_days
    if "lead_time_days" in ask:
        lead = max(int(ask["lead_time_days"]), first.lead_time_days - p.lead_give)
    terms = current.payment_terms
    if "payment_terms" in ask:
        terms = TERMS_30_70 if deposit_pct(p.terms) == 30 else p.fallback_terms
    exceptions = list(current.exceptions)
    if "moq" in ask and moq <= int(ask["moq"]):
        exceptions = [e for e in exceptions if not e.startswith("MOQ ")]
    return QuoteTerms(tiers=tiers, tooling_usd=tooling, moq=moq, lead_time_days=lead, payment_terms=terms, exceptions=exceptions)


def describe(q: QuoteTerms | Quote, ref_qty: int, version: int | None = None) -> str:
    if isinstance(q, Quote):
        price, tooling, moq, lead, terms = price_at(q.tiers, ref_qty), q.tooling_usd, q.moq, q.lead_time_days, q.payment_terms
        version = version or q.version
    else:
        price = price_at([QuoteTier(quantity=k, unit_price_usd=v) for k, v in q.tiers.items()], ref_qty)
        tooling, moq, lead, terms = q.tooling_usd, q.moq, q.lead_time_days, q.payment_terms
    v = f"v{version}: " if version else ""
    return f"{v}${price:.2f} at {ref_qty:,}, tooling ${tooling:,.0f}, MOQ {moq:,}, {lead} days, {terms}"
