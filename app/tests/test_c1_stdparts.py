"""C1 — standard parts + DFM detail behind CAD_DETAIL_LEVEL (basic | pro).

basic: byte-for-byte the pre-C1 families (golden recorded from the HEAD before C1: geometry, labels, seed code).
pro: every family builds < 5 s, GLB < 3 MB, fasteners are separate named nodes counted in the BOM, bosses / holes
match the cited tables, the pro seed code still runs in the codegen sandbox, solid-product DFM gains no new issue."""

import hashlib
import json
import time
from pathlib import Path

import pytest

from api.cad import families, glb
from api.cad import stdparts as S
from api.cad.stdparts import bom, tables as T
from contracts.artifacts import PartMeta

GOLDEN = json.loads((Path(__file__).parent / "golden" / "c1_basic_families.json").read_text())
PRO_FAMILIES = ["drone", "stick_vacuum", "home_robot", "camera", "smartphone", "irrigation", "furniture", "board"]
ENCLOSURES = {  # lamp base (demo_desk_lamp), tracker card (small slab preset), wearable pod (W17 default)
    "lamp": dict(family=0, length=120, width=120, height=22, fillet=20, edge_fillet=3, wall=2.2),
    "tracker": dict(family=2, length=86, width=54, height=9, fillet=5, edge_fillet=1.5, wall=1.5),
    "pod": dict(family=3, length=44, width=30, height=10, fillet=9, edge_fillet=2, wall=1.5, draft_deg=1.5, split_ratio=0.6),
}


@pytest.fixture
def pro(monkeypatch):
    monkeypatch.setenv("CAD_DETAIL_LEVEL", "pro")


# --------------------------------------------------------------------------- basic unchanged


@pytest.mark.parametrize("key", sorted(GOLDEN))
def test_basic_is_unchanged(monkeypatch, key):
    monkeypatch.setenv("CAD_DETAIL_LEVEL", "basic")  # C5: pro is the default; basic stays the pre-C1 CAD
    name, variant = key.split(":")
    variant = None if variant == "None" else variant
    p = families.params_for(name, variant)
    _, parts = families.build_family(name, p)
    m = families.measure_parts(parts)
    g = GOLDEN[key]
    assert [r["label"] for r in m["parts"]] == g["labels"]
    assert m["bbox_mm"] == g["bbox_mm"] and m["volume_mm3"] == g["volume_mm3"]
    assert hashlib.sha1(families.seed_code_for(name, p).encode()).hexdigest() == g["seed_sha"]
    assert not any(getattr(q, "std_meta", None) for q in parts)


def test_unknown_level_is_basic(monkeypatch):
    monkeypatch.setenv("CAD_DETAIL_LEVEL", "ultra")
    assert S.detail_level() == "basic"


# --------------------------------------------------------------------------- pro families


@pytest.mark.parametrize("name", PRO_FAMILIES)
def test_pro_family_builds_fast_small_and_counts_fasteners(pro, tmp_path, name):
    t = time.monotonic()
    out = families.export_family(name, tmp_path, name)
    assert time.monotonic() - t < 5.0
    st = glb.stats(out["files"]["glb"])
    assert st["bytes"] < 3 * 1024 * 1024 and st["finished"]
    _, parts = families.build_family(name)
    hw = [q for q in parts if (getattr(q, "std_meta", None) or {}).get("bom")]
    assert hw, "pro adds standard parts"
    lines = bom.bom_lines(parts)
    assert sum(r["qty"] for r in lines) == len(hw)  # every placed standard part is one BOM unit
    facts = glb.root_extras(out["files"]["glb"])["stdparts"]
    all_nodes = glb.read_parts(out["files"]["glb"])
    for e in all_nodes:  # node extras stay valid PartMeta (the contract forbids extra keys)
        PartMeta.model_validate(e)
    nodes = [e for e in all_nodes if e["part_id"] in facts]
    by_id = {r["id"]: r for r in lines}
    linked = [e for e in nodes if e.get("bom_item_id")]
    assert {e["bom_item_id"] for e in linked} == set(by_id)  # each BOM line is a named node (and back)
    for e in linked:
        r = by_id[e["bom_item_id"]]
        f = facts[e["part_id"]]
        assert f["count"] == r["qty"] and e["unit_price"]["value"] == r["unit_price_usd"] and e["unit_price"]["label"] == "estimate"
        assert f["standard"] and e["package"] and e["layer_id"] == "fasteners" and e["role"] in ("fastener", "component", "other")
    items = bom.bom_items(lines)
    assert all(str(getattr(i.category, "value", i.category)) == "mechanical" and str(getattr(i.unit_cost_est.label, "value", i.unit_cost_est.label)) == "estimate" and i.qty >= 1 for i in items)
    basic = GOLDEN[f"{name}:None"]
    assert len(parts) > len(basic["labels"])


