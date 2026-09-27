"""W21: product families wired into stages 2-4 and the Studio, AI CAD (text-to-CAD) in the Studio, engineering recompute,
build strategy, new categories (drone, hair dryer, camera, smartphone), guards, factory category scoring, LCSC relevance,
showcase gallery. LLM always mocked (the codegen LLM returns the seed program it is given, edited on request)."""

import re
import sys
import time

import pytest
from fastapi.testclient import TestClient

import api.cad.codegen.engine as cg
import api.cad.renders as renders
import api.llm as llm
from api import auth
from api.agents.brief import BriefDraft
from api.main import app
from api.studio.patch import RefinePatch, RegenerateGeometry, SetColor, SetDimensions

client = TestClient(app)
ENV = {"OPENROUTER_API_KEY": "sk-test-not-real", "LLM_MAIN_MODEL": "m/main", "LLM_FAST_MODEL": "m/fast",
       "LLM_CN_MODEL": "m/cn", "LLM_IMAGE_MODEL": "", "API_SHARED_KEY": "", "RATE_LIMIT_PER_DAY": "0",
       "STUDIO_RATE_LIMIT_PER_DAY": "0", "DEMO_READONLY": "", "CODEGEN_ENABLED": "1"}
BOARD = {"mode": "idea", "prompt": "A hydrodynamic surfboard for beginners, 7'6\""}
DRONE = {"mode": "idea", "prompt": "A foldable drone for kitesurf follow-me shots"}
BRIEFS = {
    "surfboard": BriefDraft(product_name="Glide 7'6", one_liner="Hydrodynamic beginner surfboard, 7'6\"", category="mechanical",
                            target_markets=["EU", "US"], target_price_value=450, price_from_prompt=False,
                            key_features=["Stable beginner outline", "Soft rails"], has_battery=False, wireless=[]),
    "drone": BriefDraft(product_name="KiteCam", one_liner="Foldable follow-me drone for kitesurf shots", category="other",
                        target_markets=["EU", "US"], target_price_value=499, price_from_prompt=False,
                        key_features=["Follow-me", "Gimbal camera"], has_battery=True, wireless=["Wi-Fi"]),
}
PATCHES = {
    "wider nose": RefinePatch(summary="Wider nose", ops=[RegenerateGeometry(op="regenerate_geometry", instruction="wider nose")]),
    "make it coral": RefinePatch(summary="Coral", ops=[SetColor(op="set_color", hex="#E07A5F", name="Coral")]),
    "10% longer": RefinePatch(summary="Longer", ops=[SetDimensions(op="set_dimensions", length=2515)]),
}
CODE_RX = re.compile(r"```python\n(.*?)```", re.S)


def fake_codegen(prompt: str, system: str) -> str:
    """Returns the program found in the prompt (the seed / current code); an edit request gets a marked edit."""
    code = max(CODE_RX.findall(prompt), key=len)
    if "Change requested by the user" in prompt:
        code = code.replace("def build():", "# edited: wider nose\ndef build():", 1)
        code = re.sub(r"('nose_width': )([\d.]+)", lambda m: f"{m.group(1)}{float(m.group(2)) * 1.15:.1f}", code)
    return f"```python\n{code}```\n- ok"


def _mock(monkeypatch, brief_key: str):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    calls = {"codegen": 0}

    def fake(route, prompt, schema, **_k):
        if schema is BriefDraft:
            return BRIEFS[brief_key].model_copy(deep=True)
        if schema is RefinePatch:
            for key, p in PATCHES.items():
                if key in prompt:
                    return p.model_copy(deep=True)
        raise llm.LLMError(route, "mocked provider failure")

    def fake_text(*_a, **_k):
        raise llm.LLMError("cn", "mocked provider failure")

    def codegen(prompt, system):
        calls["codegen"] += 1
        return fake_codegen(prompt, system)

    monkeypatch.setattr(llm, "complete_json", fake)
    monkeypatch.setattr(llm, "complete_text", fake_text)
    monkeypatch.setattr(cg, "_default_llm", codegen)
    for name, mod in list(sys.modules.items()):
        if name.startswith("api.") and mod is not llm and getattr(mod, "complete_json", None) is not None:
            monkeypatch.setattr(mod, "complete_json", fake)
    return calls


