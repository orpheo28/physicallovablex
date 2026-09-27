"""Engineering layer (W20): packs, physics formulas with known answers, PVGIS cache, firmware zip (template + mocked
LLM), the engineering endpoint on both demo projects, site-install mode, Factory Pack section and PDF chapter."""

from __future__ import annotations

import io
import json
import math
import zipfile

import pytest
from fastapi.testclient import TestClient

import api.llm as llm
from api.engineering import category as cat
from api.engineering import firmware, physics, service, site_install, solar
from api.main import app
from contracts.artifacts import EngineeringArtifact, FactoryPack, ProcessType
from factory_mcp import network
from tests.engineering_cases import CASES, ctx_for

client = TestClient(app)
KNOWN_CHECKS = {"tip_over", "tip_push", "mass", "battery_life", "ip_rating", "thermal", "airflow", "board_volume", "irrigation_flow", "solar",
                "drone", "hair_dryer"}  # the last two: W21


@pytest.fixture(scope="module", autouse=True)
def seeded():
    assert client.post("/demo/reset").status_code == 200
    yield


# --------------------------------------------------------------------------- packs


@pytest.mark.parametrize("key", cat.pack_keys())
def test_every_pack_loads(key):
    p = cat.load_pack(key)
    assert p["key"] == key and p["title"] and p["standards"] and p["risks"] and p["tests"]
    assert set(p["checks"]) <= KNOWN_CHECKS, set(p["checks"]) - KNOWN_CHECKS
    assert p["prototype"]["method"] and p["prototype"]["steps"]
    for s in cat.standards_for(p):
        # Sourced only with a URL checked to load (date in the note); otherwise an Estimate "to be confirmed"
        assert (s.citation_label == "sourced") == bool(s.url)
        assert ("page checked 20" in s.citation_note) if s.url else ("to be confirmed" in s.citation_note)
    assert cat.risks_for(p) and cat.tests_for(p)


def test_packs_cover_the_use_cases():
    assert {"wearable", "furniture_baby", "home_robot", "vacuum", "irrigation", "solar_roof", "surfboard", "lighting", "tracker", "generic"} <= set(cat.pack_keys())


@pytest.mark.parametrize("name,expected", [
    ("kitesurf_wearable", "wearable"), ("baby_changing_table", "furniture_baby"), ("home_robot", "home_robot"),
    ("stick_vacuum", "vacuum"), ("smart_irrigation", "irrigation"), ("rooftop_solar", "solar_roof"), ("surfboard", "surfboard"),
])
def test_category_detection(name, expected):
    assert cat.detect_category(CASES[name]["prompt"]) == expected


def test_category_detection_fallbacks():
    assert cat.detect_category("Magnetic rechargeable desk lamp") == "lighting"
    assert cat.detect_category("Bluetooth tracker card for wallets") == "tracker"
    assert cat.detect_category("A pod on a strap", family="wearable_band") == "wearable"
    assert cat.detect_category("Something new", brief_category="ble_accessory") == "tracker"
    assert cat.detect_category("An espresso gadget") == "generic"
    assert cat.detect_category("Solar-powered irrigation valve for the garden") == "irrigation"


# --------------------------------------------------------------------------- physics: known answers


def test_tip_angle_of_a_known_box():
    assert physics.tip_angle_deg(0.3, 0.3) == pytest.approx(45.0)
    assert physics.tip_angle_deg(0.1, 0.1 * math.sqrt(3)) == pytest.approx(30.0)


def test_tip_push_force():
    assert physics.tip_push_force_n(10, 0.25, 1.0) == pytest.approx(10 * 9.81 * 0.25)


def test_board_litres_and_buoyancy():
    assert physics.litres(30000) == 30.0
    assert physics.buoyancy_kg(30.0) == pytest.approx(30.75)
    # planing onset at Fn∇ = 2: v = 2 √(g (m/ρ)^(1/3))
    assert physics.planing_speed_ms(1025.0, 2.0) == pytest.approx(2 * math.sqrt(9.81))


def test_battery_life_and_thermal():
    assert physics.battery_life_h(1000, 10) == pytest.approx(85.0)
    assert physics.temperature_rise_k(1.0, 0.01) == pytest.approx(10.0)


