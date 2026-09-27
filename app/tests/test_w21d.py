"""W21d: photos survive preview refreshes, photo routes guarded in api/auth.py, the live render uses the stored viewer
reference, solar break-even counted in installations. LLM / image model always mocked."""

import io

from fastapi.testclient import TestClient

import api.cad.renders as renders
from api import auth
from api.main import app
from tests.test_studio import PROMPT, _mock, _wait

client = TestClient(app)


def _png(rgb=(10, 200, 30)) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), rgb).save(buf, format="PNG")
    return buf.getvalue()


def test_preview_refresh_keeps_photos_and_render_uses_viewer_reference(monkeypatch):
    from api.cad.build import project_dir
    from api.studio import engine, store
    from contracts.artifacts import ProductPhoto

    _mock(monkeypatch)
    seen = []

    def fake_call(prompt, timeout, **kw):
        seen.append((prompt, kw.get("reference")))
        return _png()

    monkeypatch.setattr(renders, "_call", fake_call)
    pid = client.post("/projects", json=PROMPT).json()["id"]
    client.post(f"/projects/{pid}/studio/start")
    _wait(client, pid, 1, settle=True)
    photo = ProductPhoto(shot="hero_studio", url=f"/files/{pid}/photo_v1_hero_studio.png", label="Photo-styled from the CAD",
                         reference="viewer", aspect_ratio="4:5", version=1)
    v = store.get_version(pid, 1)
    v.preview.photos = [photo]
    store.save_version(pid, v)
    engine._refresh_preview(pid, 1)  # a background result lands (DFM review, render …)
    assert [p.shot for p in store.get_version(pid, 1).preview.photos] == ["hero_studio"]

    # a colour refine re-renders version 2; a stored viewer capture ref_v2.png is sent as the reference
    ref = _png((200, 10, 90))
    (project_dir(pid) / "ref_v2.png").write_bytes(ref)
    seen.clear()
    client.post(f"/projects/{pid}/refine", json={"message": "make it pink"})
    _wait(client, pid, 2, settle=True)
    assert seen and seen[-1][1] == ref and seen[-1][0].startswith(renders.REFERENCE_NOTE)


def test_photo_routes_are_guarded_in_auth(monkeypatch):
    auth.reset_rate_limits()
    for k in ("API_SHARED_KEY", "DEMO_READONLY"):
        monkeypatch.delenv(k, raising=False)
    pid = client.post("/projects", json={"mode": "idea", "prompt": "desk lamp"}).json()["id"]
    monkeypatch.setenv("DEMO_READONLY", "1")
    for path in (f"/projects/{pid}/versions/1/photo", f"/projects/{pid}/photos/kit"):
        r = client.post(path)
        assert r.status_code == 403 and "Read-only" in r.json()["detail"], path
    monkeypatch.delenv("DEMO_READONLY")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setenv("PHOTO_RATE_LIMIT_PER_DAY", "1")
    h = {"X-Forwarded-For": "7.7.7.7"}
    assert client.post(f"/projects/{pid}/photos/kit", headers=h).status_code != 429  # counted (404: no Studio version)
    r = client.post(f"/projects/{pid}/photos/kit", headers=h)
    assert r.status_code == 429 and "Photo limit" in r.json()["detail"]
    import api.cad.photos.routes as routes

    assert not hasattr(routes, "_hits")  # the duplicate in-route limiter is gone
    auth.reset_rate_limits()


def test_solar_breakeven_in_installations():
    client.post("/demo/reset")
    c = client.get("/projects/demo_solar_biarritz/stages/5")
    if c.status_code != 200:
        import pytest

        pytest.skip("solar showcase not recorded")
    c = c.json()["artifact"]
    be = c["breakeven_units"]
    assert be["unit"] == "installations" and 2 <= be["value"] <= c["reference_quantity"]
    assert "pilot" in be["source_or_assumption"] and "installations" in be["source_or_assumption"].lower()
    assert any("Tools" in x["name"] for x in c["cash_breakdown"])


# --------------------------------------------------------------------------- W21e


