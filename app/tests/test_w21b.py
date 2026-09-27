"""W21b: battery upgrades recompute runtime, structured part risk + cheaper alternative, partner kind, project name from
the brief, native /mcp exemption, LSR overmolding seed factory, per-installation basis. LLM always mocked."""

import pytest
from fastapi.testclient import TestClient

from api.agents.brief import BriefDraft
from api.main import app
from api.studio.patch import AddComponent, AddFeature, NoteRequirement, RefinePatch, UpgradeBattery
from tests.test_w21 import BRIEFS, DRONE, PATCHES, _mock, _stage, _wait

client = TestClient(app)


def test_longer_flight_time_is_a_battery_change(monkeypatch):
    _mock(monkeypatch, "drone")
    monkeypatch.setenv("CODEGEN_ENABLED", "0")
    # the model only noted a requirement: the deterministic backstop turns it into a battery upgrade
    monkeypatch.setitem(PATCHES, "longer flight time", RefinePatch(summary="Longer flight time", ops=[
        NoteRequirement(op="note_requirement", text="Longer flight time")]))
    monkeypatch.setitem(PATCHES, "double the battery", RefinePatch(summary="Double", ops=[
        UpgradeBattery(op="upgrade_battery", factor=2)]))
    pid = client.post("/projects", json=DRONE).json()["id"]
    client.post(f"/projects/{pid}/studio/start")
    _wait(pid, 1, settle=True)
    client.post(f"/projects/{pid}/refine", json={"message": "longer flight time"})
    v2 = _wait(pid, 2)
    assert v2["status"] == "done", v2
    bat = next(c for c in v2["changes"] if c["label"] == "Battery capacity")
    assert "mAh" in bat["after"] and "+" in bat["after"] and bat["label_kind"] == "estimate"
    perf = next(c for c in v2["changes"] if c["area"] == "performance")
    assert perf["label"] == "Flight time" and perf["before"] and perf["after"] != perf["before"]
    assert not any(c["area"] == "requirement" for c in v2["changes"])
    line = next(b for b in _stage(pid, 3)["bom"] if "mAh" in b["part"] and "in Studio" in (b["description"] or ""))
    assert line["lcsc_pn"] is None
    _wait(pid, 2, settle=True)
    client.post(f"/projects/{pid}/refine", json={"message": "double the battery"})
    v3 = _wait(pid, 3)
    b3 = next(c for c in v3["changes"] if c["label"] == "Battery capacity")
    assert float(b3["after"].split()[0]) == pytest.approx(2 * float(bat["after"].split()[0]), rel=0.02)


def test_battery_upgrade_unit():
    from api.studio.battery import wants_battery

    assert wants_battery("longer flight time") and wants_battery("more runtime please") and wants_battery("longer battery life")
    assert not wants_battery("a 5-day battery target on the box") and not wants_battery("waterproof to 10 m")


def test_added_part_carries_structured_risk(monkeypatch):
    from tests.test_studio import PROMPT, _mock as mock_whoop, _wait as wait_whoop

    mock_whoop(monkeypatch)
    pid = client.post("/projects", json=PROMPT).json()["id"]
    client.post(f"/projects/{pid}/studio/start")
    wait_whoop(client, pid, 1, settle=True)
    client.post(f"/projects/{pid}/refine", json={"message": "add heart-rate and HRV sensing"})
    v2 = wait_whoop(client, pid, 2)
    ch = next(c for c in v2["changes"] if c["area"] == "component" and "C6454833" in (c["after"] or ""))
    risk = ch["risk"]
    assert risk["level"] in ("medium", "high") and any("expensive" in r for r in risk["reasons"])
    assert any("low stock" in r for r in risk["reasons"])
    # the snapshot has no other heart-rate sensor: no alternative is invented, the reason says so
    assert risk["alternative"] is None and any("no cheaper in-stock part" in r for r in risk["reasons"])
    row = next(r for r in _stage(pid, 4)["component_risks"] if "heart" in r["part"].lower())
    assert "alternative" in row


def test_cheaper_alternative_is_structured():
    from api.costs.lcsc import component_risk, get_part
    from contracts.artifacts import BOMItem

    p = get_part("C6455140")  # A4994 motor driver, ≈ $9.75 at 2k, 6 in stock
    [r] = component_risk([BOMItem(id="e1", part="Stepper motor driver", category="electronic", qty=1, lcsc_pn="C6455140",
                                  manufacturer_pn=p.mfr)])
    alt = r.alternative
    assert alt is not None and alt.lcsc_pn != "C6455140" and alt.label == "sourced"
    assert alt.price.value < p.price(2000) and alt.price.label == "sourced" and alt.stock.value >= 1000