def test_pro_seed_code_runs_in_sandbox(pro):
    from api.cad.codegen.sandbox import check_code, run_code

    code = families.seed_code_for("drone")
    assert "from api.cad.stdparts import" in code and check_code(code) == []
    res = run_code(code, timeout_s=40)
    assert res["ok"], res.get("error")
    assert sum(1 for r in res["parts"] if r["role"] in ("steel", "brass")) >= 40


@pytest.mark.parametrize("line", [
    "from api.cad.stdparts import detail_level", "from api.cad.stdparts import *", "import api.cad.stdparts",
    "from api.cad import stdparts", "from api.cad.stdparts.level import is_pro", "from api.cad.stdparts import bom",
])
def test_sandbox_allows_only_named_helpers(line):
    from api.cad.codegen.sandbox import check_code

    assert check_code(f"{line}\ndef build():\n    return []\n")


def test_sandbox_runner_rechecks_names(tmp_path):
    """The runner's import guard refuses a non-helper name even if the static check were bypassed."""
    import subprocess
    import sys

    from api.cad.codegen import sandbox

    code = ("def build():\n    from api.cad.stdparts import screw\n    return [screw('M3', 8).part]\n")
    (tmp_path / "model.py").write_text(code)
    subprocess.run([sys.executable, "-I", "-B", str(sandbox.RUNNER), "model.py", str(tmp_path)], cwd=tmp_path, check=True,
                   timeout=60)
    assert json.loads((tmp_path / "result.json").read_text())["ok"]
    bad = "def build():\n    from api.cad.stdparts import is_pro\n    return []\n"
    (tmp_path / "model.py").write_text(bad)
    subprocess.run([sys.executable, "-I", "-B", str(sandbox.RUNNER), "model.py", str(tmp_path)], cwd=tmp_path, check=True,
                   timeout=60)
    res = json.loads((tmp_path / "result.json").read_text())
    assert not res["ok"] and "not allowed" in res["error"]


@pytest.mark.parametrize("name", ["board", "furniture"])
def test_solid_dfm_still_passes(pro, name):
    from api.cad.family_mode import solid_issues

    _, parts = families.build_family(name)
    m = families.measure_parts(parts)
    issues = solid_issues(name, m)
    assert all(str(getattr(i.severity, "value", i.severity)) != "major" for i in issues)


def test_moulded_dfm_input_unchanged(pro, tmp_path):
    """Stage 4 reads the W2 enclosure STEP of shell products: pro detail does not touch it."""
    from api.cad.build import build_shape

    _, (bottom, top) = build_shape(ENCLOSURES["lamp"])
    assert not getattr(bottom, "std_meta", None) and not getattr(top, "std_meta", None)


# --------------------------------------------------------------------------- enclosures (lamp / tracker / pod)


@pytest.mark.parametrize("key", sorted(ENCLOSURES))
def test_enclosure_pro_details(key, tmp_path):
    from api.cad.stdparts.enclosure import joint_for, pro_viewer_parts

    t = time.monotonic()
    parts = pro_viewer_parts(ENCLOSURES[key], {"button", "led", "feet"})
    out = families.export_parts(parts, tmp_path / key, families.family_look("#4F6F95"))
    assert time.monotonic() - t < 5.0 and glb.stats(out["glb"])["bytes"] < 3 * 1024 * 1024
    facts = glb.root_extras(out["glb"])["stdparts"]
    for e in glb.read_parts(out["glb"]):
        PartMeta.model_validate(e)
    nodes = {f["name"]: f for f in facts.values()}
    if joint_for(ENCLOSURES[key]) == "weld":
        (lip,) = nodes.values()
        assert lip["dfm"]["height_mm"] == pytest.approx(lip["dfm"]["base_mm"] / 2, abs=0.02)  # 90° energy director
        assert not any(k.startswith("M") for k in nodes)  # screwless
    else:
        n = 2 if key == "pod" else 4
        screws = [f for k, f in nodes.items() if "screw" in k]
        inserts = [f for k, f in nodes.items() if "insert" in k]
        assert screws[0]["count"] == n and inserts[0]["count"] == n
        boss = nodes["Screw bosses"]
        d = S.boss_dims(inserts[0]["size"], "insert")
        assert boss["dfm"]["od_mm"] == d["od"] and boss["dfm"]["hole_mm"] == d["hole"]


# --------------------------------------------------------------------------- dimensions per the tables


