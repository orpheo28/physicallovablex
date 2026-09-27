"""Stage runner. Owner: W0. Contract: contracts/stage_runner.md.

    run_stage(project_id, n, inputs=None) -> StageArtifact

1. Load the project and every stored artifact → StageContext.
2. If a handler is registered for stage n, call it and validate its return value against ARTIFACT_MODELS[n].
3. On ANY exception (LLMError, ValidationError, KeyError, build123d crash...) or when no handler is
   registered → load api/fixtures/<example>/<NN>_<name>.json, set fallback=True (+ fallback_reason).
4. Persist as status 'draft' and return it.
"""

from __future__ import annotations

import json
import logging
import os
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.artifacts import (
    ARTIFACT_MODELS,
    STAGE_NAMES,
    STAGE_TITLES,
    ArtifactBase,
    FactoryPack,
    Project,
    StageResult,
    StageStatus,
    StageSummary,
)

from api import db
from api.stages.registry import PROVIDERS, STAGE_HANDLERS, StageContext

log = logging.getLogger("runner")

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
DEFAULT_EXAMPLE = "desk_lamp"
FACTORY_PACK_STAGE = 0  # storage slot for the Factory Pack
STAGE_TIMEOUT_S = float(os.getenv("STAGE_TIMEOUT_S", "45"))  # hard cap per stage / Factory Pack → fixture "timeout"
# Handlers run on this pool so a stuck call (LLM, CAD) can be abandoned: its late result is simply never saved.
_POOL = ThreadPoolExecutor(max_workers=32, thread_name_prefix="stage")  # nested use (stage → capped LLM call)


class StageTimeout(TimeoutError):
    pass


def call_with_timeout(fn, *args, timeout: float | None = None):
    """Run fn(*args) with a hard timeout (the worker thread is abandoned, not killed)."""
    fut = _POOL.submit(fn, *args)
    try:
        return fut.result(timeout=timeout or STAGE_TIMEOUT_S)
    except FuturesTimeout:
        raise StageTimeout(f"timeout: no answer within {timeout or STAGE_TIMEOUT_S:g} s") from None


class NotFound(Exception):
    pass


# --------------------------------------------------------------------------- fixtures


def fixture_path(example: str, n: int) -> Path:
    if n == FACTORY_PACK_STAGE:
        return FIXTURES_DIR / example / "factory_pack.json"
    return FIXTURES_DIR / example / f"{n:02d}_{STAGE_NAMES[n]}.json"


def available_examples() -> list[str]:
    return sorted(p.name for p in FIXTURES_DIR.iterdir() if (p / "project.json").exists())


def load_fixture(example: str | None, n: int, project_id: str | None = None) -> Any:
    """Load a fixture as a validated model. Falls back to DEFAULT_EXAMPLE if the example lacks that file."""
    ex = example if example and fixture_path(example, n).exists() else DEFAULT_EXAMPLE
    raw = json.loads(fixture_path(ex, n).read_text())
    if project_id:
        raw["project_id"] = project_id
    model = FactoryPack if n == FACTORY_PACK_STAGE else ARTIFACT_MODELS[n]
    return model.model_validate(raw)


# --------------------------------------------------------------------------- persistence


def get_project(project_id: str) -> Project:
    with db.session() as s:
        row = s.get(db.ProjectRow, project_id)
        if not row:
            raise NotFound(f"project {project_id} not found")
        return Project.model_validate_json(row.data)


def list_projects() -> list[Project]:
    with db.session() as s:
        rows = s.exec(db.select(db.ProjectRow).order_by(db.ProjectRow.created_at)).all()
        return [Project.model_validate_json(r.data) for r in rows]


def save_project(project: Project) -> Project:
    with db.session() as s:
        row = s.get(db.ProjectRow, project.id)
        if row:
            row.data = project.model_dump_json()
        else:
            row = db.ProjectRow(id=project.id, data=project.model_dump_json(), created_at=project.created_at)
        s.add(row)
        s.commit()
    return project


def new_project_id() -> str:
    return "p_" + uuid.uuid4().hex[:10]


def _load_artifact(project_id: str, n: int) -> Any | None:
    with db.session() as s:
        row = s.get(db.ArtifactRow, (project_id, n))
        if not row:
            return None
        model = FactoryPack if n == FACTORY_PACK_STAGE else ARTIFACT_MODELS[n]
        return model.model_validate_json(row.data)


def get_artifact(project_id: str, n: int) -> ArtifactBase | None:
    return _load_artifact(project_id, n)


def save_artifact(project_id: str, n: int, artifact: Any, status: StageStatus | str = StageStatus.draft) -> None:
    status = StageStatus(status).value
    if n != FACTORY_PACK_STAGE:
        artifact.status = status
    with db.session() as s:
        row = s.get(db.ArtifactRow, (project_id, n)) or db.ArtifactRow(project_id=project_id, stage=n, data="")
        row.data = artifact.model_dump_json()
        row.status = status
        row.fallback = bool(getattr(artifact, "fallback", False))
        row.updated_at = datetime.now(timezone.utc)
        s.add(row)
        s.commit()
    if n != FACTORY_PACK_STAGE:
        project = get_project(project_id)
        project.stage_status[str(n)] = StageStatus(status)
        save_project(project)


