"""W17: Studio — refine the product by prompting. Mocked LLM (brief + PATCHes), live code paths for everything else.

Whoop scenario: start → v1 wearable_band; "add heart-rate and HRV sensing" → optical HR sensor in the BOM (LCSC-matched),
cost + certifications change; "make it pink" → colour, render re-requested, costs unchanged; "thinner, 8 mm pod" →
CAD rebuilt, measured height 8 mm, DFM re-measured; restore v2; autorun through=13 completes from the refined product.
Plus: polling stays fast during a refine; a forced 402 → failed version, previous version preserved; CAD families.
"""

import io
import sys
import threading
import time

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

import api.cad.renders as renders
import api.llm as llm
from api.agents.brief import BriefDraft
from api.main import app
from api.studio.patch import AddComponent, AddFeature, RefinePatch, SetColor, SetDimensions

client = TestClient(app)
ENV = {"OPENROUTER_API_KEY": "sk-test-not-real", "LLM_MAIN_MODEL": "m/main", "LLM_FAST_MODEL": "m/fast",
       "LLM_CN_MODEL": "m/cn", "LLM_IMAGE_MODEL": "m/image", "API_SHARED_KEY": "", "RATE_LIMIT_PER_DAY": "0",
       "STUDIO_RATE_LIMIT_PER_DAY": "0", "DEMO_READONLY": ""}
PROMPT = {"mode": "idea", "prompt": "Whoop competitor: a screenless fitness band that tracks recovery, strain and sleep"}
BRIEF = BriefDraft(product_name="Pulse Band", one_liner="Screenless fitness band that tracks recovery, strain and sleep",
                   category="wearable", target_markets=["US", "EU"], target_price_value=199, price_from_prompt=False,
                   key_features=["24/7 activity tracking", "Sleep tracking"], has_battery=True, wireless=["BLE"])
PATCHES = {
    "add heart-rate and HRV sensing": RefinePatch(summary="Adds heart-rate and HRV sensing", ops=[
        AddFeature(op="add_feature", name="Heart-rate and HRV sensing", description="optical PPG on the wrist"),
        AddComponent(op="add_component", part="Optical heart-rate sensor (PPG)", category="electronic", qty=1,
                     rationale="Heart rate and HRV")]),
    "make it pink": RefinePatch(summary="Pink", ops=[SetColor(op="set_color", hex="#E8A0B4", name="Blush pink")]),
    "thinner, 8 mm pod": RefinePatch(summary="8 mm pod", ops=[SetDimensions(op="set_dimensions", height=8)]),
}


def _png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (232, 160, 180)).save(buf, format="PNG")
    return buf.getvalue()


def _mock(monkeypatch, delay: float = 0.0):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    calls = {"image": 0, "patch": 0}

    def fake(route, prompt, schema, **_k):
        time.sleep(delay)
        if schema is BriefDraft:
            return BRIEF.model_copy(deep=True)
        if schema is RefinePatch:
            calls["patch"] += 1
            for key, p in PATCHES.items():
                if key in prompt:
                    return p.model_copy(deep=True)
        raise llm.LLMError(route, "mocked provider failure")

    def fake_text(*_a, **_k):
        raise llm.LLMError("cn", "mocked provider failure")

    def fake_image(*_a, **_k):
        calls["image"] += 1
        return _png()

    monkeypatch.setattr(llm, "complete_json", fake)
    monkeypatch.setattr(llm, "complete_text", fake_text)
    monkeypatch.setattr(renders, "_call", fake_image)
    for name, mod in list(sys.modules.items()):
        if name.startswith("api.") and mod is not llm and getattr(mod, "complete_json", None) is not None:
            monkeypatch.setattr(mod, "complete_json", fake)
    return calls


