"""Test setup for api/agents (W4). Offline by default: no key, no DB, no network."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from contracts.artifacts import ARTIFACT_MODELS, BOMItem, BriefArtifact, Project, SpecArtifact

from api.stages.registry import StageContext

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "desk_lamp"
REAL_KEY = os.getenv("OPENROUTER_API_KEY", "")  # captured before any test clears it (never printed)


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls the real LLM routes (needs OPENROUTER_API_KEY)")


@pytest.fixture(autouse=True)
def offline(request, monkeypatch):
    """Clear the LLM key for W4 tests so nothing hits the network (W5's negotiation tests are left alone)."""
    if "negotiation" in Path(str(request.node.fspath)).parts or "live" in request.keywords:
        return
    monkeypatch.setenv("OPENROUTER_API_KEY", "")


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def artifact(n: int, name: str):
    return ARTIFACT_MODELS[n].model_validate(load(name))


@pytest.fixture
def project() -> Project:
    return Project.model_validate(load("project.json"))


@pytest.fixture
def lamp():
    """Desk-lamp artifacts by stage number (from api/fixtures/desk_lamp)."""
    files = {1: "01_brief.json", 3: "03_cad_spec.json", 4: "04_dfm.json", 5: "05_costs.json", 6: "06_production_plan.json", 8: "08_negotiation.json"}
    return {n: artifact(n, f) for n, f in files.items()}


@pytest.fixture
def make_ctx(project, lamp):
    def _make(stage: int, keep=(1, 3, 4, 5, 6, 8), inputs=None, **overrides) -> StageContext:
        arts = {n: a for n, a in lamp.items() if n in keep}
        arts.update(overrides)
        return StageContext(project=project, stage=stage, inputs=inputs or {}, artifacts=arts)

    return _make


@pytest.fixture
def tracker():
    """A BLE tracker card with a rechargeable LiPo cell: (brief, spec)."""
    spec = SpecArtifact.model_validate(
        {**load("03_cad_spec.json"), "product_name": "Tracker Card", "parts": load("03_cad_spec.json")["parts"][:2],
         "bom": [BOMItem(id="e1", part="nRF52832 BLE module", category="electronic", qty=1).model_dump(mode="json"),
                 BOMItem(id="e2", part="LiPo cell 3.7V 80mAh", category="electronic", qty=1).model_dump(mode="json")]}
    )  # fmt: skip
    brief = BriefArtifact.model_validate(
        {**load("01_brief.json"), "product_name": "Tracker Card", "category": "ble_accessory", "has_battery": True,
         "wireless": ["BLE"], "target_markets": ["US", "EU"], "one_liner": "A wallet-thin Bluetooth tracker card.",
         "prompt": "Bluetooth tracker card for wallets"}
    )  # fmt: skip
    return brief, spec
