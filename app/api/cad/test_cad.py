"""W2 acceptance — CAD (stages 2-3, /files). Offline, no LLM key: `uv run pytest api/cad api/dfm`."""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp())
os.environ["DB_PATH"] = str(_TMP / "test.db")  # never the shared app.db (/demo/reset below)
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["FILES_DIR"] = str(_TMP / "files")

import time  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.cad.build import build_direction, normalize, shape_facts  # noqa: E402
from api.main import app  # noqa: E402
from api.stages import runner  # noqa: E402
from contracts.artifacts import DesignArtifact, SpecArtifact  # noqa: E402

client = TestClient(app)


@pytest.mark.parametrize("family,dims", [(0, (140, 90, 40)), (1, (110, 110, 35)), (2, (86, 54, 9))])
def test_three_families_build_and_step_reimports(tmp_path, family, dims):
    L, W, H = dims
    t = time.time()
    files = build_direction({"family": family, "length": L, "width": W, "height": H, "fillet": 8}, tmp_path, name="x")
    assert time.time() - t < 10
    assert all(f.stat().st_size > 0 for f in files.values())
    facts = shape_facts(files["step"])
    assert len(facts["solids"]) == 2  # top + bottom shell
    assert facts["size"] == pytest.approx((L, W, H), abs=0.05)
    assert facts["volume_mm3"] > 0


def test_normalize_clamps():
    p = normalize({"family": 7, "length": 5000, "width": 1, "height": 0, "fillet": 999, "wall": 0.1})
    assert p["family"] == 0 and p["length"] == 400 and p["width"] == 15 and p["wall"] == 1.2
    assert p["fillet"] < p["width"] / 2 and p["height"] >= 4 * p["wall"]


def test_build_cache_hit_is_fast(tmp_path):
    params = {"family": 0, "length": 100, "width": 70, "height": 30}
    build_direction(params, tmp_path, name="a")
    t = time.time()
    build_direction(params, tmp_path, name="b")
    assert time.time() - t < 1.0


def _project(prompt="Magnetic rechargeable desk lamp, minimalist, sold €89"):
    return client.post("/projects", json={"mode": "idea", "prompt": prompt}).json()["id"]


def test_stages_2_and_3_live_without_key():
    pid = _project()
    runner.run_stage(pid, 1)
    design = runner.run_stage(pid, 2)
    assert design.fallback is False, design.fallback_reason
    DesignArtifact.model_validate(design.model_dump())
    assert len({d.cad_parameters["family"] for d in design.directions}) == 3
    for d in design.directions:
        assert client.get(d.glb_url).status_code == 200

    spec = runner.run_stage(pid, 3, {"direction_id": "d2"})
    assert spec.fallback is False, spec.fallback_reason
    SpecArtifact.model_validate(spec.model_dump())
    assert spec.direction_id == "d2"
    assert spec.overall_dimensions.length.label == "measured"
    assert spec.weight.label == "estimate" and "g/cm³" in spec.weight.source_or_assumption
    assert spec.bom and spec.electronics_blocks
    for f in spec.cad_files:
        r = client.get(f.url)
        assert r.status_code == 200 and len(r.content) == f.size_bytes


def test_stage_3_template_bom_for_unknown_example():
    pid = _project("Smart dog bowl that weighs food, Wi-Fi")
    runner.run_stage(pid, 1)
    assert runner.run_stage(pid, 2).fallback is False
    spec = runner.run_stage(pid, 3)
    assert spec.fallback is False, spec.fallback_reason
    assert spec.direction_id == "d1"


def test_files_route_prebuilt_on_fresh_db():
    client.post("/demo/reset")
    for pid in ("demo_desk_lamp", "demo_tracker_card"):
        for name in ("enclosure.glb", "enclosure.step", "enclosure.stl", "d1.glb", "d2.glb", "d3.glb"):
            r = client.get(f"/files/{pid}/{name}")
            assert r.status_code == 200 and len(r.content) > 0, (pid, name)
    assert client.get("/files/demo_desk_lamp/enclosure.glb").headers["content-type"] == "model/gltf-binary"


@pytest.mark.parametrize("url", [
    "/files/demo_desk_lamp/nope.glb",
    "/files/demo_desk_lamp/..%2F..%2Fdb.py",
    "/files/..%2Fcad/build.py",
    "/files/demo_desk_lamp/.hidden.glb",
    "/files/demo_desk_lamp/enclosure.py",
    "/files/%2Fetc/passwd",
])
def test_files_route_rejects_traversal(url):
    assert client.get(url).status_code == 404


