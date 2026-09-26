"""End-to-end API flow on fixtures with no API key (W0 acceptance)."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_demo_reset_seeds_desk_lamp():
    r = client.post("/demo/reset")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()["projects"]]
    assert "demo_desk_lamp" in ids
    detail = client.get("/projects/demo_desk_lamp").json()
    assert [s["status"] for s in detail["stages"]] == ["validated"] * 13


def test_full_flow_all_13_stages_without_key():
    p = client.post("/projects", json={"mode": "idea", "prompt": "Magnetic rechargeable desk lamp, minimalist, sold €89"}).json()
    pid = p["id"]
    assert p["example"] == "desk_lamp"
    for n in range(1, 14):
        r = client.post(f"/projects/{pid}/stages/{n}/run", json={"inputs": {}})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["stage"] == n and body["artifact"]["stage"] == n and body["artifact"]["project_id"] == pid
        assert client.get(f"/projects/{pid}/stages/{n}").status_code == 200
    detail = client.get(f"/projects/{pid}").json()
    assert all(s["status"] == "draft" for s in detail["stages"])
    assert client.get(f"/projects/{pid}/factory-pack").json()["project_id"] == pid
    pdf = client.get(f"/projects/{pid}/export")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_autorun_and_update():
    pid = client.post("/projects", json={"mode": "idea", "prompt": "Smart dog bowl that weighs food, Wi-Fi"}).json()["id"]
    r = client.post(f"/projects/{pid}/autorun?wait=true")
    assert r.status_code == 200 and r.json()["autorun"]["state"] == "done"
    assert [x["stage"] for x in r.json()["results"]] == [1, 2, 3, 4, 5, 6, 7]
    design = client.get(f"/projects/{pid}/stages/2").json()["artifact"]
    design["chosen_direction_id"] = "d2"
    r = client.put(f"/projects/{pid}/stages/2", json={"artifact": design, "validate_stage": True})
    assert r.status_code == 200 and r.json()["status"] == "validated"
    assert r.json()["artifact"]["chosen_direction_id"] == "d2"


def test_factory_portal():
    fs = client.get("/factories").json()
    assert len(fs) >= 3 and all(f["fictional"] for f in fs)
    assert client.get(f"/factories/{fs[0]['id']}").status_code == 200
    assert isinstance(client.get(f"/factories/{fs[0]['id']}/rfqs").json(), list)
    assert client.get("/factories/nope").status_code == 404


def test_errors():
    assert client.get("/projects/nope").status_code == 404
    assert client.post("/projects/demo_desk_lamp/stages/14/run").status_code == 404


def test_demo_reset_also_resets_factory_network():
    """W7 fix c: live RFQs sent by stage 8 must not survive /demo/reset (portal would show stale RFQs)."""
    from factory_mcp import network

    fid = client.get("/factories").json()[0]["id"]
    rfq_id = network.request_quote(fid, "fp_test", [500], project_id="p_test", product_name="Reset probe")
    assert rfq_id in {r["rfq"]["id"] for r in client.get(f"/factories/{fid}/rfqs").json()}
    assert client.post("/demo/reset").status_code == 200
    assert rfq_id not in {r["rfq"]["id"] for r in client.get(f"/factories/{fid}/rfqs").json()}


def test_autorun_async_202_and_polling():
    """W7 k: POST /autorun answers 202 at once; GET /projects/{id} shows progress until state == done."""
    import time

    pid = client.post("/projects", json={"mode": "idea", "prompt": "Bike light with brake detection"}).json()["id"]
    r = client.post(f"/projects/{pid}/autorun")
    assert r.status_code == 202 and r.json()["autorun"]["state"] == "running" and r.json()["results"] == []
    deadline = time.time() + 120
    while time.time() < deadline:
        auto = client.get(f"/projects/{pid}").json()["autorun"]
        if auto["state"] != "running":
            break
        time.sleep(0.5)
    assert auto["state"] == "done" and auto["completed_stages"] == [1, 2, 3, 4, 5, 6, 7] and auto["current_stage"] is None
    stages = client.get(f"/projects/{pid}").json()["stages"]
    assert [s["status"] for s in stages[:7]] == ["draft"] * 7


def test_stage_timeout_serves_fixture(monkeypatch):
    """W7 k: a stuck handler is abandoned after STAGE_TIMEOUT_S → fixture with fallback_reason 'timeout…'."""
    import time

    from api.stages import runner
    from api.stages.registry import STAGE_HANDLERS

    pid = client.post("/projects", json={"mode": "idea", "prompt": "Magnetic desk lamp"}).json()["id"]
    monkeypatch.setattr(runner, "STAGE_TIMEOUT_S", 0.2)
    monkeypatch.setitem(STAGE_HANDLERS, 13, lambda ctx: time.sleep(2))
    body = client.post(f"/projects/{pid}/stages/13/run", json={"inputs": {}}).json()
    assert body["fallback"] is True and body["artifact"]["fallback_reason"].startswith("timeout")


def test_register_factory():
    """W7 h: POST /factories → register_capacity → Fictional factory visible in the portal."""
    body = {"name": "Harbor Test Plastics", "region": "Ningbo, Zhejiang", "processes": ["injection_molding"],
            "materials": ["PC/ABS"], "moq": 500, "certifications": ["ISO 9001"], "lead_time_days": 30,
            "monthly_capacity": 20000, "current_load_pct": 40}
    r = client.post("/factories", json=body)
    assert r.status_code == 201, r.text
    f = r.json()
    assert f["name"].endswith("(fictional)") and f["label"] == "fictional" and f["fictional"] is True
    assert f["id"] in {x["id"] for x in client.get("/factories").json()}
    assert client.post("/factories", json={**body, "processes": []}).status_code == 422
    pp = f["past_performance"]  # W7g B15: no invented 0 % stats for a new factory
    assert pp["no_data"] is True and pp["on_time_rate_pct"] is None and pp["defect_rate_pct"] is None


def test_files_head():
    """W7 m: HEAD on /files works (viewer pre-checks)."""
    assert client.head("/files/demo_desk_lamp/d1.glb").status_code == 200
    assert client.head("/files/demo_desk_lamp/nope.glb").status_code == 404


def test_project_detail_has_no_fallback_for_seeded_demo():
    """W7g B1: cached demo projects are pre-built examples, not AI failures: no fallback flag."""
    client.post("/demo/reset")
    d = client.get("/projects/demo_desk_lamp").json()
    assert d["has_fallback"] is False and d["fallback_stages"] == []


def test_stage7_reasons_humanised():
    """W7g B7: no raw enums (injection_molding, pcba) in stage 7 reasons."""
    from factory_mcp import network
    from contracts.artifacts import SearchCapacityQuery

    ms = network.rank_for_product([SearchCapacityQuery(process="injection_molding", material="PC/ABS", quantity=2000, certifications_required=[]),
                                   SearchCapacityQuery(process="pcba", material="FR-4", quantity=2000, certifications_required=[])])
    text = " ".join(r for m in ms for r in m.reasons) + " ".join(c.note for m in ms for c in m.score_breakdown)
    assert "injection_molding" not in text and "pcba" not in text and "Injection molding" in text