def _wait(pid, n, *, settle=False, timeout=180):
    t0 = time.time()
    v = None
    while time.time() - t0 < timeout:
        v = next((x for x in client.get(f"/projects/{pid}/versions").json() if x["n"] == n), None)
        busy = v and (v["render_pending"] or v["background_pending"] or v["cad_pending"])
        if v and v["status"] != "running" and (not settle or not busy):
            return v
        time.sleep(0.25)
    raise AssertionError(f"version {n} not settled after {timeout} s: {v}")


def _stage(pid, n):
    return client.get(f"/projects/{pid}/stages/{n}").json()["artifact"]


# --------------------------------------------------------------------------- stages 2-4 in family mode (no key)


def test_board_family_is_a_solid_product():
    pid = client.post("/projects", json=BOARD).json()["id"]
    client.post(f"/projects/{pid}/stages/1/run")
    t0 = time.time()
    design = client.post(f"/projects/{pid}/stages/2/run").json()["artifact"]
    assert time.time() - t0 < 15
    assert [d["cad_parameters"]["product_family"] for d in design["directions"]] == [10.0] * 3  # board
    d1 = design["directions"][0]
    assert d1["dimensions"]["length"]["value"] == pytest.approx(2286, abs=1) and d1["dimensions"]["length"]["label"] == "measured"
    assert "rocker" in d1["shape"].lower() and client.get(d1["glb_url"]).status_code == 200
    spec = client.post(f"/projects/{pid}/stages/3/run").json()["artifact"]
    assert spec["overall_dimensions"]["length"]["value"] == pytest.approx(2286, abs=1)
    assert spec["weight"]["unit"] == "g" and 2000 < spec["weight"]["value"] < 8000
    assert not any("shell" in p["name"].lower() for p in spec["parts"]) and not any(b["category"] == "electronic" for b in spec["bom"])
    dfm = client.post(f"/projects/{pid}/stages/4/run").json()["artifact"]
    measured = [i for i in dfm["issues"] if i["method"] == "measured"]
    assert measured and not any(i["category"] in ("draft", "undercut", "projection") for i in measured)
    section = next(i for i in measured if i["id"].startswith("m") and "thickness" in i["description"])
    assert 60 <= section["measurement"]["value"] <= 90  # the hull section, not the rocker-inflated bbox
    eng = client.get(f"/projects/{pid}/engineering").json()
    assert eng["category"] == "surfboard" and eng["build_strategy"]["strategy"] == "full_design"
    vol = next(c for c in eng["checks"] if c["id"] == "board_volume")
    assert vol["value"]["label"] == "measured" and 45 < vol["value"]["value"] < 90  # solid CAD volume, litres


def test_drone_family_shell_housing_and_checks():
    pid = client.post("/projects", json=DRONE).json()["id"]
    for n in (1, 2, 3, 4):
        client.post(f"/projects/{pid}/stages/{n}/run")
    spec = _stage(pid, 3)
    assert [p["name"] for p in spec["parts"]][:2] == ["Bottom shell", "Top shell"]
    assert any(f["description"] == "Full product — all parts, STEP AP214" for f in spec["cad_files"])
    dfm = _stage(pid, 4)
    wall = next(i for i in dfm["issues"] if i["category"] == "wall_thickness" and i["method"] == "measured")
    assert wall["measurement"]["value"] < 4  # measured on the housing shells, not on the solid product model
    eng = client.get(f"/projects/{pid}/engineering").json()
    ids = {c["id"]: c for c in eng["checks"]}
    assert eng["category"] == "drone" and {"thrust_to_weight", "hover_time", "drone_class"} <= set(ids)
    assert "2019/945" in ids["drone_class"]["threshold"]
    assert eng["build_strategy"]["strategy"] == "module_assembly"
    eu = next(s for s in eng["standards"] if s["code"] == "Regulation (EU) 2019/945")
    assert eu["citation_label"] == "sourced" and eu["url"].startswith("https://eur-lex.europa.eu/")


def test_desk_lamp_stays_w2():
    from api.cad import family_mode

    class B:
        product_name, one_liner = "Desk lamp", "A desk lamp with wireless charging"

    assert family_mode.detect(B(), "desk lamp") is None
    assert family_mode.detect(B(), "bike light that pairs with your phone") is None


# --------------------------------------------------------------------------- Studio + AI CAD