def build_context(project_id: str, n: int, inputs: dict | None = None) -> StageContext:
    project = get_project(project_id)
    artifacts = {k: a for k in range(1, 14) if (a := _load_artifact(project_id, k)) is not None}
    return StageContext(
        project=project,
        stage=n,
        inputs=inputs or {},
        artifacts=artifacts,
        factory_pack=_load_artifact(project_id, FACTORY_PACK_STAGE),
    )


def stage_summaries(project_id: str) -> list[StageSummary]:
    with db.session() as s:
        rows = {r.stage: r for r in s.exec(db.select(db.ArtifactRow).where(db.ArtifactRow.project_id == project_id))}
    out = []
    for n in range(1, 14):
        r = rows.get(n)
        out.append(
            StageSummary(
                stage=n,
                name=STAGE_NAMES[n],
                title=STAGE_TITLES[n],
                status=StageStatus(r.status) if r else StageStatus.not_started,
                fallback=r.fallback if r else False,
                updated_at=r.updated_at if r else None,
            )
        )
    return out


def to_result(project_id: str, n: int, artifact: ArtifactBase) -> StageResult:
    return StageResult(
        project_id=project_id,
        stage=n,
        name=STAGE_NAMES[n],
        title=STAGE_TITLES[n],
        status=StageStatus(artifact.status),
        fallback=artifact.fallback,
        artifact=artifact,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- run


def run_stage(project_id: str, n: int, inputs: dict | None = None) -> ArtifactBase:
    if n not in ARTIFACT_MODELS:
        raise NotFound(f"stage {n} does not exist")
    ctx = build_context(project_id, n, inputs)
    handler = STAGE_HANDLERS.get(n)
    artifact: ArtifactBase
    started = time.monotonic()
    try:
        if handler is None:
            raise LookupError(f"no handler registered for stage {n}")
        result = call_with_timeout(handler, ctx)
        model = ARTIFACT_MODELS[n]
        artifact = model.model_validate(result.model_dump() if hasattr(result, "model_dump") else result)
        artifact.project_id = project_id
    except Exception as e:  # noqa: BLE001 — by contract, every failure falls back
        if handler is not None:
            log.warning("stage %d failed for %s → fixture fallback: %s\n%s", n, project_id, e, traceback.format_exc())
        artifact = load_fixture(ctx.project.example, n, project_id)
        artifact.fallback = True
        artifact.fallback_reason = (str(e) if isinstance(e, StageTimeout) else f"{type(e).__name__}: {e}")[:500]
    log.info("stage %d for %s in %.1fs%s", n, project_id, time.monotonic() - started, " (fallback)" if artifact.fallback else "")
    save_artifact(project_id, n, artifact, StageStatus.draft)
    if n == 1 and not artifact.fallback:
        name_from_brief(project_id, artifact)
    return artifact


def name_from_brief(project_id: str, brief) -> None:
    """W21b: an auto-named project (name = truncated prompt) takes the brief's product name after stage 1."""
    project = get_project(project_id)
    new = (getattr(brief, "product_name", "") or "").strip()[:80]
    auto = not project.name.strip() or project.name.strip() == project.prompt.strip()[:60] or project.name == "Untitled product"
    if new and auto and new != project.name:
        project.name = new
        save_project(project)


def get_factory_pack(project_id: str, rebuild: bool = False) -> FactoryPack:
    """Assemble (provider 'factory_pack') or load the Factory Pack; fixture on any error."""
    if not rebuild and (fp := _load_artifact(project_id, FACTORY_PACK_STAGE)) is not None:
        return fp
    ctx = build_context(project_id, FACTORY_PACK_STAGE)
    try:
        fn = PROVIDERS.get("factory_pack")
        if fn is None:
            raise LookupError("no factory_pack provider registered")
        pack = FactoryPack.model_validate(call_with_timeout(fn, ctx).model_dump())
        pack.project_id = project_id
    except Exception as e:  # noqa: BLE001
        if "factory_pack" in PROVIDERS:
            log.warning("factory pack failed for %s → fixture: %s", project_id, e)
        pack = load_fixture(ctx.project.example, FACTORY_PACK_STAGE, project_id)
        pack.fallback = True
    save_artifact(project_id, FACTORY_PACK_STAGE, pack)
    return pack


# --------------------------------------------------------------------------- demo seed


def seed_example(example: str) -> Project:
    """Create a project entirely from an example's fixtures (all 13 stages + Factory Pack), status validated."""
    raw = json.loads((FIXTURES_DIR / example / "project.json").read_text())
    project = Project.model_validate(raw)
    project.example = example
    project.stage_status = {}
    save_project(project)
    partial = example.startswith("showcase_")  # W21: a start-only showcase has stages 1-7; never fill 8-13 with the desk lamp
    for n in range(1, 14):
        if partial and not fixture_path(example, n).exists():
            continue
        save_artifact(project.id, n, load_fixture(example, n, project.id), StageStatus.validated)
    if not partial or fixture_path(example, FACTORY_PACK_STAGE).exists():
        save_artifact(project.id, FACTORY_PACK_STAGE, load_fixture(example, FACTORY_PACK_STAGE, project.id))
    return get_project(project.id)
