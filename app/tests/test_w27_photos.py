"""W27: reference-based product photos + listing kit. The image model is always mocked (renders._call)."""

import base64
import io
import time

import pytest
from fastapi.testclient import TestClient

import api.cad.renders as renders
from api.cad.photos import engine as E
from api.cad.photos import shots as S
from api.main import app

client = TestClient(app)
PID = "demo_whoop_kitesurf"  # showcase: 4 Studio versions, current = 4, Blender CAD render hero_v4.png committed
ENV = {"OPENROUTER_API_KEY": "sk-test-not-real", "LLM_IMAGE_MODEL": "m/image", "API_SHARED_KEY": "", "DEMO_READONLY": "",
       "PHOTO_RATE_LIMIT_PER_DAY": "0", "RATE_LIMIT_PER_DAY": "0"}
PRODUCT_WORDS = ("pink", "band", "strap", "wearable", "whoop", "sensor", "pod", "44 ×", "PC/ABS", "kitesurf recovery")


def _png(w=96, h=120, colour=(200, 120, 140), mode="RGB", fmt="PNG") -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new(mode, (w, h), colour if mode == "RGB" else colour + (255,)).save(buf, format=fmt)
    return buf.getvalue()


class Error402(Exception):
    status_code = 402


@pytest.fixture()
def mocked(monkeypatch):
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
    E._jobs.clear()
    calls = []

    def fake_call(prompt, timeout, *, reference=None, aspect_ratio="1:1", model=None):
        calls.append({"prompt": prompt, "reference": reference, "aspect_ratio": aspect_ratio, "model": model})
        w, h = (int(x) * 200 for x in aspect_ratio.split(":"))
        return _png(w, h)

    monkeypatch.setattr(renders, "_call", fake_call)
    import shutil

    from api.cad.build import files_root

    assert client.post("/demo/reset").status_code == 200
    for name in ("ref_v4.png", "photos.json") + tuple(f"photo_v{n}_{s}.png" for n in (1, 4) for s in S.SHOTS):
        (files_root() / PID / name).unlink(missing_ok=True)
    shutil.rmtree(files_root() / PID / "__none__", ignore_errors=True)
    return calls


def _wait(pid=PID, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"/projects/{pid}/photos").json()
        if r["job"]["state"] != "running":
            return r
        time.sleep(0.05)
    raise AssertionError("photo job still running")


# --------------------------------------------------------------------------- prompts / labels


def test_shot_prompts_direct_photography_only():
    for shot in S.SHOTS:
        for cat in list(S.SCENES) + [None, "unknown"]:
            p = S.shot_prompt(shot, cat)
            assert p.endswith(S.PRESERVE)
            assert S.PRESERVE.endswith("No added text, logos, watermarks or extra objects unless stated.")
    assert "#F4F1EA" in S.shot_prompt("hero_studio", "wearable") and "100 mm" in S.shot_prompt("hero_studio", "wearable")
    assert "infinite white" in S.shot_prompt("packshot_white", None)
    assert "kitesurfer" in S.shot_prompt("lifestyle", "wearable") and "golden hour" in S.shot_prompt("lifestyle", "wearable")
    assert "nursery" in S.shot_prompt("lifestyle", "furniture_baby")
    assert "apartment" in S.shot_prompt("lifestyle", "vacuum")
    assert "roof" in S.shot_prompt("lifestyle", "solar_roof")
    assert "coastline" in S.shot_prompt("lifestyle", "drone")
    assert {S.SHOTS[s].aspect_ratio for s in ("hero_studio", "lifestyle", "in_hand_scale")} == {"4:5"}
    assert {S.SHOTS[s].aspect_ratio for s in ("packshot_white", "detail_macro")} == {"1:1"}


def test_labels():
    assert E.label_for("hero_studio", "cad_render") == "Photo-styled from the CAD (AI image, geometry from our CAD)"
    assert E.label_for("hero_studio", "viewer") == E.LABEL_REF
    assert E.label_for("packshot_white", "none") == "AI concept image (no CAD reference)"
    assert E.label_for("lifestyle", "cad_render") == E.LABEL_REF + " · Staged scene — illustrative"
    assert E.label_for("lifestyle", "none").endswith("Staged scene — illustrative")


# --------------------------------------------------------------------------- render_product_photo