def test_studio_family_ai_cad_and_refines(monkeypatch):
    calls = _mock(monkeypatch, "surfboard")
    pid = client.post("/projects", json=BOARD).json()["id"]
    t0 = time.time()
    assert client.post(f"/projects/{pid}/studio/start").status_code == 202
    v1 = _wait(pid, 1)
    t_v1 = time.time() - t0
    assert v1["status"] == "done" and t_v1 < 35, (t_v1, v1)
    assert v1["preview"]["shape_family"] == "board"
    v1 = _wait(pid, 1, settle=True)
    pv = v1["preview"]
    assert calls["codegen"] >= 1 and v1["cad_pending"] is False
    assert v1["cad_attempts"] == 1 and v1["cad_repairs"] == 0  # the mocked LLM's first program runs
    assert pv["glb_url"].startswith(f"/files/{pid}/model_v") and client.get(pv["glb_url"]).status_code == 200
    assert pv["cad_label"].startswith("AI-generated CAD (concept level) — geometry measured")
    code = client.get(pv["code_url"])
    assert code.status_code == 200 and "def build" in code.text
    spec = _stage(pid, 3)
    assert spec["cad_files"][0]["description"].startswith("AI-generated CAD (concept level) — geometry measured")
    assert any("enclosure" in f["url"] for f in spec["cad_files"])  # the DFM files stay
    # engineering recomputed after the start (background)
    eng = client.get(f"/projects/{pid}/engineering").json()
    assert eng["category"] == "surfboard" and eng["build_strategy"]["title"] == "Full design"

    # geometric refine → the AI program is edited (refine_cad), new program version
    t0 = time.time()
    assert client.post(f"/projects/{pid}/refine", json={"message": "wider nose"}).json() == {"version": 2}
    v2 = _wait(pid, 2, settle=True)
    print(f"\nstudio start v1 {t_v1:.1f} s, geometry refine {time.time() - t0:.1f} s (mocked LLM)")
    ch = next(c for c in v2["changes"] if c["label"] == "AI CAD program")
    assert "wider nose" in ch["after"] and v2["preview"]["code_url"] != pv["code_url"]
    assert "# edited: wider nose" in client.get(v2["preview"]["code_url"]).text

    # non-geometric refine stays fast: recoloured AI model, same program
    t0 = time.time()
    client.post(f"/projects/{pid}/refine", json={"message": "make it coral"})
    v3 = _wait(pid, 3)
    assert time.time() - t0 < 20
    assert v3["preview"]["code_url"] == v2["preview"]["code_url"]
    assert v3["preview"]["glb_url"] == f"/files/{pid}/v3_ai.glb" and client.get(v3["preview"]["glb_url"]).status_code == 200
    assert v3["preview"]["color_hex"] == "#E07A5F"
    _wait(pid, 3, settle=True)

    # restore v1 → its AI model and program
    r = client.post(f"/projects/{pid}/versions/1/restore")
    assert r.status_code == 200 and r.json()["preview"]["code_url"] == pv["code_url"]
    assert _stage(pid, 3)["cad_files"][0]["url"] == pv["glb_url"]


def test_codegen_disabled_uses_the_family_program(monkeypatch):
    calls = _mock(monkeypatch, "drone")
    monkeypatch.setenv("CODEGEN_ENABLED", "0")
    pid = client.post("/projects", json=DRONE).json()["id"]
    client.post(f"/projects/{pid}/studio/start")
    v1 = _wait(pid, 1, settle=True)
    pv = v1["preview"]
    assert calls["codegen"] == 0 and v1["cad_pending"] is False
    assert pv["glb_url"] == f"/files/{pid}/v1.glb" and pv["cad_label"].startswith("Parametric family CAD")
    assert pv["cad_source"] == "seed:drone" and "def build" in client.get(pv["code_url"]).text
    # a form change without AI CAD is noted, never faked
    monkeypatch.setitem(PATCHES, "foldable arms", RefinePatch(summary="Foldable arms", ops=[
        RegenerateGeometry(op="regenerate_geometry", instruction="foldable arms")]))
    client.post(f"/projects/{pid}/refine", json={"message": "foldable arms"})
    v2 = _wait(pid, 2)
    assert any("not modelled" in (c["after"] or "") for c in v2["changes"])


