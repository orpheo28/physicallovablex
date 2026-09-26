"""Stage 7/8 inputs derived from the project state (W5). Private helpers, not auto-imported."""

from __future__ import annotations

from collections import OrderedDict

from contracts.artifacts import FactoryPack, ProcessType, SearchCapacityQuery

from api.stages.registry import StageContext

# Desk-lamp stage-5 numbers, used only when neither stage 5 nor the Factory Pack carries tiers.
DEFAULT_ANCHORS = {500: 13.59, 2000: 12.5, 10000: 11.5}
DEFAULT_TOOLING = 10100.0
FACTORY_CERTS = ["ISO 9001"]


def factory_pack(ctx: StageContext) -> FactoryPack:
    if ctx.factory_pack is not None:
        return ctx.factory_pack
    from api.stages import runner  # lazy: assembles via W6's provider, else fixture

    return runner.get_factory_pack(ctx.project.id)


def anchors(ctx: StageContext, pack: FactoryPack | None = None) -> tuple[dict[int, float], float, str]:
    """Stage-5 ex-works unit cost per tier + tooling → what factory agents anchor their quotes on."""
    costs = ctx.artifact(5)
    if costs is not None and costs.tiers:
        return (
            {t.quantity: t.unit_cost.value for t in costs.tiers},
            costs.tooling_total.value,
            "stage 5 cost tiers + tooling total",
        )
    if pack is not None and pack.cost_estimate:
        first = min(pack.cost_estimate, key=lambda t: t.quantity)
        return (
            {t.quantity: t.unit_cost.value for t in pack.cost_estimate},
            round(first.tooling_amortisation.value * first.quantity, 2) or DEFAULT_TOOLING,
            "Factory Pack cost estimate",
        )
    return dict(DEFAULT_ANCHORS), DEFAULT_TOOLING, "desk-lamp reference numbers (no stage 5)"


def reference_quantity(ctx: StageContext, pack: FactoryPack | None = None) -> int:
    costs = ctx.artifact(5)
    if costs is not None and costs.reference_quantity:
        return int(costs.reference_quantity)
    qs = sorted(pack.target_quantities) if pack is not None and pack.target_quantities else [2000]
    return qs[len(qs) // 2]


def build_queries(ctx: StageContext, pack: FactoryPack) -> tuple[list[SearchCapacityQuery], list[float]]:
    """One search_capacity query per process (process per part from stage 6, else the spec's process_hint),
    weighted by the number of parts using it, plus final assembly for multi-part products."""
    plan = ctx.artifact(6)
    by_part = {s.part_id: s.process for s in plan.steps} if plan is not None else {}
    groups: OrderedDict[str, list] = OrderedDict()
    for part in pack.spec.parts:
        proc = by_part.get(part.id) or part.process_hint
        if proc is None:
            continue
        groups.setdefault(str(getattr(proc, "value", proc)), []).append(part)
    if not groups:
        raise ValueError("Factory Pack has no part with a manufacturing process")
    qty = reference_quantity(ctx, pack)
    queries, weights = [], []
    for proc, parts in groups.items():
        queries.append(
            SearchCapacityQuery(
                process=ProcessType(proc), material=parts[0].material, quantity=qty, certifications_required=FACTORY_CERTS
            )
        )
        weights.append(float(len(parts)))
    if len(pack.spec.parts) > 1 and "assembly" not in groups:
        queries.append(
            SearchCapacityQuery(process=ProcessType.assembly, material="any", quantity=qty, certifications_required=FACTORY_CERTS)
        )
        weights.append(1.0)
    return queries, weights