def test_cad_render_reference_passed_through(mocked):
    ph = E.render_product_photo(PID, 4, "hero_studio")
    call = mocked[-1]
    from api.cad.files import resolve_file

    assert call["reference"] == resolve_file(PID, "hero_v4.png").read_bytes()
    assert call["aspect_ratio"] == "4:5"
    low = call["prompt"].lower()
    assert not any(w.lower() in low for w in PRODUCT_WORDS), call["prompt"]
    assert ph.reference == "cad_render" and ph.label == E.LABEL_REF and ph.url == f"/files/{PID}/photo_v4_hero_studio.png"
    v = client.get(f"/projects/{PID}/versions/4").json()
    assert v["preview"]["render_url"] == ph.url  # hero replaces the concept image
    hero = [p for p in v["preview"]["photos"] if p["shot"] == "hero_studio"]
    assert len(hero) == 1 and hero[0]["model"] == "m/image"  # the new photo replaced the recorded one
    from PIL import Image

    im = Image.open(resolve_file(PID, "photo_v4_hero_studio.png"))
    assert abs(im.width / im.height - 0.8) < 0.01


def test_viewer_capture_wins_and_is_saved(mocked):
    cap = _png(300, 300, (10, 200, 10))
    r = client.post(f"/projects/{PID}/versions/4/photo?shot=packshot_white", content=cap, headers={"content-type": "image/png"})
    assert r.status_code == 202 and r.json() == {"version": 4, "shots": ["packshot_white"]}
    st = _wait()
    assert st["job"]["state"] == "done" and st["job"]["done"] == ["packshot_white"]
    ph = next(p for p in st["photos"] if p["shot"] == "packshot_white")
    assert ph["reference"] == "viewer" and ph["label"] == E.LABEL_REF and ph["aspect_ratio"] == "1:1"
    from PIL import Image

    sent = Image.open(io.BytesIO(mocked[-1]["reference"]))
    assert sent.size == (300, 300) and sent.getpixel((5, 5)) == (10, 200, 10)
    assert client.get(f"/files/{PID}/ref_v4.png").status_code == 200


def test_json_base64_and_multipart_bodies(mocked):
    b64 = "data:image/jpeg;base64," + base64.b64encode(_png(200, 200, fmt="JPEG")).decode()
    assert client.post(f"/projects/{PID}/versions/4/photo?shot=detail_macro", json={"image_base64": b64}).status_code == 202
    _wait()
    files = {"image": ("viewer.png", _png(150, 150), "image/png")}
    assert client.post(f"/projects/{PID}/versions/4/photo?shot=hero_studio", files=files).status_code == 202
    assert _wait()["job"]["state"] == "done"
    assert all(c["reference"] is not None for c in mocked)


def test_no_reference_text_fallback(mocked):
    ph = E.render_product_photo(PID, 1, "hero_studio")  # v1: no ref_v1 / hero_v1 / hero_<dN> for this showcase
    assert mocked[-1]["reference"] is None
    assert ph.reference == "none" and ph.label == E.LABEL_NOREF
    p = mocked[-1]["prompt"]
    assert "The product:" in p and "mm" in p and "reference" not in p.lower()


def test_lifestyle_label_and_scene(mocked):
    ph = E.render_product_photo(PID, 4, "lifestyle")
    assert ph.staged and ph.label.endswith("Staged scene — illustrative")
    assert "kitesurfer" in mocked[-1]["prompt"]  # category wearable → beach scene


# --------------------------------------------------------------------------- validation


@pytest.mark.parametrize("body,ctype,code", [
    (b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024 + 10), "image/png", 413),
    (b"GIF89a" + b"0" * 100, "image/png", 415),
    (b"\x89PNG\r\n\x1a\nnot really a png", "image/png", 415),
    (b"hello", "text/plain", 415),
])
def test_upload_validation(mocked, body, ctype, code):
    r = client.post(f"/projects/{PID}/versions/4/photo", content=body, headers={"content-type": ctype})
    assert r.status_code == code, r.text
    assert not mocked


def test_tiny_image_and_bad_shot_and_version(mocked):
    r = client.post(f"/projects/{PID}/versions/4/photo", content=_png(10, 10), headers={"content-type": "image/png"})
    assert r.status_code == 422
    assert client.post(f"/projects/{PID}/versions/4/photo?shot=billboard").status_code == 422
    assert client.post(f"/projects/{PID}/versions/99/photo").status_code == 404
    assert client.post("/projects/nope/versions/1/photo").status_code == 404