def test_stage_3_no_pcb_for_mechanical_product(monkeypatch):
    """W7: a product with no electronic BOM line (espresso maker, prompt 5) gets no PCB part."""
    from api.cad import spec as S

    def mech_only(brief, p, material):
        lines = [S.BomLine(id=f"m{i}", part=n, category="mechanical", qty=1) for i, n in
                 enumerate(["Top shell", "Bottom shell", "Hand pump", "Brew chamber"], 1)]
        blocks = [S.ElectronicsBlock(id="b1", name="Hand pump", function="Pressure"),
                  S.ElectronicsBlock(id="b2", name="Brew chamber", function="Extraction")]
        return S.BomDraft(bom=lines, electronics_blocks=blocks, electronics_edges=[]), "llm:test"

    monkeypatch.setattr(S, "_bom_llm", mech_only)
    pid = _project("Portable espresso maker, manual pump, no electronics")
    runner.run_stage(pid, 1)
    runner.run_stage(pid, 2)
    spec = runner.run_stage(pid, 3)
    assert spec.fallback is False, spec.fallback_reason
    assert not [p for p in spec.parts if p.process_hint == "pcba"]


# --------------------------------------------------------------------------- W12: look + concept renders


def _materials(glb_bytes_or_path):
    from pygltflib import GLTF2

    g = GLTF2.load_from_bytes(glb_bytes_or_path) if isinstance(glb_bytes_or_path, bytes) else GLTF2.load(str(glb_bytes_or_path))
    return g, {m.name for m in g.materials}


def test_stage_2_full_assembly_glb_with_materials_and_no_render_without_key():
    pid = _project("Smart dog bowl that weighs food, Wi-Fi")
    runner.run_stage(pid, 1)
    design = runner.run_stage(pid, 2)
    assert design.fallback is False, design.fallback_reason
    assert all(d.render_url is None for d in design.directions)
    assert not any(a.id == "a2_render" for a in design.assumptions)
    for d in design.directions:
        assert "#" in d.finish  # colour callout
        g, names = _materials(client.get(d.glb_url).content)
        roles = {n.name.split(".")[0] for n in g.nodes if n.mesh is not None}
        assert {"body", "accent", "rubber", "port"} <= roles, roles  # shells + feet + USB-C (+ bowl/diffuser by brief)
        assert "TPE rubber" in names and all(p.material is not None for m in g.meshes for p in m.primitives)
    spec = runner.run_stage(pid, 3)
    g, names = _materials(client.get(f"/files/{pid}/enclosure.glb").content)
    assert len(g.materials) == 2 and len(shape_facts(Path(os.environ["FILES_DIR"]) / pid / "enclosure.step")["solids"]) == 2
    full, step, stl, enc = spec.cad_files
    assert (full.format, full.url, full.description) == ("glb", f"/files/{pid}/d1.glb", "Full product — materials")
    assert full.size_bytes == len(client.get(full.url).content)
    assert [f.format for f in (step, stl, enc)] == ["step", "stl", "glb"] and enc.url == f"/files/{pid}/enclosure.glb"
    assert all(f.description.startswith("Moulded parts (DFM)") for f in (step, stl, enc))
    assert enc.size_bytes == len(client.get(enc.url).content)
    dfm = runner.run_stage(pid, 4)  # DFM still measures the moulded STEP
    assert dfm.fallback is False, dfm.fallback_reason


def _fake_png() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1200, 900), (230, 228, 222)).save(buf, format="JPEG")
    return buf.getvalue()


def test_stage_2_renders_mocked(monkeypatch):
    monkeypatch.setenv("LLM_IMAGE_MAX_RENDERS", "3")  # these tests cover all three directions
    from api.cad import renders

    prompts = []
    monkeypatch.setattr(renders, "is_configured", lambda: True)
    monkeypatch.setattr(renders, "_call", lambda prompt, timeout: prompts.append(prompt) or _fake_png())
    pid = _project("Magnetic rechargeable desk lamp, minimalist")
    runner.run_stage(pid, 1)
    t = time.time()
    design = runner.run_stage(pid, 2)
    assert time.time() - t < 30
    assert design.fallback is False and len(prompts) == 3  # ≤ 3 images per run
    for d in design.directions:
        assert d.render_url == f"/files/{pid}/{d.id}.png"
        r = client.get(d.render_url)
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
        from PIL import Image
        import io
        assert Image.open(io.BytesIO(r.content)).size == (1024, 1024)
    assert any(a.id == "a2_render" and a.label == "estimate" and renders.RENDER_CAPTION in a.text for a in design.assumptions)
    p = prompts[0]
    assert "No text" in p and "no logos" in p and " mm" in p and "Colour:" in p


def test_features_follow_the_brief():
    from types import SimpleNamespace

    from api.cad.look import features_for

    bowl = features_for(SimpleNamespace(category="Pet", product_name="Smart dog bowl", one_liner="", key_features=[]))
    assert "bowl" in bowl and "feet" in bowl
    card = features_for(SimpleNamespace(category="ble_accessory", product_name="Tracker card", one_liner="", key_features=[]))
    assert "feet" not in card and "button" in card


