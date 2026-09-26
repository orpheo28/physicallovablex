"""Smoke tests on fixtures with no API key (W6 acceptance): demo reset, both cached examples through
13 stages + factory pack + export, PDF structure, tracker card consistency (same rules as the desk lamp)."""

from __future__ import annotations

import base64
import json
import re
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from contracts.artifacts import ARTIFACT_MODELS, STAGE_NAMES, Factory, FactoryPack, LabeledValue, StageResult

FIXTURES = Path(__file__).resolve().parent.parent / "api" / "fixtures"
EXAMPLES = {"desk_lamp": "Magnetic rechargeable desk lamp, minimalist, sold €89", "tracker_card": "Bluetooth tracker card for wallets"}
DATE = re.compile(r"20\d\d-\d\d-\d\d")

client = TestClient(app)


def load(example: str, n: int) -> dict:
    return json.loads((FIXTURES / example / f"{n:02d}_{STAGE_NAMES[n]}.json").read_text())


def pdf_streams(pdf: bytes) -> list[bytes]:
    """Decoded content streams (ASCII85 and/or Flate) so tests can look for page text."""
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.DOTALL):
        data = m.group(1).strip()
        for decode in (lambda d: d, lambda d: base64.a85decode(d, adobe=data.startswith(b"<~") or data.endswith(b"~>"))):
            try:
                raw = decode(data)
                out.append(zlib.decompress(raw))
                break
            except Exception:  # noqa: BLE001
                continue
    return out


def pdf_text(pdf: bytes) -> bytes:
    return b"\n".join(pdf_streams(pdf)) + pdf


def walk_labeled(obj, path=""):
    """Yield every LabeledValue-shaped dict in a JSON document."""
    if isinstance(obj, dict):
        if {"value", "unit", "label", "source_or_assumption"} <= set(obj):
            yield path, obj
        for k, v in obj.items():
            yield from walk_labeled(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_labeled(v, f"{path}[{i}]")


# ----------------------------------------------------------------------------- demo reset


def test_demo_reset_seeds_both_examples():
    r = client.post("/demo/reset")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["projects"]}
    assert {"demo_desk_lamp", "demo_tracker_card"} <= ids
    for pid in ("demo_desk_lamp", "demo_tracker_card"):
        detail = client.get(f"/projects/{pid}").json()
        assert [s["status"] for s in detail["stages"]] == ["validated"] * 13
        fp = FactoryPack.model_validate(client.get(f"/projects/{pid}/factory-pack").json())
        assert fp.project_id == pid


# ----------------------------------------------------------------------------- both examples end to end


@pytest.mark.parametrize("example", list(EXAMPLES))
def test_example_13_stages_factory_pack_export(example):
    pid = client.post("/projects", json={"mode": "idea", "prompt": EXAMPLES[example]}).json()["id"]
    assert client.get(f"/projects/{pid}").json()["project"]["example"] == example
    for n in range(1, 14):
        r = client.post(f"/projects/{pid}/stages/{n}/run", json={"inputs": {}})
        assert r.status_code == 200, (n, r.text)
        res = StageResult.model_validate(r.json())  # schema-valid artifact
        assert res.stage == n and res.artifact.stage == n
    fp = FactoryPack.model_validate(client.get(f"/projects/{pid}/factory-pack?rebuild=true").json())
    assert fp.project_id == pid and fp.cost_estimate and fp.dfm_alerts and fp.certifications and fp.bom
    assert len(fp.questions) >= 3 and all(q.cn for q in fp.questions)
    assert all("machine-translated" in q.cn_review_note.lower() for q in fp.questions)
    assert fp.product_summary_cn
    pdf = client.get(f"/projects/{pid}/export")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF" and len(pdf.content) > 20_000
    # CN section: CID font embedded as a resource + outline entry for the Chinese Factory Pack
    assert b"STSong-Light" in pdf.content
    assert b"Factory Pack CN" in pdf.content
    assert pdf.content.count(b"/Type /Page\n") + pdf.content.count(b"/Type /Page ") >= 15


@pytest.mark.parametrize("pid", ["demo_desk_lamp", "demo_tracker_card"])
def test_seeded_dossier_has_labels_and_fictional_banners(pid):
    client.post("/demo/reset")
    pdf = client.get(f"/projects/{pid}/export").content
    text = pdf_text(pdf)
    for needle in (b"Sourced", b"Estimate", b"Fictional", b"Label legend", b"Assumption register", b"Factory Pack"):
        assert needle in text, needle


def test_cached_example_note_on_fallback_stages():
    pid = client.post("/projects", json={"mode": "idea", "prompt": "Smart dog bowl that weighs food, Wi-Fi"}).json()["id"]
    client.post(f"/projects/{pid}/autorun?wait=true")
    pdf = client.get(f"/projects/{pid}/export")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    fallbacks = [s for s in client.get(f"/projects/{pid}").json()["stages"] if s["fallback"]]
    if fallbacks:  # offline: at least the LLM stages fall back
        assert b"Cached example" in pdf_text(pdf.content)


