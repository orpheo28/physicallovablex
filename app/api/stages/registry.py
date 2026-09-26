"""Plug-in registry. Owner: W0. Wave 1 sessions register here; nobody edits api/main.py.

Stage handler (one per stage, in its owner's folder):

    from api.stages.registry import stage_handler, StageContext
    from contracts.artifacts import CostsArtifact

    @stage_handler(5)
    def run_costs(ctx: StageContext) -> CostsArtifact:
        spec = ctx.artifact(3)          # previous artifacts, already validated models (or None)
        ...
        return CostsArtifact(project_id=ctx.project.id, generated_by="code", ...)

Providers (optional overrides of W0 defaults):

    @provider("factory_pack")   # fn(ctx: StageContext) -> FactoryPack
    @provider("export_pdf")     # fn(ctx: StageContext) -> bytes (Launch Dossier PDF)
    @provider("network")        # zero-arg fn returning an object with list_factories(), get_factory(id), list_rfqs(factory_id)

Routers: a package may also define `register(router: APIRouter)` in its __init__.py or any module; api/main.py
calls it at startup (extra routes, e.g. file downloads under /files/...).

Any exception raised by a handler or provider → fixture fallback (see api/stages/runner.py).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from contracts.artifacts import ArtifactBase, Project

log = logging.getLogger("registry")


@dataclass
class StageContext:
    project: Project
    stage: int
    inputs: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[int, ArtifactBase] = field(default_factory=dict)  # validated artifacts of other stages
    factory_pack: Any | None = None  # contracts.FactoryPack when assembled

    def artifact(self, n: int) -> Any | None:
        return self.artifacts.get(n)


StageHandler = Callable[[StageContext], ArtifactBase]

STAGE_HANDLERS: dict[int, StageHandler] = {}
PROVIDERS: dict[str, Callable[..., Any]] = {}


def stage_handler(n: int) -> Callable[[StageHandler], StageHandler]:
    if not 1 <= n <= 13:
        raise ValueError(f"stage must be 1-13, got {n}")

    def deco(fn: StageHandler) -> StageHandler:
        if n in STAGE_HANDLERS and STAGE_HANDLERS[n] is not fn:
            log.warning("stage %d handler %s overrides %s", n, fn.__module__, STAGE_HANDLERS[n].__module__)
        STAGE_HANDLERS[n] = fn
        return fn

    return deco


def provider(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        PROVIDERS[name] = fn
        return fn

    return deco
