"""W29 — finished GLBs (named parts, PartMeta extras, KHR materials, smooth normals), /parts, structured part edits,
/anatomy. Offline: showcase fixtures + prebuilt files, no LLM."""

from __future__ import annotations

import math
import re
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pygltflib import GLTF2

from api import auth
from api.cad import glb
from api.cad.build import PREBUILT_DIR
from api.main import app
from contracts.artifacts import ANATOMY_LABEL, PartMeta, ProjectAnatomy, ProjectParts

client = TestClient(app)
MB3 = 3 * 1024 * 1024


@pytest.fixture(scope="module", autouse=True)
def _seed():
    assert client.post("/demo/reset").status_code == 200
    yield


def _wait(pid: str, n: int, timeout: float = 60.0) -> dict:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        v = client.get(f"/projects/{pid}/versions/{n}").json()
        if v["status"] != "running":
            return v
        time.sleep(0.1)
    raise AssertionError(f"version {n} still running")


def _parts(pid: str) -> dict:
    r = client.get(f"/projects/{pid}/parts")
    assert r.status_code == 200, r.text
    return r.json()


# --------------------------------------------------------------------------- GLB conventions


def _check_glb(path: Path) -> GLTF2:
    g = GLTF2.load(str(path))
    assert glb.is_finished(g), path
    assert path.stat().st_size < MB3, (path, path.stat().st_size)
    root = g.nodes[g.scenes[g.scene or 0].nodes[0]]
    assert root.name == "product" and root.extras.get("units") == "m" and root.extras.get("up") == "+Y"
    ids = set()
    for c in root.children:
        node = g.nodes[c]
        assert node.name == node.extras["part_id"], node.name
        PartMeta.model_validate(node.extras)
        ids.add(node.name)
        assert node.children, node.name
        for k in node.children:
            child = g.nodes[k]
            assert child.mesh is not None and re.match(r"^[a-z_]+\.\d+", child.name), child.name
            for prim in g.meshes[child.mesh].primitives:
                assert prim.attributes.NORMAL is not None and prim.attributes.TEXCOORD_0 is None
                assert prim.material is not None
    assert len(ids) == len(root.children)
    used = set(g.extensionsUsed or [])
    for m in g.materials:
        assert set((m.extensions or {}).keys()) <= used
    return g


@pytest.mark.parametrize("rel", ["showcase_whoop_kitesurf/model_v2.glb", "showcase_drone_follow/model_v1.glb",
                                 "showcase_stick_vacuum/model_v2.glb", "showcase_surfboard_beginner/model_v2.glb",
                                 "demo_desk_lamp/d1.glb", "showcase_whoop_kitesurf/anatomy_v4.glb"])
def test_glb_conventions(rel):
    g = _check_glb(PREBUILT_DIR / rel)
    used = set(g.extensionsUsed or [])
    assert used & {"KHR_materials_clearcoat", "KHR_materials_sheen", "KHR_materials_transmission", "KHR_materials_specular"}


def test_all_prebuilt_glbs_finished_and_small():
    files = [f for f in PREBUILT_DIR.glob("*/*.glb")]
    assert len(files) > 100
    for f in files:
        assert f.stat().st_size < MB3, f
        assert glb.is_finished(GLTF2.load(str(f))), f


def test_whoop_units_up_axis_and_materials():
    parts = {p["part_id"]: p for p in glb.read_parts(PREBUILT_DIR / "showcase_whoop_kitesurf/model_v2.glb")}
    top, strap = parts["top_shell"], parts["strap"]
    assert 40 < top["measured_bbox_mm"][0] < 48 and 25 < top["measured_bbox_mm"][2] < 35  # mm in extras, pod 44 × 30
    assert top["centroid_mm"][1] > strap["centroid_mm"][1]  # +Y up: the pod sits on top of the strap loop
    g = GLTF2.load(str(PREBUILT_DIR / "showcase_whoop_kitesurf/model_v2.glb"))
    acc = [g.accessors[p.attributes.POSITION] for m in g.meshes for p in m.primitives]
    assert max(max(a.max) for a in acc) < 0.1  # metres
    ext = {k for m in g.materials for k in (m.extensions or {})}
    assert {"KHR_materials_sheen", "KHR_materials_transmission", "KHR_materials_ior", "KHR_materials_clearcoat"} <= ext