@pytest.mark.parametrize("size", ["M2", "M2.5", "M3", "M4", "M5"])
def test_boss_sized_per_table(size):
    hole = T.INSERT_HEATSET[size][2]
    b = S.screw_boss(size, 3.0, 2.0, "insert")
    f = b.std_meta["dfm"]
    assert f["hole_mm"] == hole and f["od_mm"] == pytest.approx(2 * hole)  # OD = 2 × hole (Covestro)
    assert f["height_mm"] >= T.INSERT_HEATSET[size][1] + 0.5  # the insert fits
    assert b.bounding_box().size.X == pytest.approx(2 * hole, abs=0.01)
    pt = S.screw_boss(size, 10.0, 2.0, "pt").std_meta["dfm"]
    assert pt["hole_mm"] == pytest.approx(0.8 * T.NOMINAL[size]) and pt["od_mm"] == pytest.approx(2 * T.NOMINAL[size])


@pytest.mark.parametrize("size", list(T.CLEARANCE_ISO273))
def test_holes_per_iso(size):
    for i, fit in enumerate(("fine", "medium", "coarse")):
        h = S.clearance_hole(size, 6, fit)
        assert h.std_meta["dfm"]["hole_mm"] == T.CLEARANCE_ISO273[size][i]
        assert h.bounding_box().size.X == pytest.approx(T.CLEARANCE_ISO273[size][i], abs=0.01)
    assert S.tap_hole(size).std_meta["dfm"]["hole_mm"] == pytest.approx(T.NOMINAL[size] - T.PITCH[size], abs=0.06)


@pytest.mark.parametrize("size", ["M2", "M3", "M5"])
def test_fastener_dimensions(size):
    dk, k, _ = T.SOCKET_ISO4762[size]
    sc = S.screw(size, 10, "socket").part.bounding_box()
    assert sc.size.X == pytest.approx(dk, abs=0.01) and sc.size.Z == pytest.approx(10 + k, abs=0.01)
    csk = S.screw(size, 10, "countersunk").part.bounding_box()
    assert csk.size.Z == pytest.approx(10, abs=0.01) and csk.max.Z == pytest.approx(0, abs=0.01)  # ISO length incl. head
    m, s = T.NUT_ISO4032[size]
    nb = S.hex_nut(size).part.bounding_box()
    assert nb.size.Y == pytest.approx(s, abs=0.01) and nb.size.Z == pytest.approx(m, abs=0.01)
    ins = S.heat_set_insert(size).part.bounding_box()
    assert ins.size.X == pytest.approx(T.INSERT_HEATSET[size][0], abs=0.01)


def test_bearing_gear_rib_snap_rules():
    b = S.bearing("608").part.bounding_box()
    assert (round(b.size.X, 2), round(b.size.Z, 2)) == (22.0, 7.0)
    g = S.spur_gear(1.0, 20, 5, 3)
    assert g.meta["pitch_d_mm"] == 20 and g.part.bounding_box().size.X == pytest.approx(22.0, abs=0.05)  # tip Ø = m(z+2)
    r = S.rib(40, 20, 2.5)
    assert r.std_meta["dfm"]["thickness_mm"] == pytest.approx(1.5) and r.std_meta["dfm"]["height_mm"] == 7.5
    s = S.snap_fit(10, 1.2, 5).std_meta["dfm"]
    assert s["ratio_L_h"] >= 5 and s["deflection_mm"] == pytest.approx(0.67 * 0.025 * 100 / 1.2, rel=1e-3)
    gg = S.gasket_groove(100, 60, 10, 2).std_meta["dfm"]
    assert gg["squeeze"] == pytest.approx(0.25)


def test_screw_joint_lengths_are_preferred_and_engage():
    parts = S.screw_joint("M3", (0, 0, 10), (0, 0, -1), grip=2.0, into="insert")
    sc = parts[0].std_meta
    assert sc["length_mm"] in S.joints.STD_LENGTHS and sc["length_mm"] >= 2.0 + T.INSERT_HEATSET["M3"][1] * 0.9


def test_bom_merge_skips_template_rows(pro):
    from contracts.artifacts import BOMCategory, BOMItem

    lines = bom.family_lines("board")
    kinds = {r["kind"] for r in lines}
    assert kinds == {"fin_box", "leash_plug"}
    tmpl = [BOMItem(id="m1", part="Fin boxes (FCS-type plugs)", category=BOMCategory.mechanical, qty=3),
            BOMItem(id="m2", part="Leash plug", category=BOMCategory.mechanical, qty=1)]
    assert len(bom.merge_into(tmpl, lines)) == 2  # no double count
    drone = bom.merge_into([], bom.family_lines("drone"))
    assert sum(i.qty for i in drone) >= 40


def test_costs_keep_hardware_estimates():
    from api.costs.lcsc import match_bom

    items = bom.bom_items(bom.family_lines("home_robot"))
    before = {i.id: i.unit_cost_est.value for i in items}
    out = match_bom(items)
    assert all(i.unit_cost_est is not None and i.unit_cost_est.value == pytest.approx(before[i.id]) for i in out)