def test_same_look_reuses_the_previous_photo(monkeypatch):
    from api.cad.build import project_dir
    from api.cad.photos import engine as photos
    from api.studio.patch import RefinePatch, SetTargetPrice
    from contracts.artifacts import ProductPhoto
    from tests import test_studio as ts

    monkeypatch.setitem(ts.PATCHES, "target retail $149", RefinePatch(summary="$149", ops=[
        SetTargetPrice(op="set_target_price", value=149, currency="USD")]))
    _mock(monkeypatch)
    calls = []
    monkeypatch.setattr(renders, "_call", lambda *a, **k: calls.append(1) or _png())
    pid = client.post("/projects", json=PROMPT).json()["id"]
    client.post(f"/projects/{pid}/studio/start")
    _wait(client, pid, 1, settle=True)
    (project_dir(pid) / "photo_v1_hero_studio.png").write_bytes(_png())
    (project_dir(pid) / "ref_v1.png").write_bytes(_png((1, 2, 3)))
    photos.attach_photo(pid, 1, ProductPhoto(shot="hero_studio", url=f"/files/{pid}/photo_v1_hero_studio.png",
                                             label="Photo-styled from the CAD (AI image, geometry from our CAD)",
                                             reference="viewer", aspect_ratio="4:5", version=1))
    calls.clear()
    client.post(f"/projects/{pid}/refine", json={"message": "target retail $149"})
    v2 = _wait(client, pid, 2, settle=True)
    assert v2["look_changed"] is False
    [p] = v2["preview"]["photos"]
    assert p["url"] == f"/files/{pid}/photo_v2_hero_studio.png" and p["label"].startswith("Photo-styled") and p["version"] == 2
    assert client.get(p["url"]).status_code == 200 and (project_dir(pid) / "ref_v2.png").exists()
    r = client.post(f"/projects/{pid}/versions/2/photo")  # the UI's auto photo: reused, no image call
    assert r.status_code == 202 and calls == []
    client.post(f"/projects/{pid}/refine", json={"message": "make it pink"})
    v3 = _wait(client, pid, 3, settle=True)
    assert v3["look_changed"] is True and not any(x["shot"] == "hero_studio" and x["version"] == 2 for x in v3["preview"]["photos"])


def test_solar_single_installed_price():
    client.post("/demo/reset")
    vs = client.get("/projects/demo_solar_biarritz/versions").json()
    if not vs:
        import pytest

        pytest.skip("solar showcase not recorded")
    pv = vs[-1]["preview"]
    card = next(e for e in client.get("/examples").json() if e["slug"] == "solar_biarritz")
    eng = client.get("/projects/demo_solar_biarritz/engineering").json()
    c5 = client.get("/projects/demo_solar_biarritz/stages/5").json()["artifact"]
    price = pv["installed_price"]["value"]
    assert pv["unit_basis"] == "per_installation" and price == card["unit_cost"]["value"] == eng["installation_cost"]["value"] \
        == c5["target_retail_price"]["value"]
    assert pv["installer_cost"]["value"] == c5["tiers"][0]["unit_cost"]["value"] < price
    assert "not the customer price" in c5["tiers"][0]["unit_cost"]["source_or_assumption"]
    added = [c["after"] for c in vs[-1]["changes"] if c["label"] == "Component added"]
    assert added and all("/installation" in a and "$0.30" not in a for a in added)
    assert any("$3,400.00" in a for a in added) and any("$950.00" in a for a in added)


def test_whoop_listing_kit_is_complete():
    client.post("/demo/reset")
    brand = client.get("/projects/demo_whoop_kitesurf/stages/13").json()["artifact"]
    shots = [p["shot"] for p in brand["listing_photos"]]
    assert shots == ["packshot_white", "lifestyle", "in_hand_scale", "detail_macro"]
    for p in brand["listing_photos"]:
        assert p["reference"] == "cad_render" and p["label"].startswith("Photo-styled from the CAD")
        assert client.get(p["url"]).status_code == 200
    v4 = client.get("/projects/demo_whoop_kitesurf/versions/4").json()
    assert {"hero_studio", "packshot_white", "in_hand_scale", "detail_macro", "lifestyle"} <= {p["shot"] for p in v4["preview"]["photos"]}
    assert client.get("/projects/demo_whoop_kitesurf/export").status_code == 200