def test_metal_roughness_by_finish():
    look = {"metal": {"name": "anodised aluminium", "baseColorFactor": [0.8, 0.8, 0.8, 1], "metallicFactor": 1.0, "roughnessFactor": 0.3},
            "_meta": {"finish": "Brushed"}}
    assert glb.material_for("metal", look)["roughnessFactor"] == pytest.approx(0.35)
    m = glb.material_for("body", {"body": {"name": "b", "baseColorFactor": [1, 1, 1, 1], "metallicFactor": 1.0, "roughnessFactor": 0.3},
                                  "_meta": {"finish": "polished", "material_text": "Aluminium"}})
    assert m["metallicFactor"] == 1.0 and m["roughnessFactor"] == pytest.approx(0.1)
    soft = glb.material_for("body", {"body": {"name": "b", "baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0.0, "roughnessFactor": 0.5},
                                     "_meta": {"finish": "Soft-touch paint"}})
    assert 0.7 <= soft["roughnessFactor"] <= 0.8


def test_smooth_normals_crease_angle():
    pos = np.array([[0, 0, 0], [0, 0, 0], [1, 0, 0], [1, 0, 0]], float)
    a10 = [0, math.sin(math.radians(10)), math.cos(math.radians(10))]
    n = np.array([[0, 0, 1], a10, [0, 0, 1], [0, 1, 0]], float)
    out = glb.smooth_normals(pos, n)
    assert np.allclose(out[0], out[1])  # 10° seam → averaged (smooth)
    assert np.allclose(out[2], [0, 0, 1]) and np.allclose(out[3], [0, 1, 0])  # 90° edge → kept sharp


# --------------------------------------------------------------------------- /parts


@pytest.mark.parametrize("pid", ["demo_whoop_kitesurf", "demo_drone_follow", "demo_stick_vacuum"])
def test_parts_route(pid):
    j = _parts(pid)
    ProjectParts.model_validate(j)
    v = client.get(f"/projects/{pid}/versions").json()
    cur = next(x for x in v if x["is_current"])
    assert j["version"] == cur["n"] and j["glb_url"] == cur["preview"]["glb_url"]
    assert len(j["parts"]) >= 5 and all(p["label"] == "measured" for p in j["parts"])
    eds = [e for p in j["parts"] for e in p["editable"]]
    assert eds and all(e["min"] <= e["value"] <= e["max"] and e["step"] > 0 for e in eds)
    assert any(p["bom_item_id"] for p in j["parts"])
    from api.cad.files import resolve_file

    g = GLTF2.load(str(resolve_file(pid, j["glb_url"].rsplit("/", 1)[-1])))
    names = {n.name for n in g.nodes}
    assert {p["part_id"] for p in j["parts"]} <= names


def test_parts_404():
    assert client.get("/projects/nope/parts").status_code == 404
    assert client.get("/projects/demo_whoop_kitesurf/parts?version=99").status_code == 404


def test_drone_props_are_separate_parts():
    j = _parts("demo_drone_follow")
    props = [p for p in j["parts"] if p["role"] == "prop"]
    assert len(props) >= 4 and len({p["part_id"] for p in props}) == len(props)


# --------------------------------------------------------------------------- /edit


def test_edit_colour_material_param_whoop():
    pid = "demo_whoop_kitesurf"
    r = client.post(f"/projects/{pid}/parts/strap/edit", json={"colour_hex": "#9DB09A"})
    assert r.status_code == 202, r.text
    t0 = time.monotonic()
    v = _wait(pid, r.json()["version"])
    assert time.monotonic() - t0 < 2.0
    assert v["status"] == "done" and v["summary"] == "Strap colour → Sage (#9DB09A)" and v["is_current"]
    j = _parts(pid)
    assert next(p for p in j["parts"] if p["part_id"] == "strap")["colour_hex"] == "#9DB09A"
    assert j["glb_url"].endswith(f"v{v['n']}_ai.glb")
    before = client.get(f"/projects/{pid}/stages/5").json()["artifact"]

    r = client.post(f"/projects/{pid}/parts/top_shell/edit", json={"material": "aluminium"})
    v = _wait(pid, r.json()["version"])
    assert v["status"] == "done", v
    assert re.match(r"Top shell material PC/ABS → Aluminium 6063-T5 \(\+\$\d+\.\d\d/unit, Estimate\)", v["summary"]), v["summary"]
    after = client.get(f"/projects/{pid}/stages/5").json()["artifact"]
    assert after["tiers"][0]["unit_cost"]["value"] > before["tiers"][0]["unit_cost"]["value"]
    assert next(p for p in _parts(pid)["parts"] if p["part_id"] == "strap")["colour_hex"] == "#9DB09A"  # override kept

    spec = next(e for p in _parts(pid)["parts"] if p["part_id"] == "top_shell" for e in p["editable"] if e["param"] == "pod_thickness")
    old = spec["value"]
    t0 = time.monotonic()
    r = client.post(f"/projects/{pid}/parts/top_shell/edit", json={"param": "pod_thickness", "value": old + 1})
    v = _wait(pid, r.json()["version"])
    assert time.monotonic() - t0 < 8.0
    assert v["status"] == "done", v
    assert v["summary"].startswith(f"Pod thickness {old:.1f} → {old + 1:.1f} mm (Measured)")
    assert any(c["label_kind"] == "measured" and c["area"] == "dimensions" for c in v["changes"])
    h = client.get(f"/projects/{pid}/stages/3").json()["artifact"]["overall_dimensions"]["height"]
    assert h["label"] == "measured" and h["value"] == pytest.approx(old + 1, abs=0.05)
    j = _parts(pid)
    top = next(p for p in j["parts"] if p["part_id"] == "top_shell")
    assert next(e for e in top["editable"] if e["param"] == "pod_thickness")["value"] == pytest.approx(old + 1)
    assert v["preview"]["code_url"] and client.get(v["preview"]["code_url"]).status_code == 200
    assert f"\"pod_thickness\": {old + 1}" in client.get(v["preview"]["code_url"]).text
    vs = client.get(f"/projects/{pid}/versions").json()
    assert [x["n"] for x in vs][-3:] == [v["n"] - 2, v["n"] - 1, v["n"]]


def test_edit_param_vacuum_bin():
    pid = "demo_stick_vacuum"
    j = _parts(pid)
    part, spec = next((p, e) for p in j["parts"] for e in p["editable"] if e["param"] == "bin_diameter")
    new = min(spec["max"], spec["value"] + 8)
    r = client.post(f"/projects/{pid}/parts/{part['part_id']}/edit", json={"param": "bin_diameter", "value": new})
    assert r.status_code == 202
    v = _wait(pid, r.json()["version"])
    assert v["status"] == "done", v
    assert v["summary"].startswith(f"Bin diameter {spec['value']:.1f} → {new:.1f} mm (Measured)")
    fam = client.get(f"/projects/{pid}/stages/2").json()["artifact"]
    d = next(x for x in fam["directions"] if x["id"] == fam["chosen_direction_id"])
    assert d["cad_parameters"]["fp_bin_diameter"] == pytest.approx(new)
    after = next(p for p in _parts(pid)["parts"] if p["part_id"] == part["part_id"])
    assert after["measured_bbox_mm"][0] > part["measured_bbox_mm"][0]


def test_edit_validation():
    pid = "demo_drone_follow"
    j = _parts(pid)
    p, e = next((p, e) for p in j["parts"] for e in p["editable"])
    r = client.post(f"/projects/{pid}/parts/{p['part_id']}/edit", json={"param": e["param"], "value": e["max"] * 10 + 1})
    assert r.status_code == 422 and "outside" in r.json()["detail"]
    assert client.post(f"/projects/{pid}/parts/{p['part_id']}/edit", json={}).status_code == 422
    assert client.post(f"/projects/{pid}/parts/{p['part_id']}/edit", json={"colour_hex": "pink"}).status_code == 422
    assert client.post(f"/projects/{pid}/parts/{p['part_id']}/edit", json={"material": "unobtainium"}).status_code == 422
    assert client.post(f"/projects/{pid}/parts/nope/edit", json={"colour_hex": "#112233"}).status_code == 404
    assert client.post("/projects/nope/parts/x/edit", json={"colour_hex": "#112233"}).status_code == 404


def test_edit_guards(monkeypatch):
    monkeypatch.setenv("DEMO_READONLY", "1")
    r = client.post("/projects/demo_whoop_kitesurf/parts/strap/edit", json={"colour_hex": "#9DB09A"})
    assert r.status_code == 403
    monkeypatch.setenv("DEMO_READONLY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-used")  # the Studio bucket only counts with a key
    monkeypatch.setenv("STUDIO_RATE_LIMIT_PER_DAY", "1")
    auth.reset_rate_limits()
    try:
        assert client.post("/projects/nope/parts/x/edit", json={"colour_hex": "#112233"}).status_code == 404  # counted
        r = client.post("/projects/nope/parts/x/edit", json={"colour_hex": "#112233"})
        assert r.status_code == 429 and "Studio limit" in r.json()["detail"]
    finally:
        auth.reset_rate_limits()


# --------------------------------------------------------------------------- /anatomy


def _anatomy(pid: str) -> dict:
    r = client.get(f"/projects/{pid}/anatomy")
    assert r.status_code == 200, r.text
    j = r.json()
    ProjectAnatomy.model_validate(j)
    assert j["label"] == ANATOMY_LABEL == "Illustrative internal layout — not a routed PCB"
    ids = {p["part_id"] for p in j["parts"]}
    for L in j["layers"]:
        assert np.linalg.norm(L["explode_vector"]) == pytest.approx(1.0, abs=1e-3)
        assert L["parts"] and set(L["parts"]) <= ids and L["explode_distance_mm"] >= 0
    layer_ids = {L["id"] for L in j["layers"]}
    assert all(p["layer_id"] in layer_ids for p in j["parts"])
    assert 5 <= len(j["steps"]) <= 7
    for s in j["steps"]:
        assert set(s["layers_exploded"]) <= layer_ids and set(s["focus_parts"]) <= ids
        assert re.match(r"^\d\d · ", s["kicker"]) and s["caption"] and len(s["camera"]["position_mm"]) == 3
    from api.cad.files import resolve_file

    g = _check_glb(resolve_file(pid, j["glb_url"].rsplit("/", 1)[-1]))
    assert {n.name for n in g.nodes} >= ids
    return j


def test_anatomy_whoop():
    j = _anatomy("demo_whoop_kitesurf")
    assert j["kind"] == "electronics"
    kickers = [s["kicker"] for s in j["steps"]]
    assert kickers[0] == "01 · The band" and kickers[1] == "02 · Top shell lifts" and kickers[-1].endswith("Back together")
    assert any(k.startswith("04 · The sensor stack — MAX30102") for k in kickers)
    caps = " ".join(s["caption"] for s in j["steps"])
    assert "MAX30102" in caps and "C6454833" in caps and "(Sourced)" in caps and "Li-po" in caps and "(Estimate)" in caps
    internals = [p for p in j["parts"] if p["label"] == "estimate"]
    assert any(p["role"] == "pcb" for p in internals) and any(p["role"] == "battery" for p in internals)
    ppg = next(p for p in internals if "MAX30102" in p["name"])
    assert ppg["package"] == "OESIP-14" and sorted(ppg["measured_bbox_mm"]) == pytest.approx(sorted([5.6, 3.3, 1.55]), abs=0.05)
    for p in internals:
        if p["bom_item_id"] and p["role"] in ("component", "connector"):
            assert p["package"] or p["measured_bbox_mm"], p


def test_anatomy_drone_vacuum_surfboard():
    d = _anatomy("demo_drone_follow")
    assert any(p["role"] == "cable" for p in d["parts"]) and any("ESC" in p["name"] for p in d["parts"])
    v = _anatomy("demo_stick_vacuum")
    cells = [p for p in v["parts"] if p["name"].startswith("18650 cell")]
    assert len(cells) == 6 and "6 × 18650" in " ".join(s["caption"] for s in v["steps"])
    assert any(p["role"] == "motor" and p["label"] == "estimate" for p in v["parts"])
    b = _anatomy("demo_surfboard_beginner")
    assert b["kind"] == "construction"
    names = " ".join(p["name"] for p in b["parts"])
    for word in ("foam core", "Stringer", "laminate", "Fin box", "Leash plug", "Traction pad"):
        assert word.lower() in names.lower(), word
    assert not any(p["role"] == "pcb" for p in b["parts"])


@pytest.mark.parametrize("pid", ["demo_minimal_phone", "demo_instant_camera", "demo_irrigation_biarritz", "demo_home_robot",
                                 "demo_changing_table", "demo_desk_lamp", "demo_tracker_card", "demo_hair_dryer"])
def test_anatomy_other_families(pid):
    j = _anatomy(pid)
    assert j["parts"] and j["layers"]


def test_package_table():
    from api.cad.anatomy.packages import battery_body, package_size

    assert package_size("QFN-48(7x7)") == (7.0, 7.0, 0.9)
    assert package_size("LGA14-(2.5x3)")[:2] == (2.5, 3.0)
    assert package_size("SOT-23-5") == (2.9, 1.6, 1.1)
    assert package_size("0402") == (1.0, 0.5, 0.35)
    b = battery_body("LiPo battery, 3.7 V, 190 mAh")
    assert b.kind == "battery" and b.extras["volume_cm3"] == pytest.approx(0.19 * 3.7 / 400 * 1000, rel=1e-3)
    c = battery_body("21.6 V (6S) rechargeable Li-ion battery pack")
    assert c.shape == "cyl" and c.qty == 6
