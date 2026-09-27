"""W29b — QA 3D-wave fixes: stale photo after a look edit (M1), series-pack runtime + whole-product mass (M2),
look-only edits keep the factory shortlist (m2), duplicate change line (p2), discovery clash (P1). Offline."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from api.main import app
from contracts.artifacts import BOMItem, ProductPhoto

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _seed():
    assert client.post("/demo/reset").status_code == 200
    yield


def _wait(pid: str, n: int) -> dict:
    t0 = time.monotonic()
    while time.monotonic() - t0 < 60:
        v = client.get(f"/projects/{pid}/versions/{n}").json()
        if v["status"] != "running":
            return v
        time.sleep(0.1)
    raise AssertionError("still running")


def _shortlist(pid: str) -> list[str]:
    return [f["factory_name"] for f in client.get(f"/projects/{pid}/stages/7").json()["artifact"]["shortlist"]]


def test_look_edit_marks_photo_stale_and_keeps_shortlist():
    pid = "demo_whoop_kitesurf"
    before = client.get(f"/projects/{pid}/versions").json()[-1]
    assert before["preview"]["photos"]  # the showcase's pink photos
    shortlist = _shortlist(pid)
    r = client.post(f"/projects/{pid}/parts/top_shell/edit", json={"colour_hex": "#9DB09A"})
    v = _wait(pid, r.json()["version"])
    assert v["status"] == "done" and v["look_changed"]
    p = v["preview"]
    assert p["photo_stale"] is True and p["photos"] == [] and p["render_url"] is None  # never the old pink photo as current
    assert _shortlist(pid) == shortlist  # m2: colour only → same factories
    photos = client.get(f"/projects/{pid}/photos").json()
    assert all(ph["version"] == v["n"] for ph in photos["photos"])
    r = client.post(f"/projects/{pid}/parts/strap/edit", json={"material": "fabric"})
    v2 = _wait(pid, r.json()["version"])
    assert v2["status"] == "done" and v2["preview"]["photo_stale"] and _shortlist(pid) == shortlist


def test_param_edit_lists_the_change_once():
    pid = "demo_whoop_kitesurf"
    top = next(p for p in client.get(f"/projects/{pid}/parts").json()["parts"] if p["part_id"] == "top_shell")
    e = next(x for x in top["editable"] if x["param"] == "pod_thickness")
    v = _wait(pid, client.post(f"/projects/{pid}/parts/top_shell/edit", json={"param": "pod_thickness", "value": e["value"] + 1}).json()["version"])
    assert v["status"] == "done"
    assert [c["label"] for c in v["changes"]].count("Pod thickness") == 0
    assert sum(c["label"].startswith("Pod thickness") for c in v["changes"]) == 1


def test_auto_photo_with_stored_reference(monkeypatch):
    from api.cad.build import project_dir
    from api.cad.photos import engine as photos
    from api.studio import edit, store

    pid = "demo_drone_follow"
    n = store.next_n(pid)
    (project_dir(pid) / f"ref_v{n}.png").write_bytes(b"\x89PNG fake")
    calls = []
    monkeypatch.setattr(photos, "start_job", lambda p, k, shots, ref=None, **kw: calls.append((p, k, shots, ref)))
    real = photos.project_photos
    monkeypatch.setattr(photos, "project_photos", lambda p: real(p).model_copy(update={"configured": True}))
    part = next(p for p in client.get(f"/projects/{pid}/parts").json()["parts"] if p["colour_editable"] and p["role"] != "shell_top")
    r = client.post(f"/projects/{pid}/parts/{part['part_id']}/edit", json={"colour_hex": "#E07A3A"})
    assert r.json()["version"] == n
    v = _wait(pid, n)
    assert v["status"] == "done" and v["preview"]["photo_stale"]
    assert calls == [(pid, n, ["hero_studio"], b"\x89PNG fake")]  # same auto hero_studio path, stored viewer reference
    # the photo landing clears the flag
    photos.attach_photo(pid, n, ProductPhoto(shot="hero_studio", url=f"/files/{pid}/photo_v{n}_hero_studio.png",
                                             label=photos.LABEL_REF, reference="viewer", aspect_ratio="4:5", version=n))
    assert store.get_version(pid, n).preview.photo_stale is False
    del edit


def test_vacuum_series_pack_runtime_and_mass():
    eng = client.get("/projects/demo_stick_vacuum/engineering").json()
    el = eng["electronics"]
    assert el["battery_voltage"]["value"] == pytest.approx(21.6)
    life_min = el["battery_life"]["value"] * 60
    assert 14 <= life_min <= 18, life_min  # 2600 mAh × 85 % / (180 W / 21.6 V) ≈ 16 min
    motors = [ln for ln in el["power_budget"] if ln["block"] == "motor"]
    assert len(motors) == 1
    an = client.get("/projects/demo_stick_vacuum/anatomy").json()
    caps = " ".join(s["caption"] for s in an["steps"])
    assert "in series, 21.6 V pack" in caps and "runtime 16 min" in caps and "4 min" not in caps
    assert "product mass 1." in an["steps"][-1]["caption"]  # all parts, not the 280 g enclosure


def test_classify_uses_the_part_name_first():
    from api.engineering.electronics import classify

    b = classify(BOMItem(id="e1", part="21.6 V (6S) rechargeable Li-ion battery pack", category="electronic", qty=1,
                         description="Powers the BLDC motor"))
    t = classify(BOMItem(id="e4", part="Pistol-grip trigger switch", category="electronic", qty=1, description="Starts the motor"))
    assert b.kind == "battery" and t.kind == "button"


def test_curated_module_has_no_route_hook():
    import api.cad.partnames_curated as m

    assert not callable(getattr(m, "register", None))