def test_partner_kind_and_lsr_seed():
    from contracts.artifacts import ProcessType, SearchCapacityQuery
    from factory_mcp import network

    fs = {f["id"]: f for f in client.get("/factories").json()}
    assert {fs[i]["kind"] for i in fs if i.startswith("i_")} == {"installer"}
    assert fs["f_skyforge"]["kind"] == "integrator" and fs["f_coralline"]["kind"] == "factory"
    assert not any("Tidewater" in f["name"] for f in fs.values())  # the MCP demo registers Tidewater itself
    q = lambda proc, mat: SearchCapacityQuery(process=proc, material=mat, quantity=2000,  # noqa: E731
                                              certifications_required=["ISO 9001"])
    lsr = network.search_capacity(q(ProcessType.injection_molding, "LSR silicone"))
    assert lsr[0].factory_id == "f_coralline" and "LSR" in lsr[0].score_breakdown[0].note
    pcba = [m.factory_id for m in network.search_capacity(q(ProcessType.pcba, "FR-4"))]
    assert "f_coralline" in pcba  # one factory covers both processes of the buyer demo
    fid = network.register_capacity(name="Test Installer Co", region="Lyon", processes=["other"], materials=["PV modules"], moq=1,
                                    certifications=[], lead_time_days=10, monthly_capacity=20, current_load_pct=10,
                                    archetype="installer (balanced)")
    assert network.get_factory(fid).kind == "installer"


def test_project_name_from_brief(monkeypatch):
    _mock(monkeypatch, "drone")
    pid = client.post("/projects", json=DRONE).json()["id"]
    assert client.get(f"/projects/{pid}").json()["project"]["name"] == DRONE["prompt"][:60]
    client.post(f"/projects/{pid}/stages/1/run")
    assert client.get(f"/projects/{pid}").json()["project"]["name"] == BRIEFS["drone"].product_name
    named = client.post("/projects", json={**DRONE, "name": "My own name"}).json()["id"]
    client.post(f"/projects/{named}/stages/1/run")
    assert client.get(f"/projects/{named}").json()["project"]["name"] == "My own name"


def test_mcp_exemption_is_native(monkeypatch):
    from api import auth

    assert not hasattr(auth.Guards, "_mcp_exempt") and "/mcp" in auth.MCP_PATHS
    monkeypatch.setenv("API_SHARED_KEY", "s3cret")
    monkeypatch.delenv("MCP_TOKEN", raising=False)
    r = client.post("/mcp", json={})
    assert r.status_code == 401 and "MCP_TOKEN" in r.json()["detail"]  # the endpoint's own gate, not Guards'
    assert client.get("/projects").status_code == 401


def test_solar_is_per_installation():
    client.post("/demo/reset")
    solar = next((e for e in client.get("/examples").json() if e["slug"] == "solar_biarritz"), None)
    if solar is None:
        pytest.skip("solar showcase not recorded")
    assert solar["unit_basis"] == "per_installation" and solar["unit_cost"]["unit"] == "USD" and "installed per roof" in solar["one_line_result"]
    eng = client.get(f"/projects/{solar['id']}/engineering").json()
    assert eng["unit_basis"] == "per_installation" and eng["installation_cost"]["unit"] == "USD"
    # W21c: one currency, one installation, a pilot of 10, margin vs the installed price
    c = client.get(f"/projects/{solar['id']}/stages/5").json()["artifact"]
    assert c["unit_basis"] == "per_installation" and c["currency"] == "USD" and [t["quantity"] for t in c["tiers"]] == [10]
    assert c["reference_quantity"] == 10 and c["target_retail_price"]["value"] == solar["unit_cost"]["value"]
    assert 0 < c["tiers"][0]["margin_pct"]["value"] < 60 and c["total_cash_needed"]["value"] < 200_000
    bat = next(ln for ln in c["bom_lines"] if "battery pack" in ln["part"].lower())
    assert bat["unit_price"]["value"] > 1000  # priced per installation, not a $0.30 placeholder
    assert client.get(f"/projects/{solar['id']}/stages/11").json()["artifact"]["incoterm"] == "DDP"
    whoop = next(e for e in client.get("/examples").json() if e["slug"] == "whoop_kitesurf")
    assert whoop["unit_basis"] == "per_unit" and whoop["unit_cost"]["unit"] == "USD"
    assert client.get(f"/projects/{whoop['id']}/engineering").json()["firmware"]["generated_by"].startswith("llm:")  # cache kept


def test_brief_draft_names():
    assert isinstance(BRIEFS["drone"], BriefDraft)
    assert AddComponent and AddFeature  # (imports used by the Studio mocks)


# --------------------------------------------------------------------------- W21c


