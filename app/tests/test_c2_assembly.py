"""C2 — assemblies: parts connected by build123d Joints, measured interference / clearance / fastener checks, exploded
vectors, fastener BOM lines, GET /projects/{id}/assembly, the engineering "assembly" group. Offline (showcase fixtures +
prebuilt STEP files, in-process solids), no LLM. CAD_ASSEMBLY=1 is set per test with monkeypatch."""

from __future__ import annotations

import math

import pytest
from build123d import Box, Cylinder, Pos
from fastapi.testclient import TestClient

from api.cad import families
from api.cad.assembly import engine as E
from api.cad.assembly import fasteners as fx
from api.cad.assembly import service as S
from api.cad.assembly.checks import assembly_checks
from api.main import app
from contracts.artifacts import BOMItem, EngineeringArtifact, ProjectAssembly

client = TestClient(app)
SHOWCASES_CLEAN = ["demo_whoop_kitesurf", "demo_stick_vacuum", "demo_home_robot"]


@pytest.fixture(scope="module", autouse=True)
def _seed():
    assert client.post("/demo/reset").status_code == 200
    yield


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("CAD_ASSEMBLY", "1")


def _asm(pid: str) -> dict:
    r = client.get(f"/projects/{pid}/assembly")
    assert r.status_code == 200, r.text
    return r.json()


def _check(j: dict, cid: str) -> dict:
    return next(c for c in j["checks"] if c["id"] == cid)


def _solve(items, family=None) -> E.Result:
    return E.solve(E.from_shapes(items), family)


def _family(name: str, **params) -> E.Result:
    from api.cad.family_mode import part_names
    from api.cad.parts import trace_labels

    p = families.params_for(name, **params)
    with trace_labels(families.module(name).__file__) as sites:
        _, parts = families.module(name).build(p)
    names = part_names(name, sites, [q.label for q in parts])
    groups: dict[str, list] = {}
    for q in parts:
        info = names.get(q.label) or {"part_id": q.label, "name": q.label, "role": "other"}
        g = groups.setdefault(info["part_id"], [info["part_id"], info["name"], info["role"], [], []])
        g[3].append(q)
        g[4].append(q.label)
    return _solve([tuple(g) for g in groups.values()], name)


def _bad(r: E.Result) -> list[tuple[str, str]]:
    return [(r.comps[x["a"]].part_id, r.comps[x["b"]].part_id) for x in r.interferences if x["kind"] == "interference"]


# --------------------------------------------------------------------------- flag


def test_route_off_when_disabled(monkeypatch):
    monkeypatch.setenv("CAD_ASSEMBLY", "0")  # C5: on by default
    assert client.get("/projects/demo_whoop_kitesurf/assembly").status_code == 404
    eng = client.get("/projects/demo_whoop_kitesurf/engineering").json()
    assert eng.get("assembly") is None
    assert not [c for c in eng["checks"] if c["domain"] == "assembly"]


def test_route_errors(on, monkeypatch):
    assert client.get("/projects/nope/assembly").status_code == 404
    assert client.get("/projects/demo_whoop_kitesurf/assembly?version=99").status_code == 404
    monkeypatch.setattr(S, "step_for", lambda pid, glb: None)  # a legacy W2 direction: no labelled STEP next to its GLB
    r = client.get("/projects/demo_desk_lamp/assembly")
    assert r.status_code == 404 and "STEP" in r.json()["detail"]


def test_demos_have_pro_assemblies(on):
    """C5: the two cached demos ship a labelled STEP for their chosen direction (lamp: base screws into inserts;
    card: welded, screwless)."""
    lamp, card = _asm("demo_desk_lamp"), _asm("demo_tracker_card")
    assert not [x for x in lamp["interferences"] + card["interferences"] if x["kind"] == "interference"]
    assert any("held by the modelled hardware" in j["rule"] for j in lamp["joints"])
    assert not card["fasteners"]  # the energy director holds the card: no rule-of-thumb screws


# --------------------------------------------------------------------------- showcases (correct models)