def test_family_dimension_edit_scales_the_product(monkeypatch):
    _mock(monkeypatch, "surfboard")
    monkeypatch.setenv("CODEGEN_ENABLED", "0")
    pid = client.post("/projects", json=BOARD).json()["id"]
    client.post(f"/projects/{pid}/studio/start")
    _wait(pid, 1, settle=True)
    client.post(f"/projects/{pid}/refine", json={"message": "10% longer"})
    v2 = _wait(pid, 2)
    assert v2["status"] == "done", v2
    assert v2["preview"]["dimensions"]["length"]["value"] == pytest.approx(2515, abs=2)
    assert _stage(pid, 2)["directions"][0]["cad_parameters"]["fp_scale_x"] == pytest.approx(2515 / 2286, abs=0.002)


# --------------------------------------------------------------------------- guards


@pytest.fixture
def _guards(monkeypatch):
    for k in ("API_SHARED_KEY", "DEMO_READONLY", "RATE_LIMIT_PER_DAY", "STUDIO_RATE_LIMIT_PER_DAY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    auth.reset_rate_limits()
    yield
    auth.reset_rate_limits()


def test_studio_routes_are_guarded(monkeypatch, _guards):
    pid = client.post("/projects", json={"mode": "idea", "prompt": "desk lamp"}).json()["id"]
    monkeypatch.setenv("DEMO_READONLY", "1")
    for path in (f"/projects/{pid}/studio/start", f"/projects/{pid}/refine", f"/projects/{pid}/versions/1/restore",
                 f"/projects/{pid}/engineering/recompute"):
        r = client.post(path, json={"message": "x"})
        assert r.status_code == 403 and "Read-only" in r.json()["detail"], path
    monkeypatch.delenv("DEMO_READONLY")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("STUDIO_RATE_LIMIT_PER_DAY", "2")
    h = {"X-Forwarded-For": "9.9.9.9"}
    assert client.post(f"/projects/{pid}/refine", json={"message": "x"}, headers=h).status_code == 409  # counted
    assert client.post(f"/projects/{pid}/engineering/recompute", headers=h).status_code == 200
    r = client.post(f"/projects/{pid}/refine", json={"message": "x"}, headers=h)
    assert r.status_code == 429 and "Studio limit" in r.json()["detail"]
    assert client.post("/projects", json={"mode": "idea", "prompt": "lamp"}, headers=h).status_code == 201  # own bucket
    monkeypatch.setenv("API_SHARED_KEY", "s3cret")
    assert client.get(f"/projects/{pid}/cad/code/1").status_code == 401
    assert client.get(f"/projects/{pid}/cad/code/1", headers={"X-App-Key": "s3cret"}).status_code == 404


# --------------------------------------------------------------------------- quality fixes


def test_lcsc_relevance():
    from api.costs.lcsc import best_match, match_bom
    from contracts.artifacts import BOMItem

    assert best_match("PPG sensor", None, 2000, part="PPG sensor").mfr.startswith("MAX30102")
    for line in ("Gas sensor", "Image sensor module", "Soil moisture sensor", "Pressure sensor for altitude"):
        p = best_match(line, None, 2000, part=line)
        assert p is None or "float" not in p.subcategory.lower(), (line, p)
    [it] = match_bom([BOMItem(id="e1", part="Camera module 5MP", category="electronic", qty=1)])
    assert it.lcsc_pn is None and it.unit_cost_est.label == "estimate"


def test_factory_category_scoring():
    from contracts.artifacts import ProcessType, SearchCapacityQuery
    from factory_mcp import network

    q = lambda proc, cat: SearchCapacityQuery(process=proc, material="PC/ABS", quantity=2000,  # noqa: E731
                                              certifications_required=["ISO 9001"], category=cat)
    wear = network.rank_for_product([q(ProcessType.injection_molding, "wearable"), q(ProcessType.pcba, "wearable"),
                                     q(ProcessType.assembly, "wearable")], limit=5)
    top3 = [m.factory_name for m in wear[:3]]
    assert not any("Lighting" in n or "Lantern" in n for n in top3), top3
    assert any("Wearables" in n or "Micro-Electronics" in n for n in top3), top3
    silver = network.get_factory("f_silverfern")
    pf = network.score_factory(silver, q(ProcessType.pcba, "wearable"))[0]
    assert pf.score == 0.5 and "specialises in lighting" in pf.note
    lamp = network.rank_for_product([q(ProcessType.injection_molding, "lighting"), q(ProcessType.pcba, "lighting")], limit=5)
    assert any("Lighting" in m.factory_name for m in lamp[:3])
    drone = network.rank_for_product([q(ProcessType.cnc, "drone"), q(ProcessType.assembly, "drone")], limit=3)
    assert drone[0].factory_name.startswith("Skyforge")
    assert all(f.name.endswith("(fictional)") for f in network.list_factories())


# --------------------------------------------------------------------------- new categories


def test_new_categories_and_strategies():
    from api.cad.codegen import classify, seed_for
    from api.engineering.category import detect_category
    from api.engineering.strategy import build_strategy

    cases = {"A foldable drone for kitesurf follow-me shots": ("drone", "module_assembly"),
             "A quiet, compact hair dryer": ("hair_dryer", "module_assembly"),
             "A retro instant camera": ("camera", "odm_customization"),
             "A minimalist smartphone without social apps": ("smartphone", "odm_customization"),
             "A next-gen home robot that tidies toys": ("home_robot", "odm_customization"),
             "A simple, safe changing table for babies": ("furniture_baby", "full_design"),
             "Smart irrigation for a 30 m² garden in Biarritz": ("irrigation", "module_assembly")}
    for text, (cat, strat) in cases.items():
        assert detect_category(text.lower()) == cat, text
        bs = build_strategy(cat)
        assert bs.strategy == strat and bs.moq.label == "estimate" and bs.entry_cost.value >= 0 and bs.lead_time.unit == "weeks"
    odm = build_strategy("smartphone")
    assert "reference platform" in odm.path[0] and "carried over" in odm.path[3] and "Not designed from scratch" in odm.explanation
    assert seed_for(classify("A retro instant camera"), "A retro instant camera") == ("camera", "instant")
    assert classify("A bike light that pairs with your phone") == "lighting"


def test_drone_and_dryer_physics():
    from api.engineering import physics as ph

    # momentum theory: 1 kg on 4 × 10" props, FoM 1 → n T^1.5 / √(2ρA)
    t, a = 9.81 / 4, 3.14159265 * 0.254 ** 2 / 4
    assert ph.hover_power_w(1.0, 0.254, 4, fom=1.0) == pytest.approx(4 * t ** 1.5 / (2 * 1.2 * a) ** 0.5, rel=1e-4)
    assert (ph.drone_class(249), ph.drone_class(250), ph.drone_class(899), ph.drone_class(3999)) == ("C0", "C1", "C1", "C2")
    checks = {c.id: c for c in ph.hair_dryer_checks("", "compact 1200 W dryer", {"heater_w": 1600, "fan_w": 60, "airflow_l_s": 13})}
    dt = 1200 / (1.2 * 0.013 * 1005)
    assert checks["outlet_temperature"].value.value == pytest.approx(20 + dt, abs=1)
    assert checks["dryer_power"].value.value == 1260


# --------------------------------------------------------------------------- showcase gallery


def test_examples_after_reset():
    from api.showcase import FIXTURES_DIR, PREFIX

    assert client.post("/demo/reset").status_code == 200
    ex = client.get("/examples").json()
    n = len(list(FIXTURES_DIR.glob(f"{PREFIX}*/example.json")))
    assert len(ex) == n and all(e["seeded"] for e in ex) and all("Example" in e["tags"] for e in ex)
    for e in ex:
        d = client.get(f"/projects/{e['id']}").json()
        assert d["project"]["tags"] == ["Example"]
        done = [s["stage"] for s in d["stages"] if s["status"] == "validated"]
        assert len(done) == e["stages_done"] and not d["has_fallback"], (e["id"], done)  # never padded with the desk lamp
        assert client.get(f"/projects/{e['id']}/versions").json()[-1]["preview"]["code_url"]
        if e["hero_image_url"]:
            assert client.get(e["hero_image_url"]).status_code == 200, e
        if e["glb_url"]:
            assert client.get(e["glb_url"]).status_code == 200, e
    whoop = next((e for e in ex if e["slug"] == "whoop_kitesurf"), None)
    if whoop is None:
        pytest.skip("showcase fixtures not recorded yet")
    pid = whoop["id"]
    vs = client.get(f"/projects/{pid}/versions").json()
    assert [v["n"] for v in vs] == [1, 2, 3, 4] and vs[-1]["is_current"]
    assert client.get(vs[-1]["preview"]["code_url"]).status_code == 200
    assert [s["status"] for s in client.get(f"/projects/{pid}").json()["stages"]] == ["validated"] * 13
    eng = client.get(f"/projects/{pid}/engineering").json()
    assert eng["category"] == "wearable" and eng["build_strategy"]["strategy"] == "module_assembly"
    assert client.get(f"/projects/{pid}/export").status_code == 200
