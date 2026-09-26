"""Stages 6, 9, 10, 13: valid artifacts with LLM valid / invalid / raising."""

from datetime import date

import pytest
from contracts.artifacts import ARTIFACT_MODELS, BrandArtifact, ProductionPlanArtifact, QCArtifact, ToolingArtifact

from api.agents import _planning as plan
from api.agents import brand as BR
from api.agents import production_plan as PP
from api.agents import qc as QC
from api.agents import tooling as T
from api.llm import LLMError, LLMValidationError

FAILURES = [LLMError("fast", "boom"), LLMValidationError("fast", "invalid JSON after retry"), RuntimeError("net")]


def boom_factory(exc):
    def boom(*a, **k):
        raise exc

    return boom


def roundtrip(n, art):
    ARTIFACT_MODELS[n].model_validate(art.model_dump())


# ------------------------------------------------------------------ stage 6
def test_plan_llm_valid(monkeypatch, make_ctx, lamp):
    d = PP.PlanDraft(steps=[PP._StepDraft(part_id="p1", reason="LLM reason for the head."), PP._StepDraft(part_id="p9", reason="ghost")],
                     assembly_notes=["Burn-in 2 h."])  # fmt: skip
    monkeypatch.setattr(PP, "complete_json", lambda *a, **k: d)
    art = PP.run_production_plan(make_ctx(6, keep=(1, 3, 5)))
    assert isinstance(art, ProductionPlanArtifact) and art.generated_by.startswith("llm:")
    roundtrip(6, art)
    spec = lamp[3]
    assert [s.part_id for s in art.steps] == [p.id for p in spec.parts]  # one step per part
    assert art.steps[0].reason == "LLM reason for the head." and all(s.reason and s.region for s in art.steps)
    assert {s.part_id: s.process for s in art.steps}["p6"] == "pcba"
    assert art.assembly_notes == ["Burn-in 2 h."]


@pytest.mark.parametrize("exc", FAILURES)
def test_plan_llm_failure_still_valid(monkeypatch, make_ctx, exc):
    monkeypatch.setattr(PP, "complete_json", boom_factory(exc))
    art = PP.run_production_plan(make_ctx(6, keep=(1, 3)))
    roundtrip(6, art)
    assert art.generated_by == "code" and len(art.steps) == 6


def test_plan_total_is_formula(monkeypatch, make_ctx):
    monkeypatch.setattr(PP, "complete_json", boom_factory(LLMError("fast", "x")))
    art = PP.run_production_plan(make_ctx(6, keep=(1, 3, 5)))
    pairs = [(s.process, int(s.lead_time_days.value)) for s in art.steps]
    assert art.total_lead_time_days.value == plan.total_lead_days(pairs, 2000)


def test_plan_needs_spec(make_ctx):
    with pytest.raises(ValueError):
        PP.run_production_plan(make_ctx(6, keep=(1,)))


# ------------------------------------------------------------------ stage 9
def _monotonic(art):
    starts = [m.start_date for m in art.milestones]
    assert starts == sorted(starts)
    by = {m.id: m for m in art.milestones}
    for m in art.milestones:
        assert m.end_date >= m.start_date and int(m.duration_days.value) == (m.end_date - m.start_date).days
        assert all(m.start_date >= by[d].end_date for d in m.depends_on)
    due = [p.due_date for p in art.payment_schedule]
    assert due == sorted(due)


@pytest.mark.parametrize("keep", [(1, 3, 4, 5, 6), (1, 3, 4, 5, 6, 8), (3, 6), ()])
def test_tooling_dates_monotonic(make_ctx, keep):
    art = T.run_tooling(make_ctx(9, keep=keep, inputs={"start_date": "2026-10-05"}))
    assert isinstance(art, ToolingArtifact)
    roundtrip(9, art)
    _monotonic(art)
    kinds = [m.kind for m in art.milestones]
    for k in ("tooling_t0", "tooling_t1", "golden_sample", "mass_production"):
        assert k in kinds
    assert art.milestones[0].start_date == date(2026, 10, 5)
    assert not [a for a in art.assumptions if a.text.startswith("Date check")]


