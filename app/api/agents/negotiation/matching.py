"""Stage 7 — Factory matching (W5). Deterministic scoring via the production MCP's search_capacity logic."""

from __future__ import annotations

from contracts.artifacts import Assumption, MatchingArtifact, process_label

from api.agents.negotiation import _inputs
from api.stages.registry import StageContext, stage_handler
from factory_mcp import network

SHORTLIST_SIZE = 5


def match(ctx: StageContext) -> MatchingArtifact:
    pack = _inputs.factory_pack(ctx)
    queries, weights = _inputs.build_queries(ctx, pack)
    shortlist = network.rank_for_product(queries, weights, limit=SHORTLIST_SIZE)
    if len(shortlist) < 3:
        raise ValueError(f"only {len(shortlist)} factories match — need ≥3")
    procs = ", ".join(f"{process_label(q.process)} ×{w:g}" for q, w in zip(queries, weights))
    return MatchingArtifact(
        project_id=ctx.project.id,
        generated_by="code",
        factory_pack_id=pack.id,
        queries=queries,
        shortlist=shortlist,
        assumptions=[
            Assumption(
                id="a7_network",
                text="Factories, capacity, load and past performance come from the simulated production network.",
                label="fictional",
                source="factory_mcp (demo data)",
                stage=7,
            ),
            Assumption(
                id="a7_weights",
                text="Score = 35% process fit + 15% MOQ + 15% certifications + 15% load + 20% lead time; "
                f"product-level criteria are part-weighted means over the queries ({procs}).",
                label="estimate",
                stage=7,
            ),
        ],
    )


@stage_handler(7)
def run(ctx: StageContext) -> MatchingArtifact:
    return match(ctx)