def test_guards(monkeypatch, mocked):
    monkeypatch.setenv("DEMO_READONLY", "1")
    assert client.post(f"/projects/{PID}/photos/kit").status_code == 403
    monkeypatch.setenv("DEMO_READONLY", "")
    monkeypatch.setenv("LLM_IMAGE_MODEL", "")
    assert client.post(f"/projects/{PID}/photos/kit").status_code == 503
    assert client.get(f"/projects/{PID}/photos").json()["configured"] is False


# --------------------------------------------------------------------------- failures keep the previous image


def test_402_calm_failure_keeps_previous(mocked, monkeypatch):
    first = E.render_product_photo(PID, 4, "hero_studio")
    from api.cad.files import resolve_file

    before = resolve_file(PID, "photo_v4_hero_studio.png").read_bytes()

    def broke(*a, **k):
        raise Error402("Payment Required")

    monkeypatch.setattr(renders, "_call", broke)
    with pytest.raises(E.PhotoFailed) as ei:
        E.render_product_photo(PID, 4, "hero_studio")
    assert ei.value.status == 402 and "previous photo is kept" in ei.value.reason
    assert resolve_file(PID, "photo_v4_hero_studio.png").read_bytes() == before
    assert client.post(f"/projects/{PID}/versions/4/photo?shot=hero_studio").status_code == 202
    st = _wait()
    assert st["job"]["state"] == "failed" and "402" in st["job"]["error"] and st["job"]["failed"] == ["hero_studio"]
    assert next(p for p in st["photos"] if p["shot"] == "hero_studio")["url"] == first.url
    v = client.get(f"/projects/{PID}/versions/4").json()
    assert v["preview"]["render_url"] == first.url


# --------------------------------------------------------------------------- listing kit


def test_listing_kit_attaches_to_stage_13_and_dossier(mocked):
    r = client.post(f"/projects/{PID}/photos/kit")
    assert r.status_code == 202 and r.json()["shots"] == list(S.LISTING_KIT)
    st = _wait()
    assert st["job"]["state"] == "done" and sorted(st["job"]["done"]) == sorted(S.LISTING_KIT)
    assert {p["shot"] for p in st["photos"]} >= set(S.LISTING_KIT)
    assert {c["aspect_ratio"] for c in mocked} == {"4:5", "1:1"}
    brand = client.get(f"/projects/{PID}/stages/13").json()
    lp = (brand.get("artifact") or brand)["listing_photos"]
    assert [p["shot"] for p in lp] == list(S.LISTING_KIT)
    assert all(p["reference"] == "cad_render" for p in lp)
    from api.export import pdf
    from api.stages.registry import StageContext
    from api.stages import runner

    ctx = StageContext(project=runner.get_project(PID), stage=0,
                       artifacts={n: a for n in range(1, 14) if (a := runner.get_artifact(PID, n)) is not None})
    page = pdf.listing_photos_section(ctx)
    assert len(page) > 3
    assert client.get(f"/projects/{PID}/export").content[:4] == b"%PDF"


def test_kit_without_detail_and_conflict(mocked, monkeypatch):
    import threading

    gate = threading.Event()
    orig = renders._call

    def slow(*a, **k):
        gate.wait(5)
        return orig(*a, **k)

    monkeypatch.setattr(renders, "_call", slow)
    r = client.post(f"/projects/{PID}/photos/kit?detail=false")
    assert r.json()["shots"] == ["packshot_white", "lifestyle", "in_hand_scale"]
    assert client.post(f"/projects/{PID}/photos/kit").status_code == 409
    gate.set()
    assert _wait()["job"]["state"] == "done"


def test_showcase_cards_use_cad_photo():
    """Recorded showcases: gallery hero = hero_studio photo styled from the Blender CAD render, labelled honestly."""
    cards = client.get("/examples").json()
    with_photo = [c for c in cards if c.get("photos")]
    assert with_photo, "no showcase has recorded photos"
    for c in with_photo:
        hero = next((p for p in c["photos"] if p["shot"] == "hero_studio"), None)
        if hero:
            assert c["hero_image_url"] == hero["url"] and c["hero_image_label"] == E.LABEL_REF
            assert hero["reference"] == "cad_render"
            assert client.get(hero["url"]).status_code == 200
