"""Factory Pack assembly (PRD §8.1). Owner: W6.

`@provider("factory_pack")`: ctx → FactoryPack, built from the validated artifacts of stages 1-6.
Any section whose source stage is missing/empty is taken from the example fixture and the pack is flagged
`fallback: true`. The provider never raises for missing data: the worst case is the whole cached example.
"""

from __future__ import annotations

import logging
from typing import Any

from contracts.artifacts import (
    CACHED_NOTE,
    Assumption,
    BOMItem,
    ComponentRisk,
    FactoryPack,
    FactoryQuestion,
    Label,
    StructuredSpec,
    utcnow,
)

from api.export import translate_cn as cn
from api.stages.registry import StageContext, provider

log = logging.getLogger("export.factory_pack")

SECTIONS = {
    1: "Product summary and target markets",
    2: "Structured spec",
    3: "CAD and drawings",
    4: "BOM with component risk and alternatives",
    5: "DFM alerts and resolutions",
    6: "Certification checklist by market",
    7: "Target quantities and cost estimate",
    8: "Questions for the factory",
    9: "Assumption register",
    10: "Engineering & prototype path",
}

_SEV_ORDER = {"critical": 0, "major": 1, "minor": 2}

# Generic factory questions: {n} placeholders are filled from the pack. (EN, CN) written by hand.
GENERIC_QUESTIONS = [
    (
        "What are your MOQ and lead time for {q1} units, and how do they change at {q2} and {q3} units?",
        "起订量和交期：{q1} 件的起订量和交期是多少？数量增至 {q2} 件和 {q3} 件时如何变化？",
    ),
    (
        "Please confirm the tolerances in the spec and flag any tolerance or finish you cannot hold.",
        "请确认规格书中的公差要求，并指出无法保证的公差或表面处理。",
    ),
    (
        "Which BOM components do you source yourselves, and do you accept the listed alternatives for high-risk parts?",
        "BOM 中哪些元器件由贵司自行采购？对于高风险物料，是否接受清单中列出的替代方案？",
    ),
    (
        "What payment terms and sample rounds (T0, T1, golden sample) do you propose, with dates?",
        "请说明贵司建议的付款条款和打样轮次（T0、T1、金样），并给出日期。",
    ),
]


def _example_pack(ctx: StageContext) -> FactoryPack:
    from api.stages.runner import FACTORY_PACK_STAGE, load_fixture

    return load_fixture(ctx.project.example, FACTORY_PACK_STAGE, ctx.project.id)


def _enrich_bom(bom: list[BOMItem], dfm: Any, costs: Any) -> list[BOMItem]:
    """Attach DFM component risks/alternatives and stage-5 prices to BOM lines that lack them."""
    risks = {r.bom_item_id: r for r in (dfm.component_risks if dfm else [])}
    prices = {line.bom_item_id: line for line in (costs.bom_lines if costs else [])}
    out = []
    for item in bom:
        item = item.model_copy(deep=True)
        r = risks.get(item.id)
        if r is not None:
            if item.risk is None:
                item.risk = ComponentRisk(level=r.level, reasons=list(r.reasons))
            if not item.alternative and r.alternatives:
                item.alternative = "; ".join(r.alternatives)
        line = prices.get(item.id)
        if line is not None and item.unit_cost_est is None:
            item.unit_cost_est = line.unit_price
        out.append(item)
    return [BOMItem.model_validate(i.model_dump()) for i in out]


def _dfm_questions(dfm: Any, limit: int = 3) -> list[tuple[str, str | None]]:
    if not dfm:
        return []
    open_issues = sorted((i for i in dfm.issues if not i.resolved), key=lambda i: _SEV_ORDER.get(i.severity, 3))
    out = []
    for i in open_issues[:limit]:
        en = f"DFM {i.severity} — {i.description} Proposed fix: {i.fix} Can you accommodate this, and at what cost or lead-time impact?"
        cn_fb = f"DFM 问题（{cn.SEVERITY_CN.get(i.severity, i.severity)}，{i.category}，编号 {i.id}）：详见资料包第 5 节英文说明。请评估可行性、修改方案及对成本和交期的影响。"
        out.append((en, cn_fb))
    return out


def _build_questions(ctx: StageContext, brief: Any, dfm: Any, quantities: list[int], example: FactoryPack, summary_en: str, name: str, markets: list[str]) -> tuple[str, list[FactoryQuestion]]:
    q = (quantities + [quantities[-1]] * 3)[:3] if quantities else [500, 2000, 10000]
    generic = [(en.format(q1=f"{q[0]:,}", q2=f"{q[1]:,}", q3=f"{q[2]:,}"), zh.format(q1=f"{q[0]:,}", q2=f"{q[1]:,}", q3=f"{q[2]:,}")) for en, zh in GENERIC_QUESTIONS]
    # Cached example (stage 1 or 4 missing/fallback): curated, pre-translated questions of the example pack.
    cached = brief is None or brief.fallback or dfm is None or dfm.fallback
    curated = [(fq.en, fq.cn) for fq in example.questions] if cached else _dfm_questions(dfm)
    pairs = curated + [generic[0], generic[3]] + [generic[1], generic[2]]
    pairs = pairs[:8]
    summary_cn, cn_list, source = cn.translate(summary_en, name, markets, quantities, pairs)
    if source == "fallback" and (brief is None or brief.fallback) and example.product_summary_cn:
        summary_cn = example.product_summary_cn  # pre-translated summary of the cached example
    questions = [
        FactoryQuestion(id=f"fq{i + 1}", en=en, cn=zh, cn_review_note=cn.REVIEW_NOTE)
        for i, ((en, _), zh) in enumerate(zip(pairs, cn_list))
    ]
    log.info("factory pack CN source: %s", source)
    return summary_cn, questions