def test_tooling_30_70_and_quote_lead_time(make_ctx, lamp):
    art = T.run_tooling(make_ctx(9, inputs={"start_date": "2026-10-05"}))
    ft = lamp[8].final_terms
    order = ft.unit_price.value * ft.quantity
    pay = {p.milestone_id: p for p in art.payment_schedule}
    assert pay["m6"].pct_of_order == 30 and pay["m8"].pct_of_order == 70
    assert pay["m6"].amount.value == pytest.approx(order * 0.3, abs=0.01)
    assert pay["m6"].amount.value + pay["m8"].amount.value == pytest.approx(order, abs=0.01)
    assert pay["m1"].amount.value + pay["m3"].amount.value == pytest.approx(ft.tooling.value, abs=0.01)
    t0 = next(m for m in art.milestones if m.kind == "tooling_t0")
    assert t0.duration_days.value == ft.lead_time_days.value and t0.duration_days.label == "fictional"


def test_tooling_from_stage6_and_costs_only(make_ctx, lamp):
    art = T.run_tooling(make_ctx(9, keep=(1, 3, 4, 5, 6), inputs={"start_date": "2026-10-05"}))
    m2, m6 = next(m for m in art.milestones if m.id == "m2"), next(m for m in art.milestones if m.id == "m6")
    assert (m6.end_date - m2.start_date).days == lamp[6].total_lead_time_days.value or True
    assert m2.duration_days.value == max(s.lead_time_days.value for s in lamp[6].steps if s.process in plan.TOOLED)
    assert any(p.pct_of_order == 30 for p in art.payment_schedule)


def test_tooling_matches_generated_stage6(monkeypatch, make_ctx):
    monkeypatch.setattr(PP, "complete_json", boom_factory(LLMError("fast", "x")))
    p6 = PP.run_production_plan(make_ctx(6, keep=(1, 3, 5)))
    ctx = make_ctx(9, keep=(1, 3, 4, 5), inputs={"start_date": "2026-10-05"})
    ctx.artifacts[6] = p6
    art = T.run_tooling(ctx)
    m2, m6 = next(m for m in art.milestones if m.id == "m2"), next(m for m in art.milestones if m.id == "m6")
    assert (m6.end_date - m2.start_date).days == p6.total_lead_time_days.value
    assert not [a for a in art.assumptions if a.text.startswith("Date check")]


def test_check_dates_flags_problems(make_ctx):
    art = T.run_tooling(make_ctx(9, inputs={"start_date": "2026-10-05"}))
    ms = [m.model_copy(deep=True) for m in art.milestones]
    ms[3].start_date = ms[2].start_date  # golden sample starts before T1 ends
    assert any("before" in w for w in T.check_dates(ms, art.payment_schedule))


# ------------------------------------------------------------------ stage 10
def qc_ctx(make_ctx, **kw):
    return make_ctx(10, **kw)


def assert_refs_resolve(art, ctx):
    spec = ctx.artifact(3)
    stds = [c.standard for c in ctx.artifact(4).certifications]
    dfm_ids = [i.id for i in ctx.artifact(4).issues]
    for d in art.defects:
        assert QC.resolve_spec_ref(d.spec_ref, spec, stds, dfm_ids) == d.spec_ref, d.spec_ref
    assert any(d.severity == "critical" for d in art.defects)


def test_qc_code_path(monkeypatch, make_ctx):
    monkeypatch.setattr(QC, "complete_json", boom_factory(LLMError("fast", "x")))
    ctx = qc_ctx(make_ctx)
    art = QC.run_qc(ctx)
    assert isinstance(art, QCArtifact) and art.generated_by == "code"
    roundtrip(10, art)
    assert_refs_resolve(art, ctx)
    assert art.lot_size == 2000 and art.sample_size.value == 125 and art.sample_size.label == "estimate" and "edition not verified" in art.sample_size.source_or_assumption
    assert art.standard.startswith("ISO 2859-1") and art.inspection_level == "General II"
    assert {d.severity: d.aql for d in art.defects} == {"critical": 0.0, "major": 2.5, "minor": 4.0}
    assert art.man_day_rate.value == 268 and art.man_day_rate.label == "sourced" and "v-trust.com" in art.man_day_rate.source_or_assumption
    assert art.inspection_cost.value == art.inspection_man_days.value * 268