def _wait(c, pid, n, *, settle=False, timeout=120):
    """Poll GET /versions until version n is not running (settle: also its render / background work)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        vs = c.get(f"/projects/{pid}/versions").json()
        v = next((x for x in vs if x["n"] == n), None)
        if v and v["status"] != "running" and (not settle or not (v["render_pending"] or v["background_pending"])):
            return v
        time.sleep(0.2)
    raise AssertionError(f"version {n} still running after {timeout} s: {v}")


def _stage(c, pid, n):
    return c.get(f"/projects/{pid}/stages/{n}").json()["artifact"]


def test_whoop_scenario(monkeypatch):
    calls = _mock(monkeypatch)
    pid = client.post("/projects", json=PROMPT).json()["id"]
    assert client.post(f"/projects/{pid}/refine", json={"message": "make it pink"}).status_code == 409  # not started

    r = client.post(f"/projects/{pid}/studio/start")
    assert r.status_code == 202 and r.json() == {"version": 1}
    v1 = _wait(client, pid, 1, settle=True)
    assert v1["status"] == "done" and v1["is_current"], v1
    pv = v1["preview"]
    assert pv["shape_family"] == "wearable_band"
    assert pv["glb_url"] == f"/files/{pid}/v1.glb" and client.get(pv["glb_url"]).status_code == 200
    assert pv["dimensions"]["height"]["label"] == "measured" and pv["dimensions"]["height"]["value"] == pytest.approx(10.0, abs=0.05)
    assert len(pv["unit_costs"]) == 3 and all(u["label"] == "estimate" for u in pv["unit_costs"])
    assert len(pv["top_factories"]) == 3 and all(f["label"] == "fictional" for f in pv["top_factories"])
    assert pv["render_url"] == f"/files/{pid}/v1.png" and calls["image"] >= 1
    assert any("ISO 10993" in c for c in [x["standard"] for x in _stage(client, pid, 4)["certifications"]])
    spec = _stage(client, pid, 3)
    assert any("strap" in b["part"].lower() for b in spec["bom"]) and any(p["name"] == "Strap" for p in spec["parts"])
    assert client.post(f"/projects/{pid}/studio/start").json() == {"version": 1}  # idempotent

    # v2: heart-rate + HRV → optical HR sensor, LCSC-matched; cost and certifications change
    t0 = time.time()
    assert client.post(f"/projects/{pid}/refine", json={"message": "add heart-rate and HRV sensing"}).json() == {"version": 2}
    v2 = _wait(client, pid, 2)
    print(f"\nrefine v2 preview in {time.time() - t0:.1f} s (mocked LLM)")
    assert v2["status"] == "done", v2
    hr = next(b for b in _stage(client, pid, 3)["bom"] if "heart" in b["part"].lower())
    assert hr["lcsc_pn"] == "C6454833" and hr["unit_cost_est"]["label"] == "sourced"
    comp = next(ch for ch in v2["changes"] if ch["area"] == "component")
    assert comp["label_kind"] == "sourced" and "C6454833" in comp["after"]
    assert any(ch["area"] == "feature" for ch in v2["changes"])
    assert any(ch["area"] == "cost" and ch["label"].startswith("Unit cost") for ch in v2["changes"])
    assert v2["preview"]["unit_costs"][1]["value"] > pv["unit_costs"][1]["value"] + 5  # MAX30102 ≈ $12 at 2k
    assert any("62471" in c for c in v2["preview"]["certifications"]) and not any("62471" in c for c in pv["certifications"])
    assert any(ch["area"] == "certification" for ch in v2["changes"])
    assert any(r["bom_item_id"] == hr["id"] for r in _stage(client, pid, 4)["component_risks"])
    assert any(line["lcsc_pn"] == "C6454833" for line in _stage(client, pid, 5)["bom_lines"])
    v2 = _wait(client, pid, 2, settle=True)

    # v3: pink → colour change, render re-requested, costs unchanged
    images_before = calls["image"]
    client.post(f"/projects/{pid}/refine", json={"message": "make it pink"})
    v3 = _wait(client, pid, 3, settle=True)
    assert [ch["area"] for ch in v3["changes"]] == ["color"], v3["changes"]
    assert v3["preview"]["color_hex"] == "#E8A0B4" and calls["image"] > images_before
    assert v3["preview"]["render_url"] == f"/files/{pid}/v3.png"
    assert [u["value"] for u in v3["preview"]["unit_costs"]] == [u["value"] for u in v2["preview"]["unit_costs"]]
    assert "#E8A0B4" in _stage(client, pid, 2)["directions"][0]["finish"]

    # v4: thinner 8 mm pod → CAD rebuilt, measured, DFM re-measured on the new STEP
    client.post(f"/projects/{pid}/refine", json={"message": "thinner, 8 mm pod"})
    v4 = _wait(client, pid, 4)
    dims = next(ch for ch in v4["changes"] if ch["area"] == "dimensions")
    assert dims["label"] == "Pod thickness" and dims["after"] == "8.0 mm" and dims["label_kind"] == "measured"
    assert v4["preview"]["dimensions"]["height"]["value"] == pytest.approx(8.0, abs=0.05)
    spec4 = _stage(client, pid, 3)
    assert spec4["cad_files"][1]["url"] == f"/files/{pid}/v4_enclosure.step"
    dfm4 = _stage(client, pid, 4)
    assert any(a["id"] == "a4_studio" and "v4" in a["text"] for a in dfm4["assumptions"])
    assert any(i["method"] == "measured" for i in dfm4["issues"])
    _wait(client, pid, 4, settle=True)

    # restore v2 → stage artifacts return to it
    r = client.post(f"/projects/{pid}/versions/2/restore")
    assert r.status_code == 200 and r.json()["is_current"] is True
    vs = client.get(f"/projects/{pid}/versions").json()
    assert [v["is_current"] for v in vs] == [False, True, False, False]
    assert _stage(client, pid, 3)["overall_dimensions"]["height"]["value"] == pytest.approx(10.0, abs=0.05)
    assert "#E8A0B4" not in _stage(client, pid, 2)["directions"][0]["finish"]
    assert client.post(f"/projects/{pid}/versions/9/restore").status_code == 404

    # "Make it": autorun through=13 continues from the refined product (v2)
    r = client.post(f"/projects/{pid}/autorun?through=13&wait=true")
    assert r.status_code == 200, r.text
    assert [x["stage"] for x in r.json()["results"]] == list(range(2, 14))  # stage 1 exists: not re-run
    assert any(b.get("lcsc_pn") == "C6454833" or "heart" in b["part"].lower() for b in _stage(client, pid, 3)["bom"])
    assert _stage(client, pid, 2)["directions"][0]["cad_parameters"]["family"] == 3
    assert _stage(client, pid, 8)["user_approved"] is True
    assert client.get(f"/projects/{pid}/factory-pack").status_code == 200


class _Failing:
    def __init__(self, status):
        self.status, self.chat, self.completions = status, self, self

    def with_options(self, **_):
        return self

    def create(self, **_):
        resp = httpx.Response(self.status, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
        raise openai.APIStatusError(f"Error code: {self.status} - Insufficient credits", response=resp, body=None)


def test_402_fails_the_version_and_keeps_the_previous(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    failing = _Failing(402)
    monkeypatch.setattr(llm, "_client", lambda *a, **k: failing)
    monkeypatch.setattr(renders, "_client", lambda *a, **k: failing)
    pid = client.post("/projects", json=PROMPT).json()["id"]
    assert client.post(f"/projects/{pid}/studio/start").status_code == 202
    r = client.post(f"/projects/{pid}/refine", json={"message": "make it pink"})  # sent while v1 builds: queued
    assert r.status_code == 202 and r.json() == {"version": 2}
    v1 = _wait(client, pid, 1, settle=True)
    assert v1["status"] == "done"  # every LLM step fell back; version 1 still exists
    before = _stage(client, pid, 2)
    v2 = _wait(client, pid, 2)
    assert v2["status"] == "failed" and "402" in v2["error"] and "version 1 is still current" in v2["error"]
    vs = client.get(f"/projects/{pid}/versions").json()
    assert [v["is_current"] for v in vs] == [True, False]
    assert _stage(client, pid, 2)["directions"][0] == before["directions"][0]  # (d2/d3 may be patched in lazily)
    assert client.post(f"/projects/{pid}/versions/2/restore").status_code == 409


@pytest.fixture
def server(monkeypatch):
    import uvicorn

    _mock(monkeypatch, delay=1.5)
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    deadline = time.time() + 20
    while not srv.started and time.time() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{srv.servers[0].sockets[0].getsockname()[1]}"
    srv.should_exit = True
    th.join(10)


def test_polling_stays_fast_during_refine(server):
    c = httpx.Client(base_url=server, timeout=5)
    pid = c.post("/projects", json=PROMPT).json()["id"]
    assert c.post(f"/projects/{pid}/studio/start").status_code == 202
    lat = []
    for n, msg in ((1, None), (2, "add heart-rate and HRV sensing"), (3, "thinner, 8 mm pod")):
        if msg:
            assert c.post(f"/projects/{pid}/refine", json={"message": msg}).json() == {"version": n}
        t0 = time.time()
        while time.time() - t0 < 120:
            s = time.perf_counter()
            r = c.get(f"/projects/{pid}/versions")
            lat.append(time.perf_counter() - s)
            assert r.status_code == 200
            v = r.json()[-1]
            assert c.get(f"/projects/{pid}").status_code == 200
            if v["status"] != "running":
                break
            time.sleep(0.3)
        assert v["status"] == "done", v
    assert max(lat) < 1.0, f"slowest poll {max(lat):.2f} s"
    assert len(lat) >= 6


def test_cad_families_clamp_and_build(tmp_path):
    from api.cad.build import build_direction, normalize, shape_facts
    from api.cad.wearables import PRESETS

    p = normalize({**PRESETS[3], "height": 2, "length": 500, "strap_width": 90})
    assert (p["family"], p["length"], p["strap_width"]) == (3, 60.0, 28.0)  # pod ≤ 60 mm, strap < pod width
    assert p["height"] >= 4 * p["wall"] + 1.0
    size = shape_facts(build_direction({**PRESETS[3], "height": 8}, tmp_path)["step"])["size"]
    assert size == pytest.approx((44.0, 30.0, 8.0), abs=0.05)
    r = normalize({**PRESETS[4], "length": 40, "width": 10})
    assert r["length"] == r["width"] == 30.0
    size = shape_facts(build_direction(PRESETS[4], tmp_path)["step"])["size"]
    assert size == pytest.approx((22.0, 22.0, 8.0), abs=0.05)
    assert normalize({"family": 1, "length": 80, "width": 50}) == normalize({"family": 1, "length": 80, "width": 80})


def test_family_choice():
    from api.studio.product import studio_family

    class B:
        product_name, one_liner, category, key_features = "", "", "", []

    assert studio_family(B(), "Whoop competitor") == "wearable_band"
    assert studio_family(B(), "a sleep ring with temperature sensing") == "ring"
    assert studio_family(B(), "desk lamp with a ring light") is None
    assert studio_family(B(), "smart dog bowl") is None