@pytest.mark.parametrize("pid", SHOWCASES_CLEAN)
def test_showcase_assembly_clean(on, pid):
    j = _asm(pid)
    a = ProjectAssembly.model_validate(j)
    parts = {p["part_id"] for p in client.get(f"/projects/{pid}/parts").json()["parts"]}
    ids = [n.part_id for n in a.nodes]
    assert set(ids) == parts and len(ids) == len(set(ids))
    # a tree: one root, every other part has exactly one parent and one joint
    assert [n.part_id for n in a.nodes if n.parent is None] == [a.root]
    assert len(a.joints) == len(a.nodes) - 1
    assert {jt.child for jt in a.joints} == set(ids) - {a.root}
    assert all(jt.parent in parts for jt in a.joints)
    # 0 interferences on the correct models; every overlap is classified and measured
    assert [x for x in a.interferences if x.kind == "interference"] == []
    assert all(x.volume.value > E.TOL and x.volume.label == "measured" for x in a.interferences)
    assert _check(j, "asm_interference")["verdict"] == "pass"
    assert _check(j, "asm_joint_closure")["verdict"] == "pass"
    assert all(c["domain"] == "assembly" and c["value"]["label"] in ("measured", "estimate") and c["threshold"] is not None
               or c["verdict"] == "info" for c in j["checks"])
    assert a.summary.startswith(f"{len(ids)} parts")
    # exploded vectors: unit length, the root stays, every other part moves
    for n in a.nodes:
        assert math.isclose(math.hypot(*n.explode_vector), 1.0, abs_tol=1e-3)
        if n.parent is None:
            assert n.explode_distance_mm == 0
        else:
            assert n.explode_distance_mm > 0


def test_whoop_joints(on):
    j = _asm("demo_whoop_kitesurf")
    kinds = {x["child"]: (x["parent"], x["kind"], x["method"]) for x in j["joints"]}
    assert kinds["top_shell"] == ("bottom_shell", "rigid", "snap_fit")  # 44 mm pod: snap-fit, no screws
    assert kinds["strap"][2] == "clip"
    assert kinds["window"][2] == "inlay"
    lines = j["fasteners"]
    assert [f["part"].split()[0] for f in lines] == ["Spring"] and lines[0]["qty"] == 2
    gap = _check(j, "asm_parting_gap")
    assert gap["verdict"] == "pass" and gap["value"]["value"] <= 0.3
    # the strap loop is drawn with a gap under the pod: measured and flagged, not hidden
    assert _check(j, "asm_support")["verdict"] == "warn" and "Strap" in _check(j, "asm_support")["notes"][0]


def test_vacuum_moving_joints_and_fasteners(on):
    j = _asm("demo_stick_vacuum")
    kinds = {x["child"]: x for x in j["joints"]}
    assert kinds["brush_roll"]["kind"] == "revolute" and kinds["rear_wheels"]["kind"] == "revolute"
    assert kinds["trigger"]["kind"] == "linear" and kinds["trigger"]["range"] == [0, 0.5]
    assert kinds["wand_release"]["kind"] == "linear"  # its pocket runs through the collar (same rigid body): no interference
    screwed = [x for x in j["joints"] if x["method"] == "screwed"]
    assert screwed and all(f["source"] in ("api.cad.stdparts", "built-in table") for x in screwed for f in x["fasteners"])
    n_uses = sum(f["qty"] for x in j["joints"] for f in x["fasteners"])
    assert sum(f["qty"] for f in j["fasteners"]) == n_uses == _check(j, "asm_fastener_count")["value"]["value"]
    assert all(f["id"].startswith("fx") and f["category"] == "mechanical" and f["unit_cost_est"]["value"] > 0 for f in j["fasteners"])
    eng = _check(j, "asm_fastener_engagement")
    assert eng["verdict"] in ("pass", "warn") and eng["value"]["label"] == "measured"
    # clearances measured for every moving joint
    moving = {x["child"] for x in j["joints"] if x["dof"]}
    assert moving <= {c["part_id"] for c in j["clearances"]}


def test_drone_showcase_props_clear_after_c5(on):
    """The recorded drone concept had 5-inch props on 83 mm arms: discs overlapping each other and sweeping the top
    battery (found by this motion study). C5 regenerated it with 110 mm arms + its pro hardware: 0 interferences."""
    j = _asm("demo_drone_follow")
    assert not [x for x in j["interferences"] if x["kind"] == "interference"]
    assert _check(j, "asm_interference")["verdict"] == "pass"
    kinds = {x["child"]: x for x in j["joints"]}
    assert kinds["prop_1"]["parent"] == "motor_1" and kinds["prop_1"]["kind"] == "revolute"
    assert kinds["motor_1"]["parent"] == "arm_1" and kinds["motor_1"]["method"] == "screwed"
    assert kinds["arm_1"]["parent"] == "hinge_1" and kinds["arm_1"]["kind"] == "revolute" and kinds["arm_1"]["dof"] == 0  # locked
    # pro: the motor's 4 modelled screws (C1) hold it — no rule-of-thumb screws on top (one source of truth)
    assert "held by the modelled hardware" in kinds["motor_1"]["rule"] and not kinds["motor_1"]["fasteners"]


# --------------------------------------------------------------------------- parametric families


