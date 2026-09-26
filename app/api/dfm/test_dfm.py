"""W2 acceptance — measured DFM + stage 4. Offline, no LLM key."""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp())
os.environ.setdefault("DB_PATH", str(_TMP / "test.db"))
os.environ["OPENROUTER_API_KEY"] = ""
os.environ.setdefault("FILES_DIR", str(_TMP / "files"))

from build123d import Box, Pos, Rectangle, export_step, extrude  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.dfm.measure import facts, measure  # noqa: E402
from api.main import app  # noqa: E402
from api.stages import runner  # noqa: E402
from contracts.artifacts import DFMArtifact  # noqa: E402

client = TestClient(app)


def _step(shape, tmp_path, name):
    p = tmp_path / f"{name}.step"
    export_step(shape, str(p))
    return p


def _by_cat(issues):
    return {i.category: i for i in issues}


def test_draft_flags_zero_draft_box(tmp_path):
    issues = _by_cat(measure(_step(Box(50, 40, 30), tmp_path, "box")))
    d = issues["draft"]
    assert d.severity == "major" and d.method == "measured"
    assert d.measurement.label == "measured" and d.measurement.value < 0.1
    assert d.rule_citation and d.fix


def test_draft_passes_drafted_box(tmp_path):
    drafted = extrude(Rectangle(50, 40), amount=30, taper=2)
    f = facts(drafted)
    assert abs(f["draft"]["min_wall_draft"]["draft_deg"] - 2.0) < 0.05
    issues = _by_cat(measure(_step(drafted, tmp_path, "drafted"), finish="Polished SPI-B2"))
    assert "draft" not in issues  # 2° ≥ 1° for a polished finish
    tex = _by_cat(measure(_step(drafted, tmp_path, "drafted2"), finish="MT-11010 texture"))
    assert tex["draft"].severity == "minor"  # textured needs ~3°


def test_undercut_flags_side_overhang(tmp_path):
    c = Box(60, 40, 5).moved(Pos(0, 0, 2.5)) + Box(10, 40, 30).moved(Pos(-25, 0, 15)) + Box(60, 40, 5).moved(Pos(0, 0, 27.5))
    issues = _by_cat(measure(_step(c, tmp_path, "c")))
    assert "undercut" in issues and issues["undercut"].measurement.value > 1000
    plain = _by_cat(measure(_step(extrude(Rectangle(50, 40), amount=30, taper=2), tmp_path, "p")))
    assert "undercut" not in plain


def test_projection_and_wall(tmp_path):
    issues = _by_cat(measure(_step(Box(50, 40, 30), tmp_path, "b2")))
    assert abs(issues["projection"].measurement.value - 2000) < 40
    assert "Estimate" in issues["projection"].description
    assert issues["wall_thickness"].measurement.label == "measured"


def test_stage_4_live_without_key():
    pid = client.post("/projects", json={"mode": "idea", "prompt": "Magnetic rechargeable desk lamp, minimalist, sold €89"}).json()["id"]
    for n in (1, 2, 3):
        runner.run_stage(pid, n)
    dfm = runner.run_stage(pid, 4)
    assert dfm.fallback is False, dfm.fallback_reason
    DFMArtifact.model_validate(dfm.model_dump())
    assert len(dfm.issues) >= 3
    measured = [i for i in dfm.issues if i.method == "measured"]
    assert measured and all(i.measurement and i.measurement.label == "measured" for i in measured)
    assert all(i.fix and i.rule_citation for i in dfm.issues)
    assert len({i.id for i in dfm.issues}) == len(dfm.issues)


def test_stage_4_on_seeded_demo_uses_prebuilt_step():
    client.post("/demo/reset")
    dfm = runner.run_stage("demo_desk_lamp", 4)
    assert dfm.fallback is False, dfm.fallback_reason
    assert len(dfm.issues) >= 3