def test_vacuum_operating_point_is_self_consistent():
    op = physics.vacuum_operating_point(200, 0.3, 36, 4.0)
    assert op["air_watts"] == pytest.approx(60)
    assert op["pressure_pa"] * op["flow_ls"] / 1000 == pytest.approx(60)
    assert op["pressure_pa"] == pytest.approx(4.0 * 0.5 * 1.2 * op["velocity_ms"] ** 2)


def test_hazen_williams_known_value():
    # 1.5 L/min in 13.6 mm PE over 30 m: tiny loss; 20 L/min: several tenths of a bar
    assert physics.hazen_williams_loss_bar(1.5, 13.6, 30) < 0.02
    assert 0.5 < physics.hazen_williams_loss_bar(20, 13.6, 30) < 1.5
    # scaling law: loss ∝ Q^1.852
    assert physics.hazen_williams_loss_bar(20, 13.6, 30) / physics.hazen_williams_loss_bar(10, 13.6, 30) == pytest.approx(2 ** 1.852)


def test_tip_over_check_on_a_known_box():
    g = physics.Geometry(length=_mm(600), width=_mm(600), height=_mm(600), mass=_g(20000))
    ch = physics.check_tip_over(g, {"com_ratio": 0.5, "tip_min_deg": 15, "tip_warn_deg": 10})
    assert ch.value.value == pytest.approx(45.0) and ch.verdict == "pass" and ch.value.unit == "deg"


def _mm(v):
    return physics.lv(v, "mm", "measured", "bbox")


def _g(v):
    return physics.lv(v, "g", "estimate", "weight")


# --------------------------------------------------------------------------- PVGIS


@pytest.mark.parametrize("site", ["paris", "biarritz", "tarifa"])
def test_pvgis_cache_parsed(site):
    d = solar.load_pvgis(site)
    assert d["outputs"]["totals"]["fixed"]["E_y"] > 900
    assert len(d["outputs"]["monthly"]["fixed"]) == 12
    assert d["_cache"]["fetched_on"].startswith("20") and "re.jrc.ec.europa.eu" in d["_cache"]["url"]


def test_pvgis_sites_rank_by_sunshine():
    ey = {s: solar.load_pvgis(s)["outputs"]["totals"]["fixed"]["E_y"] for s in ("paris", "biarritz", "tarifa")}
    assert ey["tarifa"] > ey["biarritz"] > ey["paris"]


