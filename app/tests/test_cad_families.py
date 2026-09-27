"""W19 parametric product families: every family builds, exports STEP/STL/GLB with role materials, is measured,
stays fast, clamps absurd parameters, and its seed program runs unchanged in the codegen sandbox."""

import time

import pytest

from api.cad import families
from api.cad.codegen.sandbox import check_code, run_code

VARIANTS = [("board", "surf"), ("board", "kite"), ("furniture", "changing_table"), ("furniture", "activity_table"),
            ("stick_vacuum", None), ("home_robot", None), ("irrigation", None), ("solar_array", None)]
# (min, max) of the largest overall extent in mm: a recognisable real-world size
SIZE = {"board": (1100, 3300), "furniture": (500, 1700), "stick_vacuum": (900, 1400), "home_robot": (500, 2000),
        "irrigation": (300, 1500), "solar_array": (4000, 30000)}


@pytest.mark.parametrize("name,variant", VARIANTS)
def test_family_builds_exports_and_measures(tmp_path, name, variant):
    p = families.params_for(name, variant)
    t = time.monotonic()
    out = families.export_family(name, tmp_path, f"{name}_{variant}", p)
    assert time.monotonic() - t < 5.0
    for k in ("step", "stl", "glb"):
        assert out["files"][k].exists() and out["files"][k].stat().st_size > 1000
    m = out["measured"]
    assert m["volume_mm3"] > 0 and all(r["volume_mm3"] > 0 for r in m["parts"])
    lo, hi = SIZE[name]
    assert lo <= max(m["bbox_mm"]) <= hi
    roles = {r["role"] for r in m["parts"]}
    assert roles <= set(families.ROLES) and len(m["parts"]) >= 4
    from pygltflib import GLTF2

    g = GLTF2.load(str(out["files"]["glb"]))
    assert len(g.materials) >= 2 and {n.name.split(".")[0] for n in g.nodes if n.mesh is not None} <= set(families.ROLES)


@pytest.mark.parametrize("name", families.names())
def test_params_are_clamped(name):
    m = families.module(name)
    fields = m.Params.__dataclass_fields__
    wild = {k: 1e6 for k in fields}
    p = families.params_for(name, **wild)
    tiny = families.params_for(name, **{k: -1e6 for k in fields})
    for k in fields:
        assert -1e6 < p[k] < 1e6 and -1e6 < tiny[k] < 1e6
    _, parts = families.build_family(name, wild)  # absurd input still builds a plausible product
    assert parts


def test_family_variants_differ():
    surf = families.params_for("board", "surf")
    kite = families.params_for("board", "kite")
    assert kite["twin_tip"] == 1.0 and surf["twin_tip"] == 0.0 and kite["length"] < surf["length"]


@pytest.mark.parametrize("name", families.names())
def test_seed_code_runs_in_sandbox(name):
    code = families.seed_code_for(name)
    assert check_code(code) == []
    res = run_code(code, timeout_s=25)
    assert res["ok"], res.get("error")
    _, parts = families.build_family(name)
    direct = families.measure_parts(parts)["bbox_mm"]
    assert [round(v) for v in res["bbox_mm"]] == [round(v) for v in direct]  # same geometry in and out of the sandbox
