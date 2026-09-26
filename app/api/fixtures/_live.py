"""Shared by build_desk_lamp.py / build_tracker_card.py: compute the cost-side fixture numbers with the LIVE code.

HTS (CBP ruling precedent + cached USITC schedule), Drewry-derived sea freight, air by chargeable weight, duties,
broker/3PL, platform fee and QC all come from api.costs.landed — so a cached example shows exactly what the live
stages would compute from the same inputs. Stages 11 and 12 are produced by their live handlers (offline, no LLM).
"""

from __future__ import annotations

from typing import Any

from api.costs import engine, landed
from api.costs.financing import run_financing
from api.stages.registry import StageContext
from contracts import artifacts as A


def _ctx(project: dict, stages: dict[int, dict], n: int) -> StageContext:
    arts = {k: A.ARTIFACT_MODELS[k].model_validate(v) for k, v in stages.items()}
    return StageContext(project=A.Project.model_validate(project), stage=n, inputs={}, artifacts=arts)


class LiveCosts:
    """Landed-cost helpers bound to one example (its spec drives weight, packed volume and lane)."""

    def __init__(self, example: str, project: dict, brief: dict, spec: dict):
        self.ctx = _ctx(project, {1: brief, 3: spec}, 5)
        self.hts, self.precedent = landed.resolve_hts(None, example, project["prompt"])
        self.fo = engine.freight_opts(self.ctx)

    def mode(self, qty: int) -> str:
        return landed.choose_mode(qty, **self.fo)

    def rows(self, fob: float, qty: int, tooling: float, fob_label: str = "estimate", fob_note: str = "Unit cost at tier") -> list[tuple[str, float, str, str]]:
        comps, _ = landed.landed_cost(fob, qty, self.mode(qty), self.hts, False, fob_label=fob_label, fob_note=fob_note,
                                      tooling_total=tooling, **self.fo)
        return [(c.name, c.amount.value, str(getattr(c.amount.label, "value", c.amount.label)), c.amount.source_or_assumption) for c in comps]

    def cash(self, fob: float, qty: int) -> dict[str, float]:
        comps, _ = landed.landed_cost(fob, qty, self.mode(qty), self.hts, False, include_tooling=False, **self.fo)
        return landed.cash_components(comps, qty)

    def hts_dict(self) -> dict[str, Any]:
        return self.hts.model_dump(mode="json")


def live_stage(n: int, project: dict, stages: dict[int, dict]) -> dict:
    """Run the live handler of stage 11 or 12 on the fixture artifacts and return its JSON (status validated)."""
    fn = {11: landed.run_logistics, 12: run_financing}[n]
    art = fn(_ctx(project, stages, n))
    out = art.model_dump(mode="json")
    out.update(status="validated", fallback=False, generated_by="fixture (live code)")
    return out
