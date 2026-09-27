"""Showcase gallery (W21): recorded live projects, served offline at $0.

    GET /examples  → ExampleSummary[] (id, name, category, build strategy, hero image, one-line result, versions)

A showcase = api/fixtures/showcase_<slug>/ (project.json with id demo_<slug> and tag "Example", 01-13 stage
artifacts, factory_pack.json, versions.json = Studio versions + snapshots + current, example.json = gallery card) and
its files in api/cad/prebuilt/showcase_<slug>/ (GLB/STEP/renders, AI CAD programs model_v<k>.py, firmware.zip,
engineering.json). POST /demo/reset seeds the stage artifacts like any example (runner.seed_example), then
`seed_extras` restores the Studio versions and copies the engineering cache + firmware into the project's files folder,
so GET /projects/demo_<slug>/engineering is served from the recorded state (same inputs digest, no LLM call).
Files: /files/demo_<slug>/<name> resolves to api/cad/prebuilt/showcase_<slug>/<name> (`alias_dir`).
The recording script is api/fixtures/_showcase.py.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter

from api.cad.build import PREBUILT_DIR, files_root

log = logging.getLogger("showcase")

PREFIX = "showcase_"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
CACHE_FILES = ("engineering.json", "firmware.json", "firmware.zip")


def is_showcase(example: str | None) -> bool:
    return bool(example) and example.startswith(PREFIX)


def slug_of(example: str) -> str:
    return example[len(PREFIX):]


def alias_dir(project_id: str) -> Path | None:
    """demo_<slug> → api/cad/prebuilt/showcase_<slug>/ (where a showcase's recorded files live)."""
    if not project_id.startswith("demo_"):
        return None
    d = PREBUILT_DIR / f"{PREFIX}{project_id[5:]}"
    return d if d.is_dir() else None


def seed_extras(example: str, project_id: str) -> None:
    """Studio versions (+ snapshots, current version) and the engineering / firmware cache of a showcase."""
    from api.studio import store
    from contracts.artifacts import ARTIFACT_MODELS, Version

    src = FIXTURES_DIR / example / "versions.json"
    if src.exists():
        raw = json.loads(src.read_text())
        for row in raw.get("versions", []):
            v = Version.model_validate(row["version"])
            snap = {int(k): ARTIFACT_MODELS[int(k)].model_validate(a) for k, a in (row.get("snapshot") or {}).items()}
            store.save_version(project_id, v, snap or None)
        if raw.get("current"):
            store.set_current(project_id, int(raw["current"]))
    pre = PREBUILT_DIR / example
    out = files_root() / project_id
    for name in CACHE_FILES:
        if (pre / name).exists():
            out.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pre / name, out / name)


def after_seed(projects) -> None:
    for p in projects:
        if is_showcase(p.example):
            try:
                seed_extras(p.example, p.id)
            except Exception as e:  # noqa: BLE001 — the stage artifacts are seeded either way
                log.warning("showcase extras for %s failed: %s", p.id, e)


def examples() -> list:
    from api.stages import runner
    from contracts.artifacts import ExampleSummary

    ids = {p.id for p in runner.list_projects()}
    out = []
    for d in sorted(FIXTURES_DIR.glob(f"{PREFIX}*/example.json")):
        try:
            card = ExampleSummary.model_validate_json(d.read_text())
        except Exception as e:  # noqa: BLE001
            log.warning("bad showcase card %s: %s", d, e)
            continue
        card.seeded = card.id in ids
        out.append(card)
    order = {"whoop_kitesurf": 0}
    out.sort(key=lambda c: (order.get(c.slug, 1), -c.stages_done, c.name))
    return out


def register(router: APIRouter) -> None:
    from contracts.artifacts import ExampleSummary

    @router.get("/examples", response_model=list[ExampleSummary], tags=["examples"])
    def list_examples() -> list[ExampleSummary]:
        return examples()


__all__ = ["examples", "seed_extras", "after_seed", "alias_dir", "is_showcase", "PREFIX"]
