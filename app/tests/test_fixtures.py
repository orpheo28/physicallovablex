"""Every fixture file validates against contracts/artifacts.py (W0 acceptance)."""

import json
from pathlib import Path

import pytest

from contracts.artifacts import ARTIFACT_MODELS, STAGE_NAMES, Factory, FactoryPack, Project, RFQWithQuotes

FIXTURES = Path(__file__).resolve().parent.parent / "api" / "fixtures"
EXAMPLES = sorted(p for p in FIXTURES.iterdir() if (p / "project.json").exists())


def _files():
    for ex in EXAMPLES:
        yield ex.name, "project.json", Project
        yield ex.name, "factory_pack.json", FactoryPack
        for n, name in STAGE_NAMES.items():
            yield ex.name, f"{n:02d}_{name}.json", ARTIFACT_MODELS[n]


def test_desk_lamp_is_complete():
    names = {p.name for p in (FIXTURES / "desk_lamp").glob("*.json")}
    expected = {"project.json", "factory_pack.json"} | {f"{n:02d}_{s}.json" for n, s in STAGE_NAMES.items()}
    assert expected <= names


@pytest.mark.parametrize("example,filename,model", list(_files()))
def test_fixture_validates(example, filename, model):
    path = FIXTURES / example / filename
    if example != "desk_lamp" and not path.exists():
        pytest.skip(f"{example} has no {filename} yet (falls back to desk_lamp)")
    obj = model.model_validate(json.loads(path.read_text()))
    if filename[:2].isdigit():
        assert obj.stage == int(filename[:2])


def test_network_fixtures_validate():
    for f in json.loads((FIXTURES / "network" / "factories.json").read_text()):
        assert Factory.model_validate(f).fictional is True
    for r in json.loads((FIXTURES / "network" / "rfqs.json").read_text()):
        RFQWithQuotes.model_validate(r)


def test_desk_lamp_consistency():
    load = lambda n: json.loads((FIXTURES / "desk_lamp" / f"{n:02d}_{STAGE_NAMES[n]}.json").read_text())
    costs, logistics, financing = load(5), load(11), load(12)
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
    assert [t["quantity"] for t in costs["tiers"]] == [500, 2000, 10000]
    assert len(load(4)["issues"]) >= 3
    assert len(load(7)["shortlist"]) >= 3


@pytest.mark.parametrize("example,code,rate", [("desk_lamp", "8513.10.40", 3.5), ("tracker_card", "8517.62.00", 0.0)])
def test_cached_examples_are_honest(example, code, rate):
    """W7: HTS general rate Sourced from hts.json (301 stays Estimate), real measured DFM, GLBs for d1-d3 exist."""
    d = FIXTURES / example
    load = lambda n: json.loads((d / n).read_text())  # noqa: E731
    hts = load("11_logistics.json")["hts"]
    assert hts["code"].startswith(code) and hts["general_rate"]["value"] == rate and hts["general_rate"]["label"] == "sourced"
    s301 = hts["section_301_rate"]  # Sourced only when a CBP ruling cites a 9903.88.xx heading, else Estimate "confirm with broker"
    assert (s301["label"] == "sourced" and "CBP ruling" in s301["source_or_assumption"]) or (s301["label"] == "estimate" and "broker" in s301["source_or_assumption"])
    measured = [i for i in load("04_dfm.json")["issues"] if i["method"] == "measured"]
    assert measured and all(i["measurement"]["label"] == "measured" for i in measured)
    assert "placeholder" not in json.dumps(load("04_dfm.json")).lower() + json.dumps(load("03_cad_spec.json")).lower()
    pid = load("project.json")["id"]
    prebuilt = FIXTURES.parent / "cad" / "prebuilt" / pid
    design = load("02_design.json")
    assert {"a2_render", "a2_hero"} <= {a["id"] for a in design["assumptions"]}
    for direction in design["directions"]:
        assert direction["glb_url"] == f"/files/{pid}/{direction['id']}.glb"
        assert direction["render_url"] == f"/files/{pid}/{direction['id']}.png" and (prebuilt / f"{direction['id']}.png").exists()
        assert (prebuilt / f"{direction['id']}.glb").exists()
    spec = load("03_cad_spec.json")
    assert spec["direction_id"] == load("02_design.json")["chosen_direction_id"]
    assert all((prebuilt / f["url"].rsplit("/", 1)[1]).exists() and f["size_bytes"] for f in spec["cad_files"])
    assert spec["cad_files"][0]["description"].startswith("Full product") and spec["cad_files"][0]["format"] == "glb"
    assert all(f["description"].startswith("Moulded parts (DFM)") for f in spec["cad_files"][1:])
    logistics = load("11_logistics.json")
    fin = load("12_financing.json")
    assert logistics["reconciles_with_stage5"] and (fin["matches_stage5_total"] or fin["reconciliation_note"])


@pytest.mark.parametrize("example", ["desk_lamp", "tracker_card"])
def test_honesty_audit_fixtures(example):
    """W7e: extended cost = Estimate, LCSC URL on Sourced prices/stock, V-Trust URL, measured overall dims, IEEPA URL."""
    d = FIXTURES / example
    load = lambda n: json.loads((d / n).read_text())  # noqa: E731
    for line in load("05_costs.json")["bom_lines"]:
        assert line["extended"]["label"] != "sourced"
        if line["unit_price"]["label"] == "sourced":
            assert f"https://www.lcsc.com/product-detail/{line['lcsc_pn']}.html" in line["unit_price"]["source_or_assumption"]
            assert "LCSC unit price (Sourced) × estimated quantity" in line["extended"]["source_or_assumption"]
        if line["stock"]:
            assert "lcsc.com/product-detail" in line["stock"]["source_or_assumption"]
    spec = load("03_cad_spec.json")
    assert all(spec["overall_dimensions"][k]["label"] == "measured" for k in ("length", "width", "height"))
    qc = load("10_qc.json")
    assert qc["man_day_rate"]["label"] == "sourced" and "https://www.v-trust.com/en/our-network" in qc["man_day_rate"]["source_or_assumption"]
    assert qc["inspection_cost"]["label"] == "estimate" and "V-Trust rate (Sourced) × estimated man-days" in qc["inspection_cost"]["source_or_assumption"]
    ieepa = next(c for c in load("11_logistics.json")["landed_cost_breakdown"] if c["name"].startswith("IEEPA"))
    assert "content.govdelivery.com/accounts/USDHSCBP/bulletins/40b11c9" in ieepa["amount"]["source_or_assumption"]


def test_network_store_follows_db_path(monkeypatch, tmp_path):
    """W7f: without FACTORY_MCP_DB, each API database gets its own factory store (isolated DBs never share one)."""
    from factory_mcp import network

    monkeypatch.delenv("FACTORY_MCP_DB", raising=False)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "w7.db"))
    assert network.db_path() == tmp_path / "w7_network.db"
    monkeypatch.setenv("DB_PATH", str(tmp_path / "app.db"))
    assert network.db_path() == tmp_path / "factory_network.db"  # default deployment path unchanged