def test_render_failure_retries_once_then_null(monkeypatch):
    monkeypatch.setenv("LLM_IMAGE_MAX_RENDERS", "3")  # these tests cover all three directions
    from api.cad import renders

    calls = []

    def boom(prompt, timeout):
        calls.append(timeout)
        assert timeout <= renders.TIMEOUT_S
        raise TimeoutError("slow model")

    monkeypatch.setattr(renders, "is_configured", lambda: True)
    monkeypatch.setattr(renders, "_call", boom)
    pid = _project("Smart plant pot with moisture sensor")
    runner.run_stage(pid, 1)
    design = runner.run_stage(pid, 2)
    assert design.fallback is False and all(d.render_url is None for d in design.directions)
    assert len(calls) == 6  # 3 directions × (try + 1 retry)


def test_prebuilt_renders_and_material_glbs():
    for pid in ("demo_desk_lamp", "demo_tracker_card"):
        for i in (1, 2, 3):
            for name in (f"d{i}.png", f"hero_d{i}.png"):  # AI concept render + Blender render of the CAD
                r = client.get(f"/files/{pid}/{name}")
                assert r.status_code == 200 and r.headers["content-type"] == "image/png", (pid, name)
            g, names = _materials(client.get(f"/files/{pid}/d{i}.glb").content)
            assert g.materials and all(p.material is not None for m in g.meshes for p in m.primitives), (pid, i)
    _, names = _materials(client.get("/files/demo_desk_lamp/d1.glb").content)
    assert {"anodised aluminium", "frosted PC diffuser (lit)", "TPE rubber"} <= names


def test_stage2_late_render_is_patched_in(monkeypatch):
    """W7 r: stage 2 answers after the inline budget; a render finishing later is written into the saved artifact."""
    monkeypatch.setenv("LLM_IMAGE_MAX_RENDERS", "3")  # these tests cover all three directions
    import time as _t

    from api.cad import directions as D

    def slow_render(pid, brief, d, out_dir, **kw):
        _t.sleep(4)
        return f"/files/{pid}/{d.id}.png"

    monkeypatch.setattr(D, "render_direction", slow_render)
    monkeypatch.setattr(D, "INLINE_RENDER_S", 0.0)
    pid = _project("Magnetic desk lamp")
    runner.run_stage(pid, 1)
    art = runner.run_stage(pid, 2)
    assert art.fallback is False and not any(d.render_url for d in art.directions)
    for _ in range(80):
        _t.sleep(0.1)
        saved = runner.get_artifact(pid, 2)
        if all(d.render_url for d in saved.directions):
            break
    assert [d.render_url for d in saved.directions] == [f"/files/{pid}/d{i}.png" for i in (1, 2, 3)]
    assert any(a.id == "a2_render" for a in saved.assumptions)


def test_stage2_auto_renders_first_direction_only_then_on_demand(monkeypatch):
    """W7d: LLM_IMAGE_MAX_RENDERS (default 1) auto-renders d1; POST /projects/{id}/stages/2/render renders d2 on demand."""
    from api.cad import directions as D

    calls = []

    def fake_render(pid, brief, d, out_dir, **kw):
        calls.append(d.id)
        return f"/files/{pid}/{d.id}.png"

    monkeypatch.setattr(D, "render_direction", fake_render)
    monkeypatch.delenv("LLM_IMAGE_MAX_RENDERS", raising=False)
    pid = _project("Magnetic desk lamp")
    runner.run_stage(pid, 1)
    art = runner.run_stage(pid, 2)
    assert calls == ["d1"] and [d.render_url is not None for d in art.directions] == [True, False, False]
    client = TestClient(app)
    r = client.post(f"/projects/{pid}/stages/2/render", params={"direction_id": "d2"})
    assert r.status_code == 200 and r.json()["artifact"]["directions"][1]["render_url"] == f"/files/{pid}/d2.png"
    assert runner.get_artifact(pid, 2).directions[1].render_url == f"/files/{pid}/d2.png"
    assert client.post(f"/projects/{pid}/stages/2/render", params={"direction_id": "d9"}).status_code == 404
    monkeypatch.setenv("LLM_IMAGE_MAX_RENDERS", "0")
    calls.clear()
    runner.run_stage(pid, 2)
    assert calls == []


def test_stage3_slow_bom_call_falls_back_to_template(monkeypatch):
    """W7d: the BOM LLM call is capped (BOM_TIMEOUT_S); past it stage 3 is still live with the example/template BOM."""
    import time as _t

    from api.cad import spec as S

    monkeypatch.setattr(S, "BOM_TIMEOUT_S", 0.3)
    monkeypatch.setattr(S, "_bom_llm", lambda *a, **k: _t.sleep(2))
    pid = _project("Smart dog bowl that weighs food, Wi-Fi")
    runner.run_stage(pid, 1)
    runner.run_stage(pid, 2)
    t = _t.monotonic()
    spec = runner.run_stage(pid, 3)
    assert spec.fallback is False and spec.bom and _t.monotonic() - t < 10
    assert any("LLM unavailable: StageTimeout" in a.text for a in spec.assumptions)