def test_drone_family_default_is_clean_and_low_motors_are_not():
    bad = _bad(_family("drone", motor_height=16.0))  # the pre-C5 default: 7-inch props sweep through the body's top corners
    assert bad and all("propeller" in a or "propeller" in b for a, b in bad)
    r = _family("drone")  # C5 default motor_height=28: props raised above the body and battery
    assert _bad(r) == []
    props = [c for c in r.clearances if r.comps[c["part"]].role == "prop"]
    # blades clear everything over a full turn; they pass 0.9 mm over the motor bell (< 2 mm rule → warn, measured)
    assert len(props) == 4 and all(c["verdict"] in ("pass", "warn") and c["min"] > 0 for c in props)


@pytest.mark.parametrize("name", ["home_robot", "stick_vacuum"])
def test_family_models_clean(name):
    r = _family(name)
    assert _bad(r) == []
    assert all(not math.isnan(j.residual_mm) and j.residual_mm < 0.01 for j in r.joints.values())


# --------------------------------------------------------------------------- deliberate cases


def _shells(overlap_mm: float):
    bottom = Pos(0, 0, 5) * Box(80, 50, 10)
    top = Pos(0, 0, 15 - overlap_mm) * Box(80, 50, 10)
    return [("bottom", "Bottom shell", "shell_bottom", bottom), ("top", "Top shell", "shell_top", top)]


def test_overlapped_shells_detected():
    r = _solve(_shells(1.0))
    bad = [x for x in r.interferences if x["kind"] == "interference"]
    assert len(bad) == 1 and math.isclose(bad[0]["volume"], 80 * 50 * 1.0, rel_tol=1e-3)
    ck = {c.id: c for c in assembly_checks(r)}
    assert ck["asm_interference"].verdict == "fail" and ck["asm_interference"].value.value == 1


def test_clean_shells_screwed_with_measured_engagement():
    r = _solve(_shells(0.0))
    assert _bad(r) == []
    j = next(iter(r.joints.values()))
    assert j.mate.method == "screwed" and j.mate.parting  # 80 mm ≥ 60 mm: screws into heat-set inserts
    e = j.engagement
    assert e["size"] == "M2.5" and e["qty"] == 4 and e["insert"]
    # solid 10 mm shells: flange capped at 2·d = 5 mm, insert M2.5×4 → shortest ISO length ≥ 9 mm is 10
    assert e["screw_len"] == 10 and e["verdict"] == "pass"
    assert all(math.isclose(row["thread_mm"], 10.0, abs_tol=1e-6) and math.isclose(row["head_mm"], 10.0, abs_tol=1e-6)
               for row in e["rows"])
    assert e["min_engagement"] == pytest.approx(fx.insert_length("M2.5"))
    ck = {c.id: c for c in assembly_checks(r)}
    assert ck["asm_parting_gap"].verdict == "pass" and ck["asm_parting_gap"].value.value == 0


def test_thin_boss_fails_insert():
    bottom = Pos(0, 0, 1.5) * Box(80, 50, 3)
    top = Pos(0, 0, 4.5) * Box(80, 50, 3)  # 3 mm on both sides: an M2.5×4 insert needs 4.5 mm of boss
    r = _solve([("bottom", "Bottom shell", "shell_bottom", bottom), ("top", "Top shell", "shell_top", top)])
    e = next(iter(r.joints.values())).engagement
    assert e["verdict"] == "fail" and e["min_thread_mat"] == pytest.approx(3.0)
    assert {c.id: c for c in assembly_checks(r)}["asm_fastener_engagement"].verdict == "fail"


def test_prop_clearance_value():
    base = Pos(0, 0, 2) * Box(200, 200, 4)
    motor = Pos(0, 0, 14) * Cylinder(10, 20)
    prop = Pos(0, 0, 25) * Box(100, 8, 2)            # disc radius 50 mm, z 24-26
    post = Pos(58, 0, 20) * Box(4, 4, 32)            # post face at x = 56 → 6 mm from the tip at x = 50
    r = _solve([("base", "Frame", "frame", base), ("motor_1", "Motor", "motor", motor), ("prop_1", "Propeller", "prop", prop),
                ("post", "Post", "frame", post)])
    c = next(c for c in r.clearances if r.comps[c["part"]].part_id == "prop_1")
    assert c["against"] is not None and r.comps[c["against"]].part_id == "post"
    assert c["min"] == pytest.approx(6.0, abs=0.05) and c["verdict"] == "pass"
    # move the post into the disc: the motion study finds the collision
    r2 = _solve([("base", "Frame", "frame", base), ("motor_1", "Motor", "motor", motor), ("prop_1", "Propeller", "prop", prop),
                 ("post", "Post", "frame", Pos(0, 48, 20) * Box(4, 4, 32))])
    assert ("prop_1", "post") in _bad(r2) or ("post", "prop_1") in _bad(r2)