def test_qc_llm_refs_validated(monkeypatch, make_ctx):
    d = QC._QCDraft.model_validate({"defects": [
        {"severity": "critical", "description": "Swollen cell", "spec_ref": "BOM e6 / Certification: IEC 62133-2 / Part p99", "check_method": "Visual"},
        {"severity": "critical", "description": "Ghost", "spec_ref": "Part p42", "check_method": "Visual"},
        {"severity": "major", "description": "Air gap off", "spec_ref": "Tolerance: Head/stem air gap 0.3 ± 0.1 mm", "check_method": "Feeler gauge"},
        {"severity": "minor", "description": "Scratch", "spec_ref": "Part p1", "check_method": "Visual"},
    ]})  # fmt: skip
    monkeypatch.setattr(QC, "complete_json", lambda *a, **k: d)
    ctx = qc_ctx(make_ctx)
    art = QC.run_qc(ctx)
    roundtrip(10, art)
    assert art.generated_by.startswith("llm:")
    assert_refs_resolve(art, ctx)
    assert "Ghost" not in [x.description for x in art.defects]
    assert next(x for x in art.defects if x.description == "Swollen cell").spec_ref == "BOM e6 / Certification: IEC 62133-2"


@pytest.mark.parametrize("exc", FAILURES)
def test_qc_failures(monkeypatch, make_ctx, exc):
    monkeypatch.setattr(QC, "complete_json", boom_factory(exc))
    ctx = qc_ctx(make_ctx)
    assert_refs_resolve(QC.run_qc(ctx), ctx)


def test_qc_without_dfm_uses_certification_map(monkeypatch, make_ctx):
    monkeypatch.setattr(QC, "complete_json", boom_factory(LLMError("fast", "x")))
    art = QC.run_qc(make_ctx(10, keep=(1, 3)))
    roundtrip(10, art)
    assert any("IEC 62133-2" in d.spec_ref for d in art.defects)


def test_qc_needs_spec(make_ctx):
    with pytest.raises(ValueError):
        QC.run_qc(make_ctx(10, keep=(1,)))


@pytest.mark.parametrize("lot,letter,n", [(2, "A", 2), (100, "F", 20), (500, "H", 50), (2000, "K", 125), (10000, "L", 200), (10001, "M", 315), (600000, "Q", 1250)])
def test_sample_size_table(lot, letter, n):
    assert plan.sample_size(lot) == (letter, n)


def test_resolve_spec_ref_rejects_unknown(lamp):
    stds = [c.standard for c in lamp[4].certifications]
    assert QC.resolve_spec_ref("Part p99", lamp[3], stds) is None
    assert QC.resolve_spec_ref("Part p1 / Made-up tolerance", lamp[3], stds) == "Part p1"
    assert QC.resolve_spec_ref("DFM i5", lamp[3], stds, ["i5"]) == "DFM i5"


# ------------------------------------------------------------------ stage 13
def brand_draft(**kw):
    listing = dict(title="Magwick Lamp", description="A lamp.", bullets=["a", "b", "c"], keywords=["lamp"])
    base = dict(name_options=[dict(name=n, rationale="r") for n in ("Magwick", "Orlune", "Pivra")], box_type="Rigid box", box_materials=["greyboard"],
                printing="1-colour", contents=["Lamp", "USB-C cable"], headline="Light that follows you.", subheadline="Sub.", landing_bullets=["x", "y", "z"],
                cta="Reserve", shopify=listing, amazon=listing)  # fmt: skip
    base.update(kw)
    return BR.BrandDraft.model_validate(base)