def test_spo2_reuses_the_ppg_and_adds_skin_temperature(monkeypatch):
    """F1: 'Add SpO2 and skin-temperature sensing' on a band that has a PPG: no second PPG, one temperature sensor,
    a visible certification delta (FDA wellness vs medical-device boundary)."""
    from tests import test_studio as ts

    monkeypatch.setitem(ts.PATCHES, "add SpO2 and skin-temperature sensing", RefinePatch(summary="SpO2 + skin temperature", ops=[
        AddFeature(op="add_feature", name="SpO2 and skin-temperature sensing", description="blood oxygen and skin temperature"),
        AddComponent(op="add_component", part="Optical heart-rate and SpO2 sensor", category="electronic", qty=1, rationale="SpO2"),
        AddComponent(op="add_component", part="Skin temperature sensor", category="electronic", qty=1, rationale="skin temperature")]))
    ts._mock(monkeypatch)
    pid = client.post("/projects", json=ts.PROMPT).json()["id"]
    client.post(f"/projects/{pid}/studio/start")
    ts._wait(client, pid, 1, settle=True)
    client.post(f"/projects/{pid}/refine", json={"message": "add heart-rate and HRV sensing"})
    ts._wait(client, pid, 2, settle=True)
    ppg_before = [b for b in _stage(pid, 3)["bom"] if "C6454833" == b.get("lcsc_pn") or "MAX30102" in (b.get("manufacturer_pn") or "")]
    assert len(ppg_before) == 1
    client.post(f"/projects/{pid}/refine", json={"message": "add SpO2 and skin-temperature sensing"})
    v3 = ts._wait(client, pid, 3)
    bom = _stage(pid, 3)["bom"]
    ppg = [b for b in bom if "MAX30102" in (b.get("manufacturer_pn") or "") or b.get("lcsc_pn") == "C6454833"]
    temp = [b for b in bom if "temperature" in b["part"].lower()]
    assert len(ppg) == 1, [b["part"] for b in bom]
    assert len(temp) == 1 and temp[0]["unit_cost_est"]["label"] in ("sourced", "estimate")
    added = [c for c in v3["changes"] if c["label"] == "Component added"]
    assert len(added) == 1 and "temperature" in added[0]["after"].lower()
    assert any("Uses the existing" in (c["after"] or "") for c in v3["changes"])
    certs = [c for c in v3["changes"] if c["area"] == "certification"]
    assert any("SpO2" in c["after"] for c in certs), v3["changes"]
    assert any("62471" in c for c in v3["preview"]["certifications"])


def test_modules_are_never_catalogue_chips():
    """F2: complex modules and implausible matches → Estimate from the module price model."""
    from api.costs.lcsc import match_bom
    from contracts.artifacts import BOMItem

    lines = ["Smartphone ODM mainboard assembly", "Display and touch assembly", "Flash assembly", "Pistol-grip trigger switch",
             "TRIAC heater power switch", "Grouped passive components", "2D lidar module", "High-speed BLDC vacuum motor assembly",
             "Side-button flex assembly", "Brushless outrunner motor", "4-in-1 brushless ESC"]
    out = match_bom([BOMItem(id=f"e{i}", part=p, category="electronic", qty=1) for i, p in enumerate(lines)])
    assert all(it.lcsc_pn is None and it.unit_cost_est.label == "estimate" for it in out), [(i.part, i.lcsc_pn) for i in out]
    [usb] = match_bom([BOMItem(id="e1", part="USB-C receptacle 16P SMD", category="electronic", qty=1)])
    assert usb.lcsc_pn  # real catalogue parts still match


def test_showcase_economics_are_plausible():
    """F3/F8: module-level prices put the showcases in realistic ranges; no Sourced label on a module."""
    import json
    from pathlib import Path

    fx = Path(__file__).resolve().parents[1] / "api" / "fixtures"
    ranges = {"drone_follow": (120, 250), "minimal_phone": (120, 220), "stick_vacuum": (60, 110), "changing_table": (80, 160)}
    for slug, (lo, hi) in ranges.items():
        c = json.loads((fx / f"showcase_{slug}" / "05_costs.json").read_text())
        t = next(t for t in c["tiers"] if t["quantity"] == c["reference_quantity"])
        assert lo <= t["bom_cost"]["value"] <= hi, (slug, t["bom_cost"]["value"])
        assert t["unit_cost"]["value"] < c["target_retail_price"]["value"], slug
        assert not any("Placeholder USD 0.50" in ln["unit_price"]["source_or_assumption"] for ln in c["bom_lines"]), slug
        for ln in c["bom_lines"]:
            if ln["unit_price"]["label"] == "sourced":
                assert not any(w in ln["part"].lower() for w in ("mainboard", "assembly", "module", "motor", "display", "battery")), (slug, ln["part"])


def test_ppg_without_spo2_is_upgraded_in_place():
    from api.studio.apply import Applied, _covered
    from contracts.artifacts import BOMItem

    bom = [BOMItem(id="e1", part="Optical heart-rate / PPG sensor module", category="electronic", qty=1)]
    out = Applied(arts={})
    assert _covered(bom, "Optical heart-rate and SpO2 sensor", out)
    assert len(bom) == 1 and bom[0].manufacturer_pn == "MAX30102EFD+T" and out.rematch
    assert out.notes[0].label == "Component upgraded"
    assert _covered(bom, "SpO2 sensor", Applied(arts={}))  # now it provides SpO2: nothing to do
    assert not _covered(bom, "Skin temperature sensor", Applied(arts={}))