def test_button_pressed_into_neighbour():
    shell = Pos(0, 0, 5) * Box(60, 40, 10)
    button = Pos(0, 0, 10.5) * Box(6, 6, 3)          # z 9-12, seated 1 mm in the shell
    r = _solve([("shell", "Housing", "shell_bottom", shell), ("button", "Button", "button", button)])
    assert _bad(r) == []
    j = next(j for j in r.joints.values() if r.comps[j.child].part_id == "button")
    assert j.mate.kind == "linear" and j.residual_mm < 1e-6
    # a wheel (another rigid body) 0.3 mm under the button's travel: pressing 0.5 mm collides
    wheel = Pos(0, 0, 9 - 0.3 - 5) * Cylinder(5, 4, rotation=(90, 0, 0))
    r2 = _solve([("shell", "Housing", "shell_bottom", shell), ("button", "Button", "button", button),
                 ("wheel", "Wheel", "other", wheel)])
    bad = _bad(r2)
    assert any({"button", "wheel"} == {a, b} for a, b in bad), bad


# --------------------------------------------------------------------------- hooks: engineering, parts, costs


def test_engineering_group(on):
    eng = client.get("/projects/demo_stick_vacuum/engineering").json()
    a = EngineeringArtifact.model_validate(eng)
    assert a.assembly is not None and a.assembly.project_id == "demo_stick_vacuum"
    ids = [c.id for c in a.checks if c.domain == "assembly"]
    assert {"asm_interference", "asm_clearance", "asm_fastener_engagement", "asm_joint_closure"} <= set(ids)
    assert any(x.id == "e5" for x in a.assumptions)


def test_part_extras_glb_axes(on):
    ex = S.part_extras("demo_stick_vacuum")
    parts = client.get("/projects/demo_stick_vacuum/parts").json()["parts"]
    assert set(ex) == {p["part_id"] for p in parts}
    roots = [k for k, v in ex.items() if v["parent_part_id"] is None]
    assert len(roots) == 1 and ex[roots[0]]["joint"] is None
    assert ex["brush_roll"]["joint"] == "revolute"
    # CAD (Z up) → GLB (+Y up) is the same mapping as the GLB: the wand axis (CAD Z) explodes/lies along GLB Y
    assert S.glb_axes((1.0, 2.0, 3.0)) == [1.0, 3.0, -2.0]
    ctx_parts = {p["part_id"]: p for p in parts}
    comps = {c.part_id: c for c in E.load_step("api/cad/prebuilt/showcase_stick_vacuum/model_v2.step",
                                               "api/cad/prebuilt/showcase_stick_vacuum/model_v2.glb")}
    for pid in ("floor_head", "battery_pack", "wand"):
        bb = comps[pid].bb
        c = S.glb_axes(((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2))
        assert all(abs(a - b) < 1.0 for a, b in zip(c, ctx_parts[pid]["centroid_mm"])), (pid, c, ctx_parts[pid]["centroid_mm"])


def test_fastener_bom_merge_and_costs(on, monkeypatch):
    from api.costs import engine as costs_engine
    from api.stages import runner

    fxs = S.fastener_bom("demo_stick_vacuum")
    assert fxs and all(isinstance(b, BOMItem) and b.unit_cost_est is not None for b in fxs)
    assert all(b.unit_cost_est.label == "estimate" or b.lcsc_pn for b in fxs)
    items = [BOMItem(id="m1", part="Fastener set", category="mechanical", qty=1),
             BOMItem(id="e1", part="MCU 32-bit", category="electronic", qty=1)]
    merged = S.merge_fastener_lines(items, fxs)
    assert [b.id for b in merged][:1] == ["e1"] and len(merged) == 1 + len(fxs)
    assert len({b.id for b in merged}) == len(merged)
    assert S.merge_fastener_lines(items, []) == items
    # the C5 hook in load_bom → stage-5 cost lines carry the fastener lines
    orig = costs_engine.load_bom

    def hooked(ctx, order_qty=2000):
        got, gen, notes = orig(ctx, order_qty)
        return S.costs_hook(ctx, got), gen, notes

    monkeypatch.setattr(costs_engine, "load_bom", hooked)
    art = costs_engine.build_costs(runner.build_context("demo_stick_vacuum", 5))
    lines = {ln.bom_item_id: ln for ln in art.bom_lines}
    assert {b.id for b in fxs} <= set(lines)
    assert all(lines[b.id].extended.value > 0 for b in fxs)


def test_costs_hook_noop_when_off(monkeypatch):
    monkeypatch.setenv("CAD_ASSEMBLY", "0")
    from api.stages import runner

    items = [BOMItem(id="m1", part="Fastener set", category="mechanical", qty=1)]
    assert S.costs_hook(runner.build_context("demo_stick_vacuum", 5), items) == items


def test_cache_reused(on):
    import time

    client.get("/projects/demo_home_robot/assembly")
    t = time.monotonic()
    j = _asm("demo_home_robot")
    assert time.monotonic() - t < 0.5 and j["engine"] == E.ENGINE