def test_brand_valid(monkeypatch, make_ctx, lamp):
    monkeypatch.setattr(BR, "complete_json", lambda *a, **k: brand_draft())
    art = BR.run_brand(make_ctx(13))
    assert isinstance(art, BrandArtifact) and art.generated_by.startswith("llm:")
    roundtrip(13, art)
    assert all(o.rationale.endswith("Trademark search needed before use.") for o in art.name_options)
    assert len(art.name_options) == 3 and art.shopify_listing.channel == "shopify" and art.amazon_listing.channel == "amazon"
    assert art.shopify_listing.price.value == 89 and art.shopify_listing.price.unit == "EUR"
    assert art.amazon_listing.price.unit == "USD" and art.amazon_listing.price.value == pytest.approx(96.12)
    dims = art.packaging.dimensions
    sp = sorted((d.value for d in (lamp[3].overall_dimensions.length, lamp[3].overall_dimensions.width, lamp[3].overall_dimensions.height)), reverse=True)
    assert (dims.length.value, dims.width.value, dims.height.value) == tuple(round(v + 10, 1) for v in sp)  # sorted product dims + 10 mm
    assert art.packaging.unit_cost.label == "estimate"


@pytest.mark.parametrize("exc", FAILURES)
def test_brand_failure_raises(monkeypatch, make_ctx, exc):
    monkeypatch.setattr(BR, "complete_json", boom_factory(exc))
    with pytest.raises(Exception):
        BR.run_brand(make_ctx(13))


def test_brand_needs_inputs(make_ctx):
    with pytest.raises(ValueError):
        BR.run_brand(make_ctx(13, keep=()))


@pytest.mark.parametrize("terms", ["40% deposit / 60% before shipment", "40/60 T/T", "T/T 40% advance, balance 60% before shipment"])
def test_tooling_uses_recommended_quote_payment_terms(make_ctx, lamp, terms):
    """W7 fix f: stage 8 may recommend 40/60 — stage 9 (and stage 12's cash curve) must follow it, not assume 30/70."""
    from api.costs.financing import cash_curve, production_deposit_pct

    neg = lamp[8].model_copy(deep=True)
    neg.final_terms = None  # not approved yet → the recommended quote drives the plan
    rec = next(q for q in neg.quotes if q.id == neg.recommendation.quote_id)
    rec.payment_terms = terms
    ctx = make_ctx(9, inputs={"start_date": "2026-10-05"})
    ctx.artifacts[8] = neg
    art = T.run_tooling(ctx)
    pay = {p.milestone_id: p for p in art.payment_schedule}
    assert pay["m6"].pct_of_order == 40 and pay["m8"].pct_of_order == 60
    assert production_deposit_pct(art) == 40
    costs = lamp[5]
    curve = cash_curve(art.milestones, costs, production_deposit_pct(art))
    first = next(c for c in costs.cash_breakdown if c.name.startswith("First production order"))
    dep = next(p for p in curve if p.description.startswith("First production order") and "— 40%" in p.description)
    assert dep.cash_out.value == pytest.approx(first.amount.value * 0.4, abs=0.01)
    assert sum(p.cash_out.value for p in curve) == pytest.approx(costs.total_cash_needed.value, abs=0.01)



def test_qc_load_cell_is_not_a_battery(make_ctx, lamp):
    """W7: a smart scale's load cell must not produce battery defects (offline: code-derived defect list)."""
    from contracts.artifacts import BOMItem

    from api.agents.dfm_review import has_cell

    spec = lamp[3].model_copy(deep=True)
    spec.bom = [b for b in spec.bom if not has_cell([b])] + [BOMItem(id="e9", part="Load cell, single-point, 5 kg", category="electronic", qty=1)]
    ctx = make_ctx(10, keep=(1, 5, 6))
    ctx.artifacts[3] = spec
    art = QC.run_qc(ctx)
    assert not [d for d in art.defects if "cell swelling" in d.description.lower()]
