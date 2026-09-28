"""C3 — 2D technical drawings from the CAD (GET /projects/{id}/drawings, CAD_DRAWINGS=1). Offline: showcase fixtures +
prebuilt STEP files, no LLM. Sheets for whoop, vacuum, drone, surfboard, changing table; dimensions = measured bbox."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.main import app
from contracts.artifacts import DRAWINGS_NOTE, DrawingSheet

client = TestClient(app)
SHOWCASES = ["demo_whoop_kitesurf", "demo_stick_vacuum", "demo_drone_follow", "demo_surfboard_beginner", "demo_changing_table"]
_cache: dict[str, list[dict]] = {}


@pytest.fixture(scope="module", autouse=True)
def _seed():
    mp = pytest.MonkeyPatch()
    mp.setenv("CAD_DRAWINGS", "1")
    assert client.post("/demo/reset").status_code == 200
    yield
    mp.undo()


def _sheets(pid: str) -> list[dict]:
    if pid not in _cache:
        r = client.get(f"/projects/{pid}/drawings")
        assert r.status_code == 200, r.text
        _cache[pid] = r.json()
    return _cache[pid]


def _fmt(v: float) -> str:
    from api.cad.drawings.compose import fmt

    return fmt(v)


def _svg_text(svg: str) -> str:
    root = ET.fromstring(svg)
    return " ".join(t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text"))


def _pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page\b", pdf))


@pytest.mark.parametrize("pid", SHOWCASES)
def test_sheets_generated(pid):
    sheets = [DrawingSheet.model_validate(s) for s in _sheets(pid)]
    assert sheets[0].sheet == "A1" and sheets[0].kind == "assembly"
    assert any(s.kind == "part" for s in sheets)
    assert len({s.sheet for s in sheets}) == len(sheets)
    for s in sheets:
        assert s.note == DRAWINGS_NOTE and s.label == "measured"
        assert s.svg_url.startswith(f"/files/{pid}/drawings/v{s.version}_") and s.pdf_url.endswith(".pdf")
        assert re.match(r"^(\d+:1|1:\d+)$", s.scale), s.scale
        svg = client.get(s.svg_url)
        assert svg.status_code == 200 and svg.headers["content-type"].startswith("image/svg+xml")
        text = _svg_text(svg.text)  # well-formed XML
        assert "GENERATED FROM CAD — VERIFY BEFORE RELEASE" in text
        assert "ISO 2768-m" in text and f"v{s.version}" in text and "Measured" in text
        pdf = client.get(s.pdf_url)
        assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
        assert pdf.content[:5] == b"%PDF-" and pdf.content.rstrip().endswith(b"%%EOF") and _pages(pdf.content) == 1
    full = client.get(sheets[0].set_pdf_url)
    assert full.status_code == 200 and full.content[:5] == b"%PDF-" and _pages(full.content) == len(sheets)


@pytest.mark.parametrize("pid", SHOWCASES)
def test_dimensions_match_measured_bbox(pid):
    """Assembly overall L × W × H = the STEP bounding box measured independently; each value is printed on the sheet."""
    from build123d import import_step

    from api.cad.drawings import _steps
    from api.studio.parts import version_context

    model, _ = _steps(version_context(pid))
    bb = import_step(str(model)).bounding_box()
    measured = [bb.size.X, bb.size.Y, bb.size.Z]
    sheets = _sheets(pid)
    a1 = sheets[0]
    assert a1["bbox_mm"] == pytest.approx(measured, abs=0.02), (a1["bbox_mm"], measured)
    for s in sheets:
        text = _svg_text(client.get(s["svg_url"]).text)
        for v in s["bbox_mm"]:
            # bbox_mm is rounded to 0.01 before this 0.1 format; the sheet formats the unrounded value (13.849… vs 13.85)
            assert any(re.search(rf"(^|\s){re.escape(_fmt(x))} ±", text) for x in (v, v - 0.006, v + 0.006)), (s["sheet"], v)


def test_assembly_balloons_and_parts_list():
    sheets = _sheets("demo_drone_follow")
    text = _svg_text(client.get(sheets[0]["svg_url"]).text)
    assert "PARTS LIST" in text and "ITEM" in text and "BOM" in text
    parts = {s["part_id"]: s for s in sheets if s["kind"] == "part"}
    assert parts["motor_1"]["qty"] == 4 and parts["motor_1"]["bom_item_id"] == "e1"  # 4 identical motors → one item
    parts_json = client.get("/projects/demo_drone_follow/parts").json()["parts"]
    known = {p["part_id"] for p in parts_json}
    assert set(parts) <= known


def test_moulded_shell_features():
    """Whoop DFM shells: section A-A with the measured wall; the desk lamp base shell (C5 pro): 4 drafted bosses with
    ISO 273 M3 clearance holes through the floor (screws into inserts in the top shell)."""
    sheets = _sheets("demo_whoop_kitesurf")
    m = [s for s in sheets if s["kind"] == "moulded"]
    assert len(m) == 2
    text = _svg_text(client.get(m[0]["svg_url"]).text)
    assert "SECTION A-A" in text and re.search(r"WALL 1\.5 ±0\.1", text)
    r = client.get("/projects/demo_desk_lamp/drawings")
    assert r.status_code == 200
    shell = next(s for s in r.json() if s["kind"] == "part" and s["title"].lower().startswith("lower housing"))
    text = _svg_text(client.get(shell["svg_url"]).text)
    assert "4× BOSS Ø4.98" in text and "4× Ø3.4 +0.1/0" in text and "WALL 2.2 ±0.1" in text


def test_cached_and_versioned():
    first = _sheets("demo_whoop_kitesurf")
    again = client.get("/projects/demo_whoop_kitesurf/drawings").json()
    assert again == first
    v1 = client.get("/projects/demo_whoop_kitesurf/drawings?version=1").json()
    assert all(s["version"] == 1 for s in v1) and v1[0]["svg_url"].endswith("/v1_A1.svg")
    assert client.get("/projects/demo_whoop_kitesurf/drawings?version=99").status_code == 404
    assert client.get("/projects/nope/drawings").status_code == 404


def test_file_route_is_safe():
    for name in ("..%2F..%2Fapp.db", "v4_A1.step", "x.svg", "v4_A1.svg.bak"):
        assert client.get(f"/files/demo_whoop_kitesurf/drawings/{name}").status_code == 404


def test_off_by_default(monkeypatch):
    monkeypatch.setenv("CAD_DRAWINGS", "0")
    assert client.get("/projects/demo_whoop_kitesurf/drawings").status_code == 404
    assert client.get("/files/demo_whoop_kitesurf/drawings/v4_A1.svg").status_code == 404
    from api.cad.drawings import register

    probe = FastAPI()
    router = APIRouter()
    register(router)
    probe.include_router(router)
    assert not any("drawings" in p for p in probe.openapi()["paths"])  # the web hides the tab when the route is absent
    monkeypatch.setenv("CAD_DRAWINGS", "1")
    probe2, router2 = FastAPI(), APIRouter()
    register(router2)
    probe2.include_router(router2)
    assert "/projects/{project_id}/drawings" in probe2.openapi()["paths"]


def test_factory_pack_and_dossier_include_drawings():
    fp = client.get("/projects/demo_whoop_kitesurf/factory-pack?rebuild=true").json()
    assert [d["sheet"] for d in fp["drawings"]][:2] == ["A1", "P01"]
    pdf = client.get("/projects/demo_whoop_kitesurf/export")
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    assert b"/Title (Drawings)" in pdf.content or b"Drawings" in pdf.content  # outline entry of the chapter
    assert _pages(pdf.content) > len(fp["drawings"])


def test_contract_file_paths():
    from api.cad.drawings import out_dir

    d = out_dir("demo_whoop_kitesurf")
    assert (d / "v4_set.pdf").is_file() and (d / "v4.json").is_file()
    assert Path(d).parent.name == "demo_whoop_kitesurf"
