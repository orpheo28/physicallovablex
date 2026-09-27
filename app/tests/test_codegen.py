"""W19 text-to-CAD engine: sandbox policy + isolation, self-repair loop, edit mode, fallbacks, classifier, code route.
The LLM is always mocked here (no key in the test session)."""

import json
import os

import pytest

from api.cad.codegen import LABEL, check_code, classify, generate_cad, refine_cad, run_code, seed_for
from api.cad.codegen.engine import check_dims, extract_code, target_dims

GOOD = '''import math
from build123d import *

P = {"length": 120.0, "width": 80.0, "height": 40.0}


def build():
    body = Box(P["length"], P["width"], P["height"], align=(Align.CENTER, Align.CENTER, Align.MIN))
    body.label = "body.1"
    knob = Pos(0, 0, P["height"]) * Cylinder(10, 6)
    knob.label = "button.1"
    return [body, knob]
'''


def fence(code: str) -> str:
    return f"Here you go:\n```python\n{code}```\n- note"


class FakeLLM:
    """Scripted replies; records every prompt."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts: list[str] = []

    def __call__(self, prompt: str, system: str) -> str:
        self.prompts.append(prompt)
        return self.replies.pop(0)


# --------------------------------------------------------------------------- sandbox policy


@pytest.mark.parametrize("snippet,needle", [
    ("import os\n", "import 'os'"),
    ("import subprocess\n", "import 'subprocess'"),
    ("from pathlib import Path\n", "pathlib"),
    ("x = open('/etc/passwd').read()\n", "'open'"),
    ("eval('1+1')\n", "'eval'"),
    ("exec('x=1')\n", "'exec'"),
    ("__import__('os')\n", "'__import__'"),
    ("y = getattr(Box, 'x')\n", "'getattr'"),
    ("z = Box.__class__\n", "'__class__'"),
    ("z = (1).__class__.__mro__\n", "'__mro__'"),
    ("z = Box(1, 1, 1)._dim\n", "'_dim'"),
    ("export_step(Box(1, 1, 1), '/tmp/x.step')\n", "'export_step'"),
    ("s = '{0.__class__}'.format(1)\n", "'format'"),
    ("import build123d\nbuild123d.exporters3d.os.system('id')\n", "'os'"),
])
def test_sandbox_rejects_forbidden_code(snippet, needle):
    code = "from build123d import *\n" + snippet + "\ndef build():\n    return [Box(1, 1, 1)]\n"
    errs = check_code(code)
    assert errs and any(needle in e for e in errs), errs
    res = run_code(code)
    assert not res["ok"] and res["kind"] == "policy"


def test_sandbox_requires_build():
    assert any("build()" in e for e in check_code("from build123d import *\nx = Box(1, 1, 1)\n"))


def test_sandbox_runs_good_code_and_measures():
    res = run_code(GOOD)
    assert res["ok"], res.get("error")
    assert res["bbox_mm"] == [120.0, 80.0, 43.0]
    assert abs(res["volume_mm3"] - (120 * 80 * 40 + 3.14159 * 100 * 6)) < 5
    assert {p["label"] for p in res["parts"]} == {"body.1", "button.1"}
    assert all(res["files"][k].stat().st_size > 0 for k in ("step", "stl", "glb"))


def test_sandbox_infinite_loop_times_out():
    code = "from build123d import *\n\ndef build():\n    while True:\n        pass\n"
    res = run_code(code, timeout_s=4)
    assert not res["ok"] and res["kind"] == "timeout"


def test_sandbox_env_has_no_secrets(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-test-value-not-a-real-key")
    # the program cannot read os.environ (policy), so check the child environment through the runner itself:
    # a runtime error message would carry any leaked value; instead assert the clean env the parent builds
    from api.cad.codegen import sandbox

    captured = {}
    real_popen = sandbox.subprocess.Popen

    def spy(cmd, **kw):
        captured.update(kw["env"])
        captured["cmd"] = cmd
        return real_popen(cmd, **kw)

    monkeypatch.setattr(sandbox.subprocess, "Popen", spy)
    assert run_code(GOOD)["ok"]
    assert "OPENROUTER_API_KEY" not in captured and set(captured) - {"cmd"} <= {
        "PATH", "HOME", "TMPDIR", "LANG", "OMP_NUM_THREADS", "PYTHONHASHSEED", "OPENBLAS_NUM_THREADS", "MALLOC_ARENA_MAX"}
    assert "-I" in captured["cmd"]


def test_runner_import_guard_and_builtins():
    # second layer inside the child: even code that slipped past the AST check cannot import or open files
    from api.cad.codegen import _runner

    with pytest.raises(ImportError):
        _runner.guarded_import("os")
    with pytest.raises(ImportError):
        _runner.guarded_import("build123d", level=1)
    assert _runner.guarded_import("math").sqrt(4) == 2
    assert not {"open", "exec", "eval", "compile", "getattr", "__import__"} & set(_runner.SAFE_BUILTINS)
    ok = "from build123d import *\n\ndef build():\n    from math import sqrt\n    return [Box(sqrt(4), 1, 1)]\n"
    assert run_code(ok)["ok"]  # math is allowed at runtime too


def test_sandbox_runtime_error_is_reported_with_line():
    code = "from build123d import *\n\ndef build():\n    a = Box(1, 1, 1)\n    return [a, 1 / 0]\n"
    res = run_code(code)
    assert not res["ok"] and res["kind"] == "runtime" and "ZeroDivisionError" in res["error"]
    assert "model.py line 5" in res["error"]


def test_sandbox_rejects_flat_parts():
    code = "from build123d import *\n\ndef build():\n    return [Rectangle(10, 10)]\n"
    res = run_code(code)
    assert not res["ok"] and "no solid volume" in res["error"]


# --------------------------------------------------------------------------- engine


def test_generate_ok_first_try(tmp_path):
    llm = FakeLLM(fence(GOOD))
    r = generate_cad("A small desk speaker", category="generic", out_dir=tmp_path, llm=llm)
    assert r["status"] == "ok" and r["version"] == 1 and r["label"] == LABEL
    assert (tmp_path / "model_v1.py").read_text() == GOOD
    assert all((tmp_path / f"model_v1.{k}").exists() for k in ("glb", "step", "stl", "json"))
    assert r["bbox_mm"] == [120.0, 80.0, 43.0] and r["volume_mm3"] > 0 and len(r["parts"]) == 2
    assert "Minimal example of the conventions" in llm.prompts[0]  # generic seed as context


def test_repair_loop_feeds_error_back_then_succeeds(tmp_path):
    broken = GOOD.replace('body.label = "body.1"', 'body.label = "body.1"\n    raise ValueError("fillet failed here")')
    llm = FakeLLM(fence(broken), fence(GOOD))
    r = generate_cad("stick vacuum", category="vacuum", out_dir=tmp_path, llm=llm)
    assert r["status"] == "repaired" and len(r["attempts"]) == 2
    assert r["attempts"][0]["error_kind"] == "runtime" and r["attempts"][1]["error"] is None
    assert "fillet failed here" in llm.prompts[1] and "Your program failed" in llm.prompts[1]
    assert "stick_vacuum" in llm.prompts[0]  # seeded with the family program


def test_policy_violation_is_repaired(tmp_path):
    evil = "import os\n" + GOOD
    llm = FakeLLM(fence(evil), fence(GOOD))
    r = generate_cad("thing", category="generic", out_dir=tmp_path, llm=llm)
    assert r["status"] == "repaired" and r["attempts"][0]["error_kind"] == "policy"
    assert "import 'os' is not allowed" in llm.prompts[1]


def test_bbox_validation_triggers_repair(tmp_path):
    huge = GOOD.replace('"length": 120.0', '"length": 1200.0')
    llm = FakeLLM(fence(huge), fence(GOOD))
    r = generate_cad("thing", category="generic", out_dir=tmp_path, llm=llm, dims=(120, 80, 45))
    assert r["status"] == "repaired" and "outside 0.5×–2×" in r["attempts"][0]["error"]


def test_final_failure_falls_back_to_seed_family(tmp_path):
    bad = fence("from build123d import *\n\ndef build():\n    return [1 / 0]\n")
    llm = FakeLLM(bad, bad, bad)
    r = generate_cad("A next-gen home robot that tidies up", out_dir=tmp_path, llm=llm)
    assert r["category"] == "home_robot" and r["seed_family"] == "home_robot"
    assert r["status"] == "fallback" and len(r["attempts"]) == 3 and r["source"] == "seed:home_robot"
    assert "seed family" in r["notes"][0] and r["code"].count("def build_parts") == 1
    assert (tmp_path / "model_v1.glb").exists() and max(r["bbox_mm"]) > 500


def test_llm_unavailable_falls_back_without_calls(tmp_path):
    # no key in the test session → api.llm raises LLMNotConfigured → seed family, no crash
    r = generate_cad("Rooftop solar array for a family house", out_dir=tmp_path)
    assert r["status"] == "fallback" and r["seed_family"] == "solar_array" and "LLM unavailable" in r["notes"][0]


def test_wearable_falls_back_to_w17_family(tmp_path):
    r = generate_cad("Whoop-style band for kitesurfers", out_dir=tmp_path)
    assert r["category"] == "wearable" and r["status"] == "fallback" and r["source"] == "family:wearable_band"
    assert (tmp_path / "model_v1.glb").exists() and r["code"] is None and 25 <= max(r["bbox_mm"]) <= 80


def test_edit_mode_modifies_previous_code(tmp_path):
    v1 = generate_cad("desk box", category="generic", out_dir=tmp_path, llm=FakeLLM(fence(GOOD)))
    edited = GOOD.replace('"height": 40.0', '"height": 60.0')
    llm = FakeLLM(fence(edited))
    v2 = generate_cad("desk box", previous_code=v1["code"], instruction="make it taller", out_dir=tmp_path, llm=llm)
    assert v2["version"] == 2 and v2["status"] == "ok" and v2["parent_version"] == 1
    assert GOOD in llm.prompts[0] and "make it taller" in llm.prompts[0] and "Do not rewrite from scratch" in llm.prompts[0]
    assert "WORKING, tested parametric program" not in llm.prompts[0]  # no seed in edit mode
    assert v2["bbox_mm"][2] == 63.0 and (tmp_path / "model_v1.py").read_text() == GOOD  # v1 kept


def test_edit_failure_keeps_previous_version(tmp_path):
    generate_cad("desk box", category="generic", out_dir=tmp_path, llm=FakeLLM(fence(GOOD)))
    bad = fence("from build123d import *\n\ndef build():\n    return []\n")
    r = refine_cad(None, "add wheels", out_dir=tmp_path, llm=FakeLLM(bad, bad, bad))
    assert r["status"] == "fallback" and r["source"] == "previous_version" and r["code"] == GOOD and r["version"] == 2


def test_refine_uses_latest_version(tmp_path):
    generate_cad("desk box", category="generic", out_dir=tmp_path, llm=FakeLLM(fence(GOOD)))
    llm = FakeLLM(fence(GOOD.replace("Cylinder(10, 6)", "Cylinder(14, 6)")))
    r = refine_cad(None, "bigger knob", out_dir=tmp_path, llm=llm)
    assert r["version"] == 2 and r["parent_version"] == 1 and "desk box" in llm.prompts[0]
    meta = json.loads((tmp_path / "model_v2.json").read_text())
    assert meta["instruction"] == "bigger knob" and "code" not in meta


# --------------------------------------------------------------------------- helpers + classifier + route


def test_extract_code_variants():
    assert extract_code(fence(GOOD)) == GOOD
    assert extract_code(json.dumps({"code": GOOD})).strip() == GOOD.strip()
    assert extract_code(GOOD).strip() == GOOD.strip()


def test_dims_helpers():
    assert target_dims((100, 50, 20)) == (100.0, 50.0, 20.0)
    assert target_dims({"length_mm": 10, "width_mm": 5, "height_mm": 2}) == (10.0, 5.0, 2.0)
    assert target_dims({"colour": "red"}) is None
    assert check_dims([200, 100, 40], (100, 50, 20)) is None
    assert check_dims([100, 50, 20], (20, 50, 100)) is None  # orientation-free
    assert "outside" in check_dims([500, 50, 20], (100, 50, 20))


@pytest.mark.parametrize("text,cat,fam,variant", [
    ("Whoop-style fitness band for kitesurfers", "wearable", "wearable_band", None),
    ("Baby changing table with storage", "furniture_child", "furniture", "changing_table"),
    ("Kids activity table for toddlers", "furniture_child", "furniture", "activity_table"),
    ("Next-gen home robot that tidies up", "home_robot", "home_robot", "helper"),
    ("Dyson-style cordless stick vacuum", "vacuum", "stick_vacuum", "stick"),
    ("Smart irrigation controller + valve for gardens", "irrigation", "irrigation", "kit"),
    ("Rooftop solar array for a family house", "solar_roof", "solar_array", "roof"),
    ("Hydrodynamic surfboard for big waves", "board", "board", "surf"),
    ("Twin-tip kiteboard", "board", "board", "kite"),
    ("Bedside lamp with warm light", "lighting", None, None),
    ("Bluetooth key finder tag", "ble_accessory", None, None),
    ("Robot vacuum cleaner", "generic", None, None),
    ("A coffee grinder", "generic", None, None),
])
def test_classifier(text, cat, fam, variant):
    assert classify(text) == cat
    assert seed_for(cat, text) == (fam, variant)


def test_code_route_serves_program(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.cad.codegen.routes import router

    monkeypatch.setenv("FILES_DIR", str(tmp_path))
    generate_cad("desk box", category="generic", project_id="p_code1", llm=FakeLLM(fence(GOOD)))
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    r = c.get("/projects/p_code1/cad/code/1")
    assert r.status_code == 200 and r.text == GOOD and r.headers["content-type"].startswith("text/x-python")
    assert c.get("/projects/p_code1/cad/code/2").status_code == 404
    assert c.get("/projects/..%2Fetc/cad/code/1").status_code == 404
    assert os.path.exists(tmp_path / "p_code1" / "model_v1.glb")