def test_solar_design_from_prompt():
    s = solar.solar_design("Rooftop solar array for a house in Biarritz, 35 m2 south-facing roof")
    assert s.location.startswith("Biarritz") and not s.location_assumed
    assert s.module_count.value == int(35 * solar.USABLE_SHARE // solar.MODULE_AREA_M2)
    assert s.peak_power.value == pytest.approx(s.module_count.value * 0.43, abs=0.01)
    assert s.specific_yield.label == "sourced" and "PVGIS (EU JRC), fetched" in s.specific_yield.source_or_assumption
    assert s.annual_energy.value == pytest.approx(s.peak_power.value * s.specific_yield.value, rel=0.01)
    assert len(s.monthly_energy) == 12 and s.payback.label == "estimate"
    assert solar.solar_design("solar kit for my roof").location_assumed


# --------------------------------------------------------------------------- firmware


def _spec(family: str, conn: str) -> firmware.FirmwareSpec:
    return firmware.FirmwareSpec(product="Test Product", framework=firmware.framework_for(family), mcu_family=family, mcu_part=f"{family} part",
                                 connectivity=conn, sensors=[("imu", "6-axis IMU", "i2c"), ("ppg", "PPG sensor", "i2c")], actuators=[("led", "LED", "gpio")])


@pytest.mark.parametrize("family,conn,expect", [("nrf52", "BLE GATT service", "src/ble_service.c"),
                                                ("esp32", "Wi-Fi + MQTT", "src/connectivity.cpp"),
                                                ("avr", "none", "src/main.cpp")])
def test_firmware_template_zip_is_valid(tmp_path, family, conn, expect):
    files = firmware.template_files(_spec(family, conn))
    dest = tmp_path / "firmware.zip"
    names = firmware.write_zip(files, dest)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        assert f"firmware/{expect}" in z.namelist() and "firmware/README.md" in z.namelist()
        assert "Generated code — not compiled or tested" in z.read("firmware/README.md").decode()
    assert expect in names
    if family == "esp32":
        assert "PubSubClient" in files["src/connectivity.cpp"]


def test_firmware_llm_mocked(monkeypatch):
    calls = []

    def fake(route, prompt, schema, **kw):
        calls.append(route)
        return schema.model_validate({"files": [{"path": "src/main.c", "content": "int main(void){return 0;}"},
                                                {"path": "prj.conf", "content": "CONFIG_BT=y"},
                                                {"path": "../evil.sh", "content": "rm -rf /"}]})

    monkeypatch.setattr(llm, "complete_json", fake)
    monkeypatch.setattr(llm, "is_configured", lambda route="main": True)
    monkeypatch.setattr(llm, "model_for", lambda route: "test/fast-model")
    fw = service.ensure_firmware("p_fw_mock", _spec("nrf52", "BLE GATT service"), use_llm=True, background=False)
    assert calls == ["fast"]
    assert fw.generated_by == "llm:test/fast-model" and not fw.pending_llm
    assert set(fw.files) == {"README.md", "src/main.c", "prj.conf"}  # unsafe path dropped, README added
    with zipfile.ZipFile(service.files_dir("p_fw_mock") / "firmware.zip") as z:
        assert "Generated code — not compiled or tested" in z.read("firmware/README.md").decode()


def test_firmware_llm_failure_keeps_template(monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("fast", "402 credits")

    monkeypatch.setattr(llm, "complete_json", boom)
    monkeypatch.setattr(llm, "is_configured", lambda route="main": True)
    fw = service.ensure_firmware("p_fw_fail", _spec("esp32", "Wi-Fi + MQTT"), use_llm=True, background=False)
    assert fw.generated_by == "template" and "src/connectivity.cpp" in fw.files


# --------------------------------------------------------------------------- endpoint on the demo projects


@pytest.mark.parametrize("pid,category,family", [("demo_tracker_card", "tracker", "nrf52"), ("demo_desk_lamp", "lighting", "avr")])
def test_engineering_endpoint_demo_projects(pid, category, family):
    r = client.get(f"/projects/{pid}/engineering")
    assert r.status_code == 200, r.text
    a = EngineeringArtifact.model_validate(r.json())
    assert a.category == category and a.partner_word == "factories" and not a.fallback
    assert a.standards and a.risks and a.tests and a.checks
    for c in a.checks:
        assert c.value.label in ("measured", "sourced", "estimate") and c.formula and c.verdict in ("pass", "warn", "fail", "info")
    e = a.electronics
    assert e is not None and e.mcu_family == family and e.power_tree and e.connections and e.power_budget
    assert e.battery_life is not None and e.pcb_note.startswith("PCB layout: next step")
    assert a.prototype.total_cost.value > 0 and 3 <= a.prototype.timeline_weeks.value <= 4
    assert a.prototype.enclosure_volume.label == "measured"
    assert any(d.lcsc_pn and d.unit_price.label == "sourced" for d in a.prototype.devkit_bom)
    z = client.get(a.firmware.url)
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    assert zipfile.ZipFile(io.BytesIO(z.content)).testzip() is None
    # CAD files keep being served by W2's route
    assert client.get(f"/files/{pid}/enclosure.step").status_code == 200


def test_engineering_endpoint_404():
    assert client.get("/projects/nope/engineering").status_code == 404
    assert client.get("/files/nope/firmware.zip").status_code == 404


def test_recompute_follows_the_project_state():
    ctx = ctx_for("kitesurf_wearable", "p_eng_recompute")
    a1 = service.engineering_for_ctx(ctx)
    assert service.engineering_for_ctx(ctx).inputs_digest == a1.inputs_digest  # cached
    ctx.artifacts[3].overall_dimensions.height.value = 20
    a2 = service.engineering_for_ctx(ctx)
    assert a2.inputs_digest != a1.inputs_digest


# --------------------------------------------------------------------------- use cases


def _check(a: EngineeringArtifact, cid: str):
    return next(c for c in a.checks if c.id == cid)


def test_use_case_outputs():
    out = {name: service.compute(ctx_for(name), llm_firmware=False) for name in CASES}
    w = out["kitesurf_wearable"]
    assert w.category == "wearable" and w.firmware.framework == "zephyr" and "BLE" in w.firmware.connectivity
    assert _check(w, "ip_rating").value.value == 68 and _check(w, "ip_rating").notes
    assert {"ppg", "imu", "env"} <= {line.block for line in w.electronics.power_budget}
    t = out["baby_changing_table"]
    assert t.electronics is None and t.firmware is None
    b = 275 / 1000
    assert _check(t, "tip_over").value.value == pytest.approx(math.degrees(math.atan(b / (0.95 * 0.55))), abs=0.1)
    assert _check(t, "tip_push").value.value == pytest.approx(24 * 9.81 * b / 0.95, abs=0.1)
    r = out["home_robot"]
    assert r.electronics.mcu_family == "esp32" and r.firmware.framework == "arduino" and "MQTT" in r.firmware.connectivity
    v = out["stick_vacuum"]
    assert _check(v, "air_watts").value.value == pytest.approx(60) and _check(v, "airflow").value.unit == "L/s"
    i = out["smart_irrigation"]
    assert _check(i, "pressure_at_emitter").verdict == "pass" and "6 zones" in _check(i, "flow_per_zone").name
    s = out["rooftop_solar"]
    assert s.site_install and s.partner_word == "installers" and s.solar is not None and s.electronics is None
    assert len(s.installers) == 3 and all(x.name.endswith("(fictional)") and x.label == "fictional" for x in s.installers)
    assert s.prototype.total_cost.unit == "USD"  # W21c: one currency per project (the costing stages are USD)
    sb = out["surfboard"]
    vol = _check(sb, "board_volume")
    assert vol.value.value == pytest.approx(30.0) and vol.value.label == "measured"
    assert "78 kg" in _check(sb, "buoyancy").formula or any(x.value == 78 for x in _check(sb, "buoyancy").inputs)


# --------------------------------------------------------------------------- site install (stage 7)


def test_installers_in_network_and_stage7_queries():
    installers = [f for f in network.list_factories() if f.id.startswith("i_")]
    assert len(installers) == 3 and all(f.name.endswith("(fictional)") and f.label == "fictional" for f in installers)
    ctx = ctx_for("rooftop_solar")
    qs = site_install.installer_queries(ctx)
    assert qs and qs[0].process == ProcessType.other
    shortlist = network.rank_for_product(qs, limit=5)
    assert {m.factory_id for m in shortlist} == {f.id for f in installers}
    assert site_install.installer_queries(ctx_for("stick_vacuum")) is None
    # a manufactured product never gets an installer in its factory shortlist
    from api.agents.negotiation import _inputs

    pack = FactoryPack.model_validate(json.loads(open("api/fixtures/desk_lamp/factory_pack.json").read()))
    lamp_q, _ = _inputs.build_queries(ctx_for("stick_vacuum"), pack)
    assert not any(m.factory_id.startswith("i_") for m in network.rank_for_product(lamp_q, limit=8))


# --------------------------------------------------------------------------- Factory Pack + PDF


def test_factory_pack_has_engineering_section():
    fp = client.get("/projects/demo_tracker_card/factory-pack?rebuild=true").json()
    assert fp["engineering"] is not None and fp["engineering"]["category"] == "tracker"
    assert FactoryPack.model_validate(fp).engineering.prototype.total_cost.value > 0


def test_pdf_builds_with_engineering_chapter():
    r = client.get("/projects/demo_desk_lamp/export")
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and len(r.content) > 50_000
    from api.export import pdf
    from api.stages import runner

    ctx = runner.build_context("demo_desk_lamp", 0)
    fp = runner.get_factory_pack("demo_desk_lamp")
    flow = pdf.engineering_section(ctx, fp)
    assert len(flow) > 10


def test_board_litres_measured_on_w19_board_step():
    """Litres of a real surfboard hull: W19's board family → STEP → re-measured solid volume (Measured)."""
    from api.cad import families
    from contracts.artifacts import CadFile

    pid = "p_eng_board_step"
    out = families.export_family("board", service.files_dir(pid), "enclosure", families.params_for("board", "surf"))
    expected_l = out["measured"]["volume_mm3"] / 1e6
    ctx = ctx_for("surfboard", pid)
    spec = ctx.artifacts[3]
    spec.weight.source_or_assumption = "Sum of part weight estimates"  # no measured figure in stage 3 → read the STEP
    spec.cad_files = [CadFile(format="step", url=f"/files/{pid}/enclosure.step")]
    a = service.compute(ctx, llm_firmware=False)
    vol = _check(a, "board_volume").value
    assert vol.label == "measured" and vol.unit == "L"
    assert vol.value == pytest.approx(expected_l, rel=0.01) and 30 < vol.value < 45