# ----------------------------------------------------------------------------- factory pack provider (unit)


def _ctx(example: str, stages: range | list[int], fallback: bool = False):
    from api.stages import runner
    from api.stages.registry import StageContext
    from contracts.artifacts import Project

    project = Project(id="unit1", name=example, mode="idea", prompt=EXAMPLES[example], example=example)
    arts = {}
    for n in stages:
        a = runner.load_fixture(example, n, "unit1")
        a.fallback = fallback
        arts[n] = a
    return StageContext(project=project, stage=0, artifacts=arts)


@pytest.mark.parametrize("example", list(EXAMPLES))
def test_factory_pack_from_live_artifacts_is_not_fallback(example):
    from api.export.factory_pack import build_factory_pack

    fp = build_factory_pack(_ctx(example, range(1, 7)))
    assert fp.fallback is False and fp.id == "fp_unit1_v1"
    assert [t.quantity for t in fp.cost_estimate] == [500, 2000, 10000]
    assert any("machine-translated" in a.text.lower() for a in fp.assumption_register)
    ids = [a.id for a in fp.assumption_register]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("example", list(EXAMPLES))
def test_factory_pack_missing_sections_use_example_and_flag_fallback(example):
    from api.export.factory_pack import build_factory_pack

    empty = build_factory_pack(_ctx(example, []))
    assert empty.fallback is True and empty.bom and empty.dfm_alerts and empty.cost_estimate
    partial = build_factory_pack(_ctx(example, [1, 3]))  # no DFM, no costs
    assert partial.fallback is True and partial.dfm_alerts and partial.certifications and partial.cost_estimate
    assert any("cached example" in a.text.lower() for a in partial.assumption_register)


def test_translate_cn_never_raises_without_key():
    from api.export import translate_cn

    summary, cn, source = translate_cn.translate("Some product summary.", "Widget", ["US"], [500, 2000], [("Can you hold ±0.1 mm?", None), ("Unknown question", "备用译文")])
    assert source == "fallback" and "Widget" in summary
    assert cn == [None, "备用译文"]
    known = translate_cn.known_translations()
    assert any("UN38.3" in en for en in known)  # both examples' questions are pre-translated


# ----------------------------------------------------------------------------- tracker card fixtures


def test_tracker_card_is_complete_and_valid():
    ex = FIXTURES / "tracker_card"
    for n, name in STAGE_NAMES.items():
        obj = ARTIFACT_MODELS[n].model_validate(load("tracker_card", n))
        assert obj.stage == n and obj.project_id == "demo_tracker_card"
    FactoryPack.model_validate(json.loads((ex / "factory_pack.json").read_text()))
    project = json.loads((ex / "project.json").read_text())
    assert project["id"] == "demo_tracker_card" and project["example"] == "tracker_card"


def test_tracker_card_consistency():
    costs, logistics, financing = (load("tracker_card", n) for n in (5, 11, 12))
    breakdown = sum(c["amount"]["value"] for c in costs["cash_breakdown"])
    assert abs(breakdown - costs["total_cash_needed"]["value"]) < 0.05
    # stage 12 follows the approved stage-8 quote: stage 5 stays the budget reference, a difference is explained
    assert abs(financing["stage5_total"]["value"] - costs["total_cash_needed"]["value"]) < 0.05
    assert abs(sum(p["cash_out"]["value"] for p in financing["cash_curve"]) - financing["total_cash"]["value"]) < 0.05
    if financing["matches_stage5_total"]:
        assert abs(financing["total_cash"]["value"] - costs["total_cash_needed"]["value"]) < 0.05
    else:
        assert financing["reconciliation_note"].startswith("Differs from stage 5 by $") and "negotiated quote" in financing["reconciliation_note"]
    assert logistics["reconciles_with_stage5"]
    assert abs(financing["cash_curve"][-1]["cumulative"]["value"] - financing["total_cash"]["value"]) < 0.05
    assert [t["quantity"] for t in costs["tiers"]] == [500, 2000, 10000]
    unit = [t["unit_cost"]["value"] for t in costs["tiers"]]
    assert unit == sorted(unit, reverse=True)  # cost falls with volume
    assert len(load("tracker_card", 4)["issues"]) >= 3
    assert len(load("tracker_card", 7)["shortlist"]) >= 3
    landed_components = sum(c["amount"]["value"] for c in logistics["landed_cost_breakdown"])
    assert abs(landed_components - logistics["landed_cost_per_unit"]["value"]) < 0.05
    tooling_lines = sum(t["cost"]["value"] for t in costs["tooling"])
    assert abs(tooling_lines - costs["tooling_total"]["value"]) < 0.05
    ext = sum(line["extended"]["value"] for line in costs["bom_lines"])
    bom_500 = costs["tiers"][0]["bom_cost"]["value"] + costs["tiers"][0]["packaging_cost"]["value"]
    assert abs(ext - bom_500) < 0.05


