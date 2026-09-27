"""Studio persistence (W17): versions + the project's current version, in their own SQLite tables.

    studio_version(project_id, n, data = contracts.Version JSON, snapshot = {"<stage>": artifact JSON} for stages 1-7)
    studio_state(project_id, current)   # current = the version the stage artifacts reflect (0 = Studio not started)

The tables live on api.db's engine and SQLModel metadata, so POST /demo/reset (drop_all/create_all) wipes them too.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from api import db
from api.stages import runner
from contracts.artifacts import ARTIFACT_MODELS, StageStatus, Version

STUDIO_STAGES = range(1, 8)  # what a version pins; 8-13 and the Factory Pack are downstream ("Make it")


class StudioVersionRow(SQLModel, table=True):
    __tablename__ = "studio_version"
    project_id: str = Field(primary_key=True)
    n: int = Field(primary_key=True)
    data: str
    snapshot: str = ""


class StudioStateRow(SQLModel, table=True):
    __tablename__ = "studio_state"
    project_id: str = Field(primary_key=True)
    current: int = 0


def init() -> None:
    SQLModel.metadata.create_all(db.engine, tables=[StudioVersionRow.__table__, StudioStateRow.__table__])


init()


# --------------------------------------------------------------------------- state


def current(project_id: str) -> int:
    with db.session() as s:
        row = s.get(StudioStateRow, project_id)
        return row.current if row else 0


def set_current(project_id: str, n: int) -> None:
    with db.session() as s:
        row = s.get(StudioStateRow, project_id) or StudioStateRow(project_id=project_id)
        row.current = n
        s.add(row)
        s.commit()


# --------------------------------------------------------------------------- versions


def _load(row: StudioVersionRow, cur: int) -> Version:
    v = Version.model_validate_json(row.data)
    v.is_current = v.n == cur
    return v


def list_versions(project_id: str) -> list[Version]:
    cur = current(project_id)
    with db.session() as s:
        rows = s.exec(db.select(StudioVersionRow).where(StudioVersionRow.project_id == project_id)
                      .order_by(StudioVersionRow.n)).all()
        return [_load(r, cur) for r in rows]


def get_version(project_id: str, n: int) -> Version | None:
    cur = current(project_id)
    with db.session() as s:
        row = s.get(StudioVersionRow, (project_id, n))
        return _load(row, cur) if row else None


def next_n(project_id: str) -> int:
    with db.session() as s:
        rows = s.exec(db.select(StudioVersionRow.n).where(StudioVersionRow.project_id == project_id)).all()
        return max(rows, default=0) + 1


def save_version(project_id: str, v: Version, snapshot: dict[int, object] | None = None) -> Version:
    """Upsert; `snapshot` (stage → artifact model) replaces the stored one when given."""
    v = v.model_copy()
    v.is_current = False  # computed on read
    with db.session() as s:
        row = s.get(StudioVersionRow, (project_id, v.n)) or StudioVersionRow(project_id=project_id, n=v.n, data="")
        row.data = v.model_dump_json()
        if snapshot is not None:
            row.snapshot = json.dumps({str(k): a.model_dump(mode="json") for k, a in snapshot.items()})
        s.add(row)
        s.commit()
    return v


def load_snapshot(project_id: str, n: int) -> dict[int, object]:
    with db.session() as s:
        row = s.get(StudioVersionRow, (project_id, n))
        raw = json.loads(row.snapshot) if row and row.snapshot else {}
    return {int(k): ARTIFACT_MODELS[int(k)].model_validate(v) for k, v in raw.items()}


def patch_snapshot(project_id: str, n: int, artifacts: dict[int, object]) -> None:
    snap = load_snapshot(project_id, n)
    snap.update(artifacts)
    with db.session() as s:
        row = s.get(StudioVersionRow, (project_id, n))
        if row is None:
            return
        row.snapshot = json.dumps({str(k): a.model_dump(mode="json") for k, a in snap.items()})
        s.add(row)
        s.commit()


# --------------------------------------------------------------------------- live artifacts


def live_artifacts(project_id: str) -> dict[int, object]:
    return {n: a for n in STUDIO_STAGES if (a := runner.get_artifact(project_id, n)) is not None}


def write_artifacts(project_id: str, artifacts: dict[int, object], drop: set[int] | None = None) -> None:
    """Make `artifacts` the project's stage artifacts (draft). Stages in `drop` (and every downstream stage 8-13 +
    the Factory Pack) are deleted: they described another version of the product and are rebuilt by "Make it"."""
    for n, a in sorted(artifacts.items()):
        a.generated_at = a.generated_at or datetime.now(timezone.utc)
        runner.save_artifact(project_id, n, a, StageStatus.draft)
    gone = set(range(8, 14)) | {runner.FACTORY_PACK_STAGE} | (drop or set())
    gone -= set(artifacts)
    with db.session() as s:
        rows = s.exec(db.select(db.ArtifactRow).where(db.ArtifactRow.project_id == project_id)).all()
        hit = [r for r in rows if r.stage in gone]
        for r in hit:
            s.delete(r)
        s.commit()
    if hit:
        project = runner.get_project(project_id)
        for r in hit:
            project.stage_status.pop(str(r.stage), None)
        runner.save_project(project)


__all__ = ["current", "set_current", "list_versions", "get_version", "next_n", "save_version", "load_snapshot",
           "patch_snapshot", "live_artifacts", "write_artifacts", "STUDIO_STAGES"]