def _merge_assumptions(ctx: StageContext, extra: list[Assumption]) -> list[Assumption]:
    seen: set[str] = set()
    used_ids: set[str] = set()
    out: list[Assumption] = []
    for n in sorted(ctx.artifacts):
        for a in ctx.artifacts[n].assumptions:
            key = a.text.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            a = a.model_copy(deep=True)
            if a.stage is None:
                a.stage = n
            if a.id in used_ids:
                a.id = f"s{n}_{a.id}"
            used_ids.add(a.id)
            out.append(a)
    for a in extra:
        if a.text.strip().lower() not in seen:
            out.append(a)
    return out


def _engineering(ctx: StageContext) -> Any:
    """Section 10 (W20): engineering checks, standards, power budget, prototype path, firmware note. Never blocks the pack."""
    try:
        from api.engineering.service import engineering_for_ctx

        return engineering_for_ctx(ctx)
    except Exception as e:  # noqa: BLE001
        log.warning("engineering section skipped: %s", e)
        return None


@provider("factory_pack")
def build_factory_pack(ctx: StageContext) -> FactoryPack:
    example = _example_pack(ctx)
    brief, spec, dfm, costs = ctx.artifact(1), ctx.artifact(3), ctx.artifact(4), ctx.artifact(5)
    missing: list[str] = []  # human-readable section names taken from the cached example
    cached_sources = sorted(n for n in (1, 3, 4, 5) if ctx.artifact(n) is not None and ctx.artifact(n).fallback)

    # 1. Product summary + markets
    if brief is not None:
        name = brief.product_name
        markets = list(brief.target_markets)
        quantities = list(brief.target_volumes) or ([t.quantity for t in costs.tiers] if costs else [])
        qtxt = " / ".join(f"{v:,}" for v in quantities)
        summary_en = f"{brief.one_liner} Target volumes: {qtxt} units; markets: {', '.join(markets)}."
    else:
        missing.append(SECTIONS[1])
        name, markets, quantities, summary_en = example.product_name, list(example.target_markets), list(example.target_quantities), example.product_summary

    # 2-3. Spec + CAD
    if spec is not None and spec.parts:
        structured = StructuredSpec(overall_dimensions=spec.overall_dimensions, weight=spec.weight, parts=spec.parts, tolerances=spec.tolerances)
        cad_files = list(spec.cad_files) or list(example.cad_files)
        if not spec.cad_files:
            missing.append(SECTIONS[3])
        bom = _enrich_bom(spec.bom, dfm, costs) if spec.bom else list(example.bom)
        if not spec.bom:
            missing.append(SECTIONS[4])
    else:
        missing += [SECTIONS[2], SECTIONS[3], SECTIONS[4]]
        structured, cad_files, bom = example.spec, list(example.cad_files), list(example.bom)

    # 5-6. DFM + certifications
    if dfm is not None and dfm.issues:
        dfm_alerts = list(dfm.issues)
    else:
        missing.append(SECTIONS[5])
        dfm_alerts = list(example.dfm_alerts)
    if dfm is not None and dfm.certifications:
        certs = list(dfm.certifications)
    else:
        missing.append(SECTIONS[6])
        certs = list(example.certifications)

    # 7. Quantities + cost estimate
    if costs is not None and costs.tiers:
        cost_estimate = list(costs.tiers)
        target_quantities = quantities or [t.quantity for t in cost_estimate]
    else:
        missing.append(SECTIONS[7])
        cost_estimate, target_quantities = list(example.cost_estimate), quantities or list(example.target_quantities)

    # 8. Questions (EN + CN)
    dfm_for_q = dfm if (dfm is not None and dfm.issues) else None
    summary_cn, questions = _build_questions(ctx, brief, dfm_for_q, target_quantities, example, summary_en, name, markets)

    # 9. Assumption register
    extra = [Assumption(id="cn1", text="Chinese text in this pack is machine-translated — to be reviewed by a native speaker.", label=Label.estimate, source=None, stage=None)]
    for section in missing:
        extra.append(Assumption(id=f"fb_{len(extra)}", text=f"Section '{section}' shows the cached example ({ctx.project.example or 'desk_lamp'}) because its source stage is missing.", label=Label.estimate, source=None, stage=None))
    for n in cached_sources:
        extra.append(Assumption(id=f"fs_{n}", text=f"Stage {n} output is a cached example (stage fell back to fixtures).", label=Label.estimate, source=None, stage=n))
    register = _merge_assumptions(ctx, extra)
    if not register:
        register = list(example.assumption_register)

    prev = ctx.factory_pack
    version = (prev.version + 1) if prev is not None else 1
    stage_fallbacks = [n for n in range(1, 8) if (a := ctx.artifact(n)) is not None and a.fallback]
    slug = ctx.project.id.removeprefix("demo_")
    return FactoryPack(
        id=f"fp_{slug}_v{version}",
        project_id=ctx.project.id,
        version=version,
        created_at=utcnow(),
        fallback=bool(missing) or bool(cached_sources),
        cached_note=CACHED_NOTE if stage_fallbacks else None,
        fallback_stages=stage_fallbacks,
        product_name=name,
        product_summary=summary_en,
        product_summary_cn=summary_cn,
        target_markets=markets,
        spec=structured,
        cad_files=cad_files,
        bom=bom,
        dfm_alerts=dfm_alerts,
        certifications=certs,
        target_quantities=target_quantities,
        cost_estimate=cost_estimate,
        questions=questions,
        assumption_register=register,
        engineering=_engineering(ctx),
    )