def test_tracker_card_stage_links():
    spec, dfm, costs = load("tracker_card", 3), load("tracker_card", 4), load("tracker_card", 5)
    bom_ids = {b["id"] for b in spec["bom"]}
    assert {c["bom_item_id"] for c in costs["bom_lines"]} == bom_ids
    assert {r["bom_item_id"] for r in dfm["component_risks"]} <= bom_ids
    part_ids = {p["id"] for p in spec["parts"]}
    assert {i["part_id"] for i in dfm["issues"] if i["part_id"]} <= part_ids
    assert {s["part_id"] for s in load("tracker_card", 6)["steps"]} <= part_ids
    # measured DFM issues carry a measurement
    assert all(i["measurement"] for i in dfm["issues"] if i["method"] == "measured")
    # every QC defect maps to a spec line (non-empty ref)
    assert all(d["spec_ref"] for d in load("tracker_card", 10)["defects"])
    # FCC 15C, UN38.3 in the certification map
    standards = " ".join(c["standard"] for c in dfm["certifications"])
    assert "15C" in standards and "UN38.3" in standards


def test_tracker_card_milestones_respect_dependencies():
    from datetime import date

    ms = {m["id"]: m for m in load("tracker_card", 9)["milestones"]}
    for m in ms.values():
        assert date.fromisoformat(m["end_date"]) >= date.fromisoformat(m["start_date"])
        for dep in m["depends_on"]:
            assert date.fromisoformat(m["start_date"]) >= date.fromisoformat(ms[dep]["end_date"]), (m["id"], dep)
    pay = load("tracker_card", 9)["payment_schedule"]
    assert {p["milestone_id"] for p in pay} <= set(ms)


@pytest.mark.parametrize("example", list(EXAMPLES))
def test_honest_labels(example):
    """Sourced values carry a date; fictional data is used for factories, quotes, freight; no real factory names."""
    for n in range(1, 14):
        for path, lv in walk_labeled(load(example, n)):
            LabeledValue.model_validate(lv)
            if lv["label"] == "sourced":
                assert lv["source_or_assumption"].strip(), (n, path)
            if lv["label"] == "estimate":
                assert lv["source_or_assumption"].strip(), (n, path)
    for line in load(example, 5)["bom_lines"]:
        if line["unit_price"]["label"] == "sourced":
            assert line["lcsc_pn"] and "LCSC price via jlcsearch" in line["unit_price"]["source_or_assumption"]
            assert DATE.search(line["unit_price"]["source_or_assumption"])
    logistics = load(example, 11)
    # freight: Drewry-derived sea rates / chargeable-weight air rates are Estimates with their formula, else Fictional demo rates
    for o in logistics["freight_options"]:
        c = o["cost_per_unit"]
        assert c["label"] == "fictional" or (c["label"] == "estimate" and ("Drewry" in c["source_or_assumption"] or "/kg" in c["source_or_assumption"]))
    matching = load(example, 7)
    assert all(m["score"]["label"] == "fictional" and m["factory_name"].endswith("(fictional)") for m in matching["shortlist"])
    neg = load(example, 8)
    assert neg["final_terms"]["unit_price"]["label"] == "fictional"
    assert all(x["label"] == "fictional" for x in neg["quotes"] + neg["rfqs"] + neg["transcript"])


def test_tracker_card_factories_exist_in_network():
    network = {f["id"] for f in json.loads((FIXTURES / "network" / "factories.json").read_text())}
    ids = {m["factory_id"] for m in load("tracker_card", 7)["shortlist"]} | {q["factory_id"] for q in load("tracker_card", 8)["quotes"]}
    assert ids <= network, ids - network
    for f in json.loads((FIXTURES / "network" / "factories.json").read_text()):
        assert Factory.model_validate(f).name.endswith("(fictional)")


def test_tracker_card_lcsc_lines_are_real_parts():
    costs = load("tracker_card", 5)
    sourced = [line for line in costs["bom_lines"] if line["unit_price"]["label"] == "sourced"]
    assert len(sourced) >= 6
    assert all(re.fullmatch(r"C\d+", line["lcsc_pn"]) for line in sourced)
    assert all(line["stock"] and line["stock"]["label"] == "sourced" for line in sourced)


def test_export_of_project_with_no_stages_run_shows_cached_examples():
    pid = client.post("/projects", json={"mode": "prototype", "prompt": "E-ink phone, minimalist", "pasted_bom": "SoC,1,8.5"}).json()["id"]
    pdf = client.get(f"/projects/{pid}/export")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and len(pdf.content) > 20_000
    assert b"Cached example" in pdf_text(pdf.content)
