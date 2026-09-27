"""Studio pins the product (W17): once a project has a current Studio version, stages 1-3 are that version.

"Make it" (POST /projects/{id}/autorun?through=13) re-runs stages 2-7 with default inputs. Without this, stage 2 would
propose fresh directions and stage 3 a fresh LLM BOM, silently discarding every refinement. So the handlers of stages
1, 2 and 3 are wrapped: for a Studio project, a default run returns the stored (current-version) artifact unchanged.
Explicit inputs still run the original handler (stage 1 with answers, stage 3 with another direction_id).
Stage 4 is wrapped to add the wearable certification rows (skin contact, optical sensing, wellness claims).
Stages 4-7 otherwise re-run normally on the pinned product (measured DFM, costs, plan, shortlist).
"""

from __future__ import annotations

import logging

# the original handlers must be registered before they are wrapped (discovery order is alphabetical anyway)
import api.agents.brief  # noqa: F401
import api.cad.directions  # noqa: F401
import api.cad.spec  # noqa: F401
import api.dfm.stage  # noqa: F401
from api.cad.build import normalize
from api.stages.registry import STAGE_HANDLERS, StageContext
from api.studio import product as P
from api.studio import store

log = logging.getLogger("studio.pin")

ORIGINAL = {n: STAGE_HANDLERS.get(n) for n in (1, 2, 3, 4)}


def _studio(ctx: StageContext) -> bool:
    try:
        return store.current(ctx.project.id) > 0
    except Exception:  # noqa: BLE001
        return False


def _pinned(n: int):
    orig = ORIGINAL[n]

    def handler(ctx: StageContext):
        art = ctx.artifact(n)
        if art is not None and not art.fallback and _studio(ctx):
            inputs = ctx.inputs or {}
            explicit = (n == 1 and inputs.get("answers")) or (n == 3 and inputs.get("direction_id") not in (None, art.direction_id))
            if not explicit:
                log.info("stage %d for %s pinned to the current Studio version", n, ctx.project.id)
                return art.model_copy(deep=True)
        return orig(ctx)

    handler.__name__ = f"studio_pinned_{n}"
    handler.__wrapped__ = orig  # type: ignore[attr-defined]
    return handler


def _stage4(ctx: StageContext):
    art = ORIGINAL[4](ctx)
    if _studio(ctx):
        design = ctx.artifact(2)
        d = P.chosen(design)
        family = P.family_of(normalize(d.cad_parameters)) if d and d.cad_parameters else None
        art.certifications = P.merge_certs(list(art.certifications), P.studio_certs(ctx.artifact(1), ctx.artifact(3), family))
    return art


_stage4.__wrapped__ = ORIGINAL[4]  # type: ignore[attr-defined]

for _n in (1, 2, 3):
    if ORIGINAL[_n] is not None and not hasattr(ORIGINAL[_n], "__wrapped__"):
        STAGE_HANDLERS[_n] = _pinned(_n)
if ORIGINAL[4] is not None and not hasattr(ORIGINAL[4], "__wrapped__"):
    STAGE_HANDLERS[4] = _stage4
