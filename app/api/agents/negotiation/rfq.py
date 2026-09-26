"""Stage 8 — RFQ + negotiation (W5).

Flow (all through the production MCP functions in factory_mcp.network):
  request_quote → top 3 of stage 7 · 3 factory agents submit_quote (route "fast", anchored on stage-5 tiers ±
  personality) · negotiation agent (route "main") counters price / tooling / MOQ / lead time / 30-70 terms,
  max 2 rounds, factories reply within personality limits · recommendation · optional CN lines (route "cn").
Without a key every LLM step falls back to the deterministic policy in _policy.py, so the stage stays live
(`fallback: false`, generated_by "code"). inputs {"approve": true, "quote_id"?} → accept_quote + final_terms.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from contracts.artifacts import (
    Assumption,
    Factory,
    FinalTerms,
    LabeledValue,
    NegotiationArtifact,
    NegotiationTurn,
    Quote,
    Recommendation,
    Speaker,
)
from pydantic import BaseModel, Field

from api import llm
from api.agents.negotiation import _inputs, _policy
from api.agents.negotiation.matching import match
from api.stages.registry import StageContext, stage_handler
from factory_mcp import network

log = logging.getLogger("negotiation")

N_FACTORIES = 3
MAX_ROUNDS = 2
DEMO = "demo data"


# --------------------------------------------------------------------------- LLM schemas


class FactoryQuoteDraft(BaseModel):
    message: str = Field(description="1-2 sentence reply from the factory sales rep, in English")
    unit_prices: list[float] = Field(description="USD unit price per quantity tier, same order as the RFQ tiers")
    tooling_usd: float
    lead_time_days: int
    payment_terms: str
    exceptions: list[str] = Field(default_factory=list)


class CounterDraft(BaseModel):
    factory_id: str
    message: str = Field(description="Counter-offer message sent to the factory, 1-2 sentences")
    rationale: str = Field(description="Why, citing competing quotes")
    unit_price_pct: float = Field(description="Requested unit-price change in %, between -8 and 0")


class NegotiationPlan(BaseModel):
    counters: list[CounterDraft]


class RecommendationDraft(BaseModel):
    factory_id: str
    rationale: str


class CnBatch(BaseModel):
    translations: list[str]


# --------------------------------------------------------------------------- transcript helper


class Transcript:
    def __init__(self) -> None:
        self.turns: list[NegotiationTurn] = []

    def add(self, rfq_id: str, factory_id: str, speaker: Speaker, message: str, **kw) -> NegotiationTurn:
        t = NegotiationTurn(
            id=f"t{len(self.turns) + 1}",
            rfq_id=rfq_id,
            factory_id=factory_id,
            turn=len(self.turns) + 1,
            speaker=speaker,
            message=message,
            **kw,
        )
        self.turns.append(t)
        return t



def _perf(pp, full: bool = False) -> str:
    """Past performance in words; 'no data yet' for a factory without completed orders on the network."""
    if pp.no_data or pp.on_time_rate_pct is None:
        return "no performance data yet"
    return f"{pp.on_time_rate_pct:.0f}% on-time, {pp.defect_rate_pct}% defects" if full else f"{pp.on_time_rate_pct:.0f}%"

def _fmt_q(quantities: list[int]) -> str:
    return " / ".join(f"{q:,}" for q in quantities)


# --------------------------------------------------------------------------- agents


def _factory_agent(factory: Factory, base: _policy.QuoteTerms, quantities: list[int], product: str, ref_qty: int) -> tuple[_policy.QuoteTerms, str, bool]:
    """Returns (terms, message, used_llm). LLM phrasing + nudges, clamped around the policy numbers."""
    scripted = f"Quote {_policy.describe(base, ref_qty, 1)}." + (
        f" Note: {'; '.join(base.exceptions)}." if base.exceptions else ""
    )
    prompt = (
        f"You are the sales agent of {factory.name}, a fictional factory in {factory.region}. "
        f"Personality: {factory.personality or factory.archetype}.\n"
        f"RFQ: {product}, quantity tiers {quantities}. Capacity: {factory.capacity.model_dump_json()}.\n"
        f"Your costing department proposes: unit prices {[base.tiers[q] for q in sorted(base.tiers)]} USD, "
        f"tooling {base.tooling_usd} USD, lead time {base.lead_time_days} days, terms '{base.payment_terms}', "
        f"exceptions {base.exceptions}.\nStay in character: adjust within ±10% if your personality justifies it "
        "and write a short reply to the buyer."
    )
    try:
        d = llm.complete_json("fast", prompt, FactoryQuoteDraft, max_tokens=800)
    except llm.LLMError as e:
        log.info("factory agent %s scripted (%s)", factory.id, e.reason)
        return base, scripted, False
    terms = _policy.clamp_llm_quote(base, d.unit_prices, d.tooling_usd, d.lead_time_days, d.payment_terms, d.exceptions)
    return terms, d.message.strip() or scripted, True


def _plan_counters(latest: list[Quote], factories: dict[str, Factory], ref_qty: int) -> dict[str, CounterDraft]:
    """Negotiation agent (route main): phrasing + price ask per factory. Empty on any LLM failure."""
    summary = "\n".join(
        f"- {q.factory_id} ({factories[q.factory_id].name}, {factories[q.factory_id].archetype}): {_policy.describe(q, ref_qty)}; "
        f"exceptions {q.exceptions}; on-time {_perf(factories[q.factory_id].past_performance)}"
        for q in latest
    )
    prompt = (
        f"You negotiate for a hardware founder buying {ref_qty:,} units. Quotes received (fictional factories):\n{summary}\n"
        "Policy: push unit price toward the cheapest credible quote (ask between -8% and -3%), tooling -10%, "
        "MOQ at or below the first order, shorter lead time if slow, 30% deposit / 70% before shipment. "
        "Return one counter per factory_id with a short professional message and the rationale."
    )
    try:
        plan = llm.complete_json("main", prompt, NegotiationPlan, max_tokens=1500)
    except llm.LLMError as e:
        log.info("negotiation plan scripted (%s)", e.reason)
        return {}
    return {c.factory_id: c for c in plan.counters if c.factory_id in factories}


def _recommend(latest: list[Quote], factories: dict[str, Factory], ref_qty: int) -> tuple[Quote, str, bool]:
    best = _policy.pick(latest, factories, ref_qty)
    ranked = sorted(latest, key=lambda q: _policy.value_score(factories[q.factory_id], q, ref_qty))
    runner_up = ranked[1] if len(ranked) > 1 else None
    def cost(q: Quote) -> str:
        return (f"${_policy.value_score(factories[q.factory_id], q, ref_qty):.2f}/unit risk-adjusted "
                f"(${_policy.effective_unit(q, ref_qty):.2f} incl. tooling at {ref_qty:,})")

    f = factories[best.factory_id]
    rationale = (
        f"{f.name}: lowest risk-adjusted cost, {cost(best)}; {_perf(f.past_performance, full=True)}, "
        f"{best.lead_time_days} days, {best.payment_terms}."
    )
    if runner_up is not None:
        r = factories[runner_up.factory_id]
        rationale += f" Runner-up {r.name}: {cost(runner_up)}"
        rationale += f" — {'; '.join(runner_up.exceptions)}." if runner_up.exceptions else "."
    prompt = (
        "Pick the best final quote for the founder (price incl. tooling amortisation, reliability, subcontracting, "
        f"lead time, payment terms). Quantity {ref_qty:,}. Policy pick: {best.factory_id}.\n"
        + "\n".join(
            f"- {q.factory_id} ({factories[q.factory_id].name}): {_policy.describe(q, ref_qty)}; exceptions {q.exceptions}; "
            f"on-time {_perf(factories[q.factory_id].past_performance)}; risk-adjusted "
            f"{_policy.value_score(factories[q.factory_id], q, ref_qty)}"
            for q in latest
        )
    )
    try:
        d = llm.complete_json("main", prompt, RecommendationDraft, max_tokens=600)
    except llm.LLMError:
        return best, rationale, False
    chosen = next((q for q in latest if q.factory_id == d.factory_id), None)
    if chosen is None:
        return best, rationale, False
    return chosen, d.rationale.strip() or rationale, True


def _translate(turns: list[NegotiationTurn]) -> None:
    targets = [t for t in turns if t.speaker == Speaker.platform_agent]
    if not targets:
        return
    prompt = "Translate each message to Simplified Chinese for a factory sales rep. Keep numbers unchanged.\n" + "\n".join(
        f"{i + 1}. {t.message}" for i, t in enumerate(targets)
    )
    try:
        out = llm.complete_json("cn", prompt, CnBatch, max_tokens=2000, timeout_s=20)
    except llm.LLMError:
        return
    if len(out.translations) == len(targets):
        for t, cn in zip(targets, out.translations):
            t.message_cn = cn.strip() or None


# --------------------------------------------------------------------------- negotiation


def _shortlist_ids(ctx: StageContext) -> list[str]:
    matching = ctx.artifact(7)
    ids = [m.factory_id for m in matching.shortlist] if matching is not None else []
    ids = [i for i in ids if network.get_factory(i) is not None]
    if len(ids) < N_FACTORIES:
        ids += [m.factory_id for m in match(ctx).shortlist if m.factory_id not in ids]
    return ids[:N_FACTORIES]


def _submit(rfq_id: str, t: _policy.QuoteTerms) -> Quote:
    return network.get_quote(
        network.submit_quote(rfq_id, t.tiers, t.tooling_usd, t.moq, t.lead_time_days, t.payment_terms, t.exceptions)
    )


def negotiate(ctx: StageContext) -> NegotiationArtifact:
    pack = _inputs.factory_pack(ctx)
    anchors, anchor_tooling, anchor_src = _inputs.anchors(ctx, pack)
    ref_qty = _inputs.reference_quantity(ctx, pack)
    matching = ctx.artifact(7)
    needed = [q.process for q in matching.queries] if matching is not None else [q.process for q in _inputs.build_queries(ctx, pack)[0]]
    quantities = sorted(anchors)
    factories = {fid: network.get_factory(fid) for fid in _shortlist_ids(ctx)}
    if len(factories) < N_FACTORIES:
        raise ValueError("fewer than 3 factories available for the RFQ")

    tx = Transcript()
    used: set[str] = set()

    # 1. RFQs
    rfq_ids: dict[str, str] = {}
    for fid in factories:
        rfq_ids[fid] = network.request_quote(fid, pack.id, quantities, project_id=ctx.project.id, product_name=pack.product_name)
        tx.add(
            rfq_ids[fid], fid, Speaker.platform_agent,
            f"RFQ sent with Factory Pack {pack.id}: {pack.product_name}, {_fmt_q(quantities)} units, "
            f"markets {' + '.join(pack.target_markets)}. Please quote unit price per tier, tooling, MOQ, lead time and terms.",
        )

    # 2. Factory agents (parallel: 3 independent LLM calls)
    bases = {fid: _policy.initial_quote(f, anchors, anchor_tooling, needed, ref_qty) for fid, f in factories.items()}
    with ThreadPoolExecutor(max_workers=N_FACTORIES) as pool:
        replies = dict(zip(factories, pool.map(lambda fid: _factory_agent(factories[fid], bases[fid], quantities, pack.product_name, ref_qty), factories)))
    first: dict[str, Quote] = {}
    latest: dict[str, Quote] = {}
    for fid, (terms, message, llm_used) in replies.items():
        if llm_used:
            used.add("fast")
        q = _submit(rfq_ids[fid], terms)
        first[fid] = latest[fid] = q
        tx.add(rfq_ids[fid], fid, Speaker.factory_agent, message, quote_id=q.id)

    # 3. Rounds of counters
    for round_no in range(1, MAX_ROUNDS + 1):
        if round_no == 1:
            targets = list(factories)
            llm_plan = _plan_counters(list(latest.values()), factories, ref_qty)
            if llm_plan:
                used.add("main")
        else:  # round 2: only the current front-runner, if it still has room to move
            lead = _policy.pick(list(latest.values()), factories, ref_qty)
            floor = _policy.price_at(first[lead.factory_id].tiers, ref_qty) * (1 - _policy.persona_for(factories[lead.factory_id]).concession)
            if _policy.price_at(lead.tiers, ref_qty) <= floor + 0.005:
                break
            targets, llm_plan = [lead.factory_id], {}
        for fid in targets:
            q = latest[fid]
            c = _policy.counter_for(q, list(latest.values()), factories, ref_qty, round_no)
            message, rationale = c.message, c.rationale
            if fid in llm_plan:
                d = llm_plan[fid]
                c.changes["unit_price_pct"] = round(min(-1.0, max(-8.0, d.unit_price_pct)), 1)
                message, rationale = d.message.strip() or message, d.rationale.strip() or rationale
            countered = network.counter_offer(q.id, c.changes, rationale)
            tx.add(rfq_ids[fid], fid, Speaker.platform_agent, message, quote_id=countered.id,
                   proposed_changes=c.changes, rationale=rationale)
            terms = _policy.respond(factories[fid], first[fid], q, c.changes)
            revised = _submit(rfq_ids[fid], terms)
            latest[fid] = revised
            moved = (1 - _policy.price_at(revised.tiers, ref_qty) / _policy.price_at(q.tiers, ref_qty)) * 100
            tx.add(rfq_ids[fid], fid, Speaker.factory_agent,
                   f"Revised {_policy.describe(revised, ref_qty)}"
                   + (f" — {moved:.1f}% off, that is our floor." if moved < abs(c.changes['unit_price_pct']) - 0.05 else " — accepted your price."),
                   quote_id=revised.id)

    # 4. Recommendation
    best, rationale, rec_llm = _recommend(list(latest.values()), factories, ref_qty)
    if rec_llm:
        used.add("main")
    tx.add(rfq_ids[best.factory_id], best.factory_id, Speaker.platform_agent,
           f"Recommendation to founder: accept {factories[best.factory_id].name} {_policy.describe(best, ref_qty)}. Awaiting approval.",
           quote_id=best.id, rationale=rationale)
    _translate(tx.turns)

    quotes = [q for fid in factories for q in network.list_quotes(rfq_ids[fid])]
    generated_by = f"llm:{llm.model_for('main')}" if "main" in used else f"llm:{llm.model_for('fast')}" if "fast" in used else "code"
    assumptions = [
        Assumption(id="a8_network", text="Factories, quotes, counters and replies are simulated (production MCP demo network).",
                   label="fictional", source="factory_mcp (demo data)", stage=8),
        Assumption(id="a8_anchor", text=f"Factory quotes are anchored on {anchor_src} × each factory's personality margin; "
                   "subcontracted processes add 3% each.", label="estimate", stage=8),
        Assumption(id="a8_policy", text=f"Negotiation policy: max {MAX_ROUNDS} rounds; price, tooling, MOQ ≤ {ref_qty:,}, "
                   "lead time, 30% deposit / 70% before shipment; pick = lowest risk-adjusted cost incl. tooling.",
                   label="estimate", stage=8),
    ]
    if not used:
        assumptions.append(Assumption(id="a8_scripted", text="No LLM key: agents ran the deterministic scripted policy "
                                      "(same numbers, template messages).", label="estimate", stage=8))
    return NegotiationArtifact(
        project_id=ctx.project.id,
        generated_by=generated_by,
        assumptions=assumptions,
        rfqs=[network.get_rfq(rfq_ids[fid]) for fid in factories],
        quotes=quotes,
        transcript=tx.turns,
        recommendation=Recommendation(factory_id=best.factory_id, quote_id=best.id, rationale=rationale),
    )


# --------------------------------------------------------------------------- approval


def _live(art: NegotiationArtifact | None) -> bool:
    if art is None or art.fallback:
        return False
    try:
        network.get_quote(art.recommendation.quote_id)
    except network.NotFoundError:
        return False
    return True


def approve(ctx: StageContext, art: NegotiationArtifact, quote_id: str | None) -> NegotiationArtifact:
    quote_id = quote_id or art.recommendation.quote_id
    if quote_id not in {q.id for q in art.quotes}:
        raise ValueError(f"quote {quote_id} is not part of this negotiation")
    order = network.accept_quote(quote_id)
    q = network.get_quote(quote_id)
    rfq_ids = [r.id for r in art.rfqs]
    art.quotes = [x for rid in rfq_ids for x in network.list_quotes(rid)]
    art.rfqs = [network.get_rfq(rid) for rid in rfq_ids]
    pack = ctx.factory_pack
    qty = max(_inputs.reference_quantity(ctx, pack), q.moq)
    src = f"Accepted quote v{q.version} ({order.order_id}) — {DEMO}"
    art.final_terms = FinalTerms(
        factory_id=q.factory_id,
        quote_id=q.id,
        quantity=qty,
        unit_price=LabeledValue(value=_policy.price_at(q.tiers, qty), unit="USD", label="fictional", source_or_assumption=src),
        tooling=LabeledValue(value=q.tooling_usd, unit="USD", label="fictional", source_or_assumption=src),
        moq=q.moq,
        lead_time_days=LabeledValue(value=float(q.lead_time_days), unit="days", label="fictional", source_or_assumption=src),
        payment_terms=q.payment_terms,
    )
    art.user_approved = True
    rfq_id = q.rfq_id
    n = len(art.transcript)
    art.transcript += [
        NegotiationTurn(id=f"t{n + 1}", rfq_id=rfq_id, factory_id=q.factory_id, turn=n + 1, speaker=Speaker.user,
                        message=f"Approved quote v{q.version}.", quote_id=q.id),
        NegotiationTurn(id=f"t{n + 2}", rfq_id=rfq_id, factory_id=q.factory_id, turn=n + 2, speaker=Speaker.platform_agent,
                        message=f"Quote accepted — order draft {order.order_id} for {qty:,} units at "
                                f"${art.final_terms.unit_price.value:.2f}, tooling ${q.tooling_usd:,.0f}, {q.payment_terms}.",
                        quote_id=q.id),
    ]
    return art


@stage_handler(8)
def run(ctx: StageContext) -> NegotiationArtifact:
    if ctx.inputs.get("approve"):
        prior = ctx.artifact(8)
        art = prior.model_copy(deep=True) if _live(prior) else negotiate(ctx)
        return approve(ctx, art, ctx.inputs.get("quote_id"))
    return negotiate(ctx)
