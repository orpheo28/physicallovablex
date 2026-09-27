"""Record the W21 showcase gallery: live runs on an isolated API, exported as offline fixtures ($0 to open).

    # 1. isolated API (own DB + files, real key from .env):
    DB_PATH=api/data/w21.db FILES_DIR=api/data/files_w21 uv run uvicorn api.main:app --port 8121
    # 2. live runs (prints key usage before/after each batch, never the key; stops on a key error / budget):
    uv run python -m api.fixtures._showcase run whoop_kitesurf [more slugs…] --budget 3.0
    # 3. export finished projects as fixtures (same DB_PATH / FILES_DIR as the API):
    DB_PATH=api/data/w21.db FILES_DIR=api/data/files_w21 uv run python -m api.fixtures._showcase export [slugs…]
    # 4. after a schema / engine change, refresh from the fixtures alone (no DB, no LLM):
    FILES_DIR=$(mktemp -d) OPENROUTER_API_KEY= uv run python -m api.fixtures._showcase migrate [slugs…]

    # W29: named-part GLBs, parts extras and anatomy (deterministic, no LLM; photos untouched):
    DB_PATH=$(mktemp -d)/w.db FILES_DIR=$(mktemp -d) FACTORY_MCP_DB=$(mktemp -d)/n.db OPENROUTER_API_KEY= \
        uv run python -m api.fixtures._showcase w29 [slugs…]

    # 5. W27 product photos (reference = Blender render of the current version's CAD, hero_v<n>.png):
    uv run python -m api.fixtures._showcase photos [slugs…] --budget 2.0 [--lifestyle whoop_kitesurf,…]
    FILES_DIR=$(mktemp -d) OPENROUTER_API_KEY= uv run python -m api.fixtures._showcase apply-photos [slugs…]

Runs are logged in api/data/w21_showcase_runs.json (slug → project id, timings, spend).
Export writes api/fixtures/showcase_<slug>/ (project.json, 01-13, factory_pack.json, versions.json, example.json) and
api/cad/prebuilt/showcase_<slug>/ (every file the artifacts reference + AI CAD programs + firmware + engineering cache).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "api" / "data" / "w21_showcase_runs.json"
API = os.getenv("SHOWCASE_API", "http://127.0.0.1:8121")

SHOWCASES: dict[str, dict] = {
    "whoop_kitesurf": dict(name="Kitesurf recovery band", prompt="A Whoop competitor for kitesurfers, screenless, 5-day battery",
                           refines=["add heart-rate and HRV sensing", "make it pink", "thinner, 8 mm pod"], make=True),
    "changing_table": dict(name="Safe baby changing table", prompt="A simple, safe changing table for babies",
                           refines=["add two storage baskets"], make=True),
    "stick_vacuum": dict(name="Cordless stick vacuum", prompt="A cordless stick vacuum, Dyson alternative",
                         refines=["make the bin bigger"], make=True),
    "irrigation_biarritz": dict(name="Smart garden irrigation", prompt="Smart irrigation for a 30 m² garden in Biarritz",
                                refines=["solar powered"], make=True),
    "solar_biarritz": dict(name="Rooftop solar, Biarritz", prompt="Solar panels sized for my 35 m² roof in Biarritz",
                           refines=["add a battery"], make=True),
    "surfboard_beginner": dict(name="Beginner surfboard 7'6\"", prompt="A hydrodynamic surfboard for beginners, 7'6\"",
                               refines=["wider nose"], make=True),
    "drone_follow": dict(name="Kitesurf follow-me drone", prompt="A foldable drone for kitesurf follow-me shots",
                         refines=["longer flight time"], make=True),
    "home_robot": dict(name="Toy-tidying home robot", prompt="A next-gen home robot that tidies toys", refines=[], make=False),
    "hair_dryer": dict(name="Quiet compact hair dryer", prompt="A quiet, compact hair dryer", refines=[], make=False),
    "instant_camera": dict(name="Retro instant camera", prompt="A retro instant camera", refines=[], make=False),
    "minimal_phone": dict(name="Minimalist smartphone", prompt="A minimalist smartphone without social apps", refines=[], make=False),
}


# --------------------------------------------------------------------------- budget (never prints the key)


def _key() -> str:
    from dotenv import dotenv_values

    return os.getenv("OPENROUTER_API_KEY") or dotenv_values(ROOT / ".env").get("OPENROUTER_API_KEY") or ""


def key_usage() -> float:
    import httpx

    r = httpx.get("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {_key()}"}, timeout=20)
    if r.status_code != 200:
        raise SystemExit(f"key check failed: HTTP {r.status_code} — stopping")
    d = r.json().get("data", r.json())
    return float(d.get("usage") or 0.0)


def _load_runs() -> dict:
    return json.loads(RUNS.read_text()) if RUNS.exists() else {}


def _save_runs(runs: dict) -> None:
    RUNS.parent.mkdir(parents=True, exist_ok=True)
    RUNS.write_text(json.dumps(runs, indent=1))


# --------------------------------------------------------------------------- live run


def _wait_version(c, pid: str, n: int, timeout: float = 600) -> tuple[dict, float, float]:
    """(version, seconds to done, seconds to settled)."""
    t0 = time.time()
    done_at = None
    while time.time() - t0 < timeout:
        v = next((x for x in c.get(f"/projects/{pid}/versions").json() if x["n"] == n), None)
        if v and v["status"] != "running" and done_at is None:
            done_at = time.time() - t0
        if v and v["status"] != "running" and not (v["render_pending"] or v["background_pending"] or v.get("cad_pending")):
            return v, done_at or 0.0, time.time() - t0
        time.sleep(1.0)
    raise RuntimeError(f"{pid} v{n} not settled after {timeout} s")


def run_one(slug: str) -> dict:
    import httpx

    spec = SHOWCASES[slug]
    c = httpx.Client(base_url=API, timeout=60)
    rec: dict = {"slug": slug, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    pid = c.post("/projects", json={"mode": "idea", "prompt": spec["prompt"], "name": spec["name"]}).json()["id"]
    rec["pid"] = pid
    t0 = time.time()
    assert c.post(f"/projects/{pid}/studio/start").status_code == 202
    v, t_done, t_settled = _wait_version(c, pid, 1)
    rec["v1"] = {"status": v["status"], "done_s": round(t_done, 1), "settled_s": round(t_settled, 1), "cad_note": v.get("cad_note"),
                 "code_url": (v.get("preview") or {}).get("code_url"), "cad_label": (v.get("preview") or {}).get("cad_label")}
    print(f"  {slug} v1 {v['status']} in {t_done:.1f}s (settled {t_settled:.1f}s) {rec['v1']['cad_label']}", flush=True)
    rec["refines"] = []
    for i, msg in enumerate(spec["refines"], 2):
        c.post(f"/projects/{pid}/refine", json={"message": msg})
        v, t_done, t_settled = _wait_version(c, pid, i)
        geo = any(ch["label"] == "AI CAD program" for ch in v["changes"])
        rec["refines"].append({"n": i, "message": msg, "status": v["status"], "done_s": round(t_done, 1), "settled_s": round(t_settled, 1),
                               "geometry": geo, "summary": v["summary"], "error": v.get("error")})
        print(f"  {slug} v{i} '{msg}' {v['status']} in {t_done:.1f}s{' (AI CAD edit)' if geo else ''}: {v['summary'][:90]}", flush=True)
    if spec["make"]:
        t1 = time.time()
        c.post(f"/projects/{pid}/autorun?through=13")
        while time.time() - t1 < 900:
            a = (c.get(f"/projects/{pid}").json().get("autorun") or {})
            if a.get("state") in ("done", "failed"):
                break
            time.sleep(2)
        rec["make_it_s"] = round(time.time() - t1, 1)
        rec["make_it_state"] = a.get("state")
        print(f"  {slug} Make it {a.get('state')} in {rec['make_it_s']}s", flush=True)
    # engineering + firmware (LLM version in the background), Factory Pack, dossier
    for _ in range(60):
        eng = c.get(f"/projects/{pid}/engineering").json()
        if not (eng.get("firmware") or {}).get("pending_llm"):
            break
        time.sleep(2)
    rec["engineering"] = {"category": eng.get("category"), "strategy": (eng.get("build_strategy") or {}).get("strategy")}
    if spec["make"]:
        c.get(f"/projects/{pid}/factory-pack")
        rec["pdf_bytes"] = len(c.get(f"/projects/{pid}/export", timeout=180).content)
    rec["total_s"] = round(time.time() - t0, 1)
    return rec


def cmd_run(slugs: list[str], budget: float) -> None:
    runs = _load_runs()
    base = runs.get("_usage_start")
    if base is None:
        base = runs["_usage_start"] = key_usage()
        _save_runs(runs)
    for slug in slugs:
        before = key_usage()
        spent = before - base
        print(f"[{slug}] key usage before: ${before:.4f} (spent this session ${spent:.4f} / ${budget:.2f})", flush=True)
        if spent >= budget - 0.15:
            print("budget exhausted — stopping", flush=True)
            break
        rec = run_one(slug)
        after = key_usage()
        rec["spend_usd"] = round(after - before, 4)
        print(f"[{slug}] key usage after: ${after:.4f} (this run ${after - before:.4f})", flush=True)
        runs = _load_runs()
        runs[slug] = rec
        _save_runs(runs)


# --------------------------------------------------------------------------- export


def _rewrite(obj, pid: str, new: str):
    return json.loads(json.dumps(obj, default=str).replace(pid, new))


def _refs(text: str, new: str) -> set[str]:
    names = set(re.findall(rf"/files/{re.escape(new)}/([A-Za-z0-9][A-Za-z0-9_.-]*)", text))
    for k in re.findall(rf"/projects/{re.escape(new)}/cad/code/(\d+)", text):
        names |= {f"model_v{k}.py", f"model_v{k}.json"}
    return names


def export_one(slug: str, pid: str) -> dict:
    from api.cad.build import PREBUILT_DIR, files_root
    from api.stages import runner
    from api.studio import store
    from contracts.artifacts import STAGE_NAMES, ExampleSummary

    new = f"demo_{slug}"
    ex_dir = ROOT / "api" / "fixtures" / f"showcase_{slug}"
    pre = PREBUILT_DIR / f"showcase_{slug}"
    shutil.rmtree(ex_dir, ignore_errors=True)
    shutil.rmtree(pre, ignore_errors=True)
    ex_dir.mkdir(parents=True)
    pre.mkdir(parents=True)
    project = runner.get_project(pid)
    pj = _rewrite(project.model_dump(mode="json"), pid, new)
    brief1 = runner.get_artifact(pid, 1)
    pj.update(id=new, example=f"showcase_{slug}", tags=["Example"], stage_status={},
              name=(brief1.product_name if brief1 is not None and brief1.product_name else SHOWCASES[slug]["name"]))
    (ex_dir / "project.json").write_text(json.dumps(pj, indent=1, ensure_ascii=False))
    texts = []
    stages = 0
    for n in range(1, 14):
        a = runner.get_artifact(pid, n)
        if a is None:
            continue
        stages += 1
        d = _rewrite(a.model_dump(mode="json"), pid, new)
        s = json.dumps(d, indent=1, ensure_ascii=False)
        texts.append(s)
        (ex_dir / f"{n:02d}_{STAGE_NAMES[n]}.json").write_text(s)
    fp = runner.get_artifact(pid, runner.FACTORY_PACK_STAGE)
    if fp is not None:
        s = json.dumps(_rewrite(fp.model_dump(mode="json"), pid, new), indent=1, ensure_ascii=False)
        texts.append(s)
        (ex_dir / "factory_pack.json").write_text(s)
    versions = []
    for v in store.list_versions(pid):
        snap = {str(k): x.model_dump(mode="json") for k, x in store.load_snapshot(pid, v.n).items()}
        versions.append(_rewrite({"version": v.model_dump(mode="json"), "snapshot": snap}, pid, new))
    vj = {"current": store.current(pid), "versions": versions}
    s = json.dumps(vj, ensure_ascii=False)
    texts.append(s)
    (ex_dir / "versions.json").write_text(s)
    src = files_root() / pid
    missing = []
    for name in sorted(_refs("\n".join(texts), new) | {"firmware.zip", "firmware.json"}):
        if (src / name).is_file():
            if name.endswith(".png"):  # renders: 256-colour palette PNG (~3× smaller in the repo / image)
                from PIL import Image

                Image.open(src / name).convert("RGB").quantize(256, dither=Image.Dither.FLOYDSTEINBERG).save(pre / name, optimize=True)
            else:
                shutil.copyfile(src / name, pre / name)
        else:
            missing.append(name)
    eng, card = finish_fixture(slug, ex_dir, pre)
    size = sum(f.stat().st_size for f in pre.iterdir())
    return {"slug": slug, "stages": stages, "versions": len(versions), "files": len(list(pre.iterdir())), "mb": round(size / 1e6, 1),
            "missing": missing, "card": card.one_line_result}


def finish_fixture(slug: str, ex_dir: Path, pre: Path):
    """Engineering cache (computed on the seeded state: same inputs digest as GET /projects/demo_<slug>/engineering, no
    LLM) + gallery card, from the fixture files alone. Used by export and by `migrate` (schema / engine changes)."""
    from api.cad.build import files_root
    from api.engineering.service import engineering_for_ctx
    from api.stages.registry import StageContext
    from contracts.artifacts import ARTIFACT_MODELS, STAGE_NAMES, ExampleSummary, Project

    new = f"demo_{slug}"
    pj = json.loads((ex_dir / "project.json").read_text())
    vj = json.loads((ex_dir / "versions.json").read_text())
    versions = vj["versions"]
    arts = {}
    for n in range(1, 14):
        f = ex_dir / f"{n:02d}_{STAGE_NAMES[n]}.json"
        if f.exists():
            arts[n] = ARTIFACT_MODELS[n].model_validate_json(f.read_text())
    stages = len(arts)
    ctx = StageContext(project=Project.model_validate(pj), stage=0, artifacts=arts)
    work = files_root() / new
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    for name in ("firmware.zip", "firmware.json"):
        if (pre / name).exists():
            shutil.copyfile(pre / name, work / name)
    eng = engineering_for_ctx(ctx, llm_firmware=False, force=True)
    for name in ("engineering.json", "firmware.json", "firmware.zip"):
        if (work / name).exists():
            shutil.copyfile(work / name, pre / name)
    shutil.rmtree(work, ignore_errors=True)
    cur = next((v["version"] for v in versions if v["version"]["n"] == vj["current"]), None)
    pv = (cur or {}).get("preview") or {}
    design = arts.get(2)
    hero = pv.get("render_url") or next((d.render_url for d in (design.directions if design else []) if d.render_url), None)
    costs = arts.get(5)
    unit = next((t.unit_cost for t in costs.tiers if t.quantity == costs.reference_quantity), None) if costs else None
    parts = [f"{len(versions)} version{'s' if len(versions) != 1 else ''}"]
    if (pv.get("cad_label") or "").startswith("AI-generated"):
        parts.append("AI-written CAD")
    if costs is not None and costs.unit_basis == "per_installation":  # installed price of the current version (battery incl.)
        unit = costs.target_retail_price
        parts.append(f"${unit.value:,.0f} installed per roof (turnkey, Estimate)")
    elif eng.unit_basis == "per_installation" and eng.installation_cost is not None:
        unit = eng.installation_cost
        parts.append(f"${unit.value:,.0f} per installation (turnkey, Estimate)")
    elif unit is not None:
        parts.append(f"${unit.value:,.2f}/unit @ {costs.reference_quantity:,} (Estimate)")
    if eng.build_strategy:
        parts.append(eng.build_strategy.title)
    parts.append(f"{stages}/13 stages")
    card = ExampleSummary(id=new, slug=slug, name=pj["name"], prompt=pj["prompt"], category=eng.category,
                          strategy=eng.build_strategy.strategy if eng.build_strategy else None, hero_image_url=hero,
                          glb_url=pv.get("glb_url"), one_line_result=" · ".join(parts), unit_basis=eng.unit_basis, unit_cost=unit,
                          versions=len(versions), stages_done=stages, tags=["Example"])
    photos = pv.get("photos") or []  # W27: hero_studio photo (reference = the CAD render) replaces the concept render
    from contracts.artifacts import ProductPhoto

    card.photos = [ProductPhoto.model_validate(p) for p in photos if p["shot"] in ("hero_studio", "lifestyle")]
    hero_photo = next((p for p in photos if p["shot"] == "hero_studio" and p["url"] == hero), None)
    card.hero_image_label = hero_photo["label"] if hero_photo else ("AI concept render — illustrative, not the CAD" if hero else None)
    (ex_dir / "example.json").write_text(card.model_dump_json(indent=1))
    return eng, card


def _ref_tier(costs):
    return next((t for t in costs.tiers if t.quantity == costs.reference_quantity), costs.tiers[0])


def _recost_snapshot(project, snap: dict) -> dict:
    """Stage 4 component risks + stage 5 costs of one Studio version, recomputed by the current code (deterministic)."""
    from api.costs.engine import build_costs
    from api.costs.lcsc import component_risk, match_bom
    from api.stages.registry import StageContext

    if 4 in snap and 3 in snap:
        snap[4].component_risks = component_risk(match_bom(snap[3].bom))
    if 5 in snap and 3 in snap:
        c = build_costs(StageContext(project=project, stage=5, artifacts={k: v for k, v in snap.items() if k in (1, 2, 3, 4)}))
        c.project_id, c.status, c.generated_at = project.id, snap[5].status, snap[5].generated_at
        snap[5] = c
    return snap


def recompute_one(ex_dir: Path) -> dict:
    """W21c: recompute every cost-dependent artifact of a showcase with the current code, no LLM: stage 4 component risks,
    stage 5 costs, stage 8 (policy quotes, template messages, autofill approval), 11, 12, the Factory Pack's BOM / cost
    sections, brand listing prices, every Studio version's stage 4/5 + preview + cost changes, the engineering cache and
    the gallery card. Needs DB_PATH / FILES_DIR / FACTORY_MCP_DB pointing at a scratch location and no OPENROUTER_API_KEY."""
    import api.main as m
    from api.cad.build import PREBUILT_DIR
    from api.costs.lcsc import component_risk, match_bom
    from api.showcase import after_seed
    from api.stages import runner
    from api.studio import product as P
    from api.studio import store
    from contracts.artifacts import STAGE_NAMES, VersionChange

    slug = ex_dir.name[len("showcase_"):]
    pid = f"demo_{slug}"
    old5 = json.loads((ex_dir / "05_costs.json").read_text())
    ot = next(t for t in old5["tiers"] if t["quantity"] == old5["reference_quantity"])
    before = {"unit": ot["unit_cost"]["value"], "retail": old5["target_retail_price"]["value"], "margin": ot["margin_pct"]["value"],
              "unit_label": old5.get("unit_basis", "per_unit"), "tiers": [t["quantity"] for t in old5["tiers"]]}
    project = after_seed([runner.seed_example(ex_dir.name)]) or runner.get_project(pid)
    project = runner.get_project(pid)
    arts = {n: a for n in range(1, 14) if (a := runner.get_artifact(pid, n)) is not None}
    snap = _recost_snapshot(project, {k: v for k, v in arts.items() if k <= 7})
    for n in (4, 5):
        runner.save_artifact(pid, n, snap[n], "validated")
    costs = snap[5]
    fp = runner.get_artifact(pid, runner.FACTORY_PACK_STAGE)
    if fp is not None:
        lines = {ln.bom_item_id: ln for ln in costs.bom_lines}
        bom = []
        for it in arts[3].bom:
            it = it.model_copy(deep=True)
            if (ln := lines.get(it.id)) is not None:
                it.unit_cost_est, it.lcsc_pn = ln.unit_price, ln.lcsc_pn
            bom.append(it)
        risks = {r.bom_item_id: r for r in snap[4].component_risks}
        for it in bom:
            r = risks.get(it.id)
            if r is not None:
                from contracts.artifacts import ComponentRisk

                it.risk = ComponentRisk(level=r.level, reasons=list(r.reasons))
        fp.bom, fp.cost_estimate, fp.target_quantities = bom, list(costs.tiers), [t.quantity for t in costs.tiers]
        runner.save_artifact(pid, runner.FACTORY_PACK_STAGE, fp)
    if 8 in arts:  # quotes follow the new stage-5 anchors (policy numbers, template messages: no LLM in a migration)
        m._autorun_threads.pop(pid, None)
        runner.run_stage(pid, 8)
        m._autofill_approve(pid)
        for n in (11, 12):
            if n in arts:
                runner.run_stage(pid, n)
        for n in (8, 11, 12):
            if (a := runner.get_artifact(pid, n)) is not None:
                runner.save_artifact(pid, n, a, "validated")
    if (brand := runner.get_artifact(pid, 13)) is not None:
        for lst in (brand.shopify_listing, brand.amazon_listing):
            if lst is not None:
                lst.price = costs.target_retail_price.model_copy()
        runner.save_artifact(pid, 13, brand, "validated")
    # Studio versions: stage 4/5 per snapshot, preview, cost changes
    prev = None
    for v in store.list_versions(pid):
        s5 = _recost_snapshot(project, store.load_snapshot(pid, v.n))
        store.patch_snapshot(pid, v.n, {k: s5[k] for k in (4, 5) if k in s5})
        v = store.get_version(pid, v.n)
        kept = list(v.preview.photos) if v.preview else []  # W27: photos are not derived from the snapshot
        v.preview = P.preview(s5)
        v.preview.photos = kept
        if prev is not None:
            stale = ("Component added", "Component removed")  # W21e: prices as stage 5 has them (per installation for solar)
            fresh = [c for c in P.changes(prev, s5) if c.area == "cost" or c.label in stale]
            v.changes = [c for c in v.changes if c.area != "cost" and c.label not in stale] + fresh
        v.cad_attempts, v.cad_repairs = _model_attempts(pid, v.preview.code_url if v.preview else None)
        store.save_version(pid, v)
        prev = s5
    # write the fixture files back from the scratch DB
    for n in range(1, 14):
        a = runner.get_artifact(pid, n)
        if a is not None:
            (ex_dir / f"{n:02d}_{STAGE_NAMES[n]}.json").write_text(json.dumps(a.model_dump(mode="json"), indent=1, ensure_ascii=False))
    fp = runner.get_artifact(pid, runner.FACTORY_PACK_STAGE)
    if fp is not None:
        (ex_dir / "factory_pack.json").write_text(json.dumps(fp.model_dump(mode="json"), indent=1, ensure_ascii=False))
    versions = [{"version": v.model_dump(mode="json"), "snapshot": {str(k): x.model_dump(mode="json") for k, x in store.load_snapshot(pid, v.n).items()}}
                for v in store.list_versions(pid)]
    (ex_dir / "versions.json").write_text(json.dumps({"current": store.current(pid), "versions": versions}, ensure_ascii=False))
    eng, card = finish_fixture(slug, ex_dir, PREBUILT_DIR / ex_dir.name)
    c5 = runner.get_artifact(pid, 5)
    t = _ref_tier(c5)
    after = {"unit": t.unit_cost.value, "retail": c5.target_retail_price.value, "margin": t.margin_pct.value, "bom": t.bom_cost.value,
             "unit_label": c5.unit_basis, "tiers": [x.quantity for x in c5.tiers], "cash": c5.total_cash_needed.value}
    return {"slug": slug, "before": before, "after": after, "card": card.one_line_result}


def _model_attempts(pid: str, code_url: str | None) -> tuple[int, int]:
    from api.cad.build import PREBUILT_DIR

    mm = re.search(r"/cad/code/(\d+)$", code_url or "")
    if not mm:
        return 0, 0
    f = PREBUILT_DIR / f"showcase_{pid[5:]}" / f"model_v{mm.group(1)}.json"
    if not f.exists():
        return 0, 0
    meta = json.loads(f.read_text())
    n = len(meta.get("attempts") or [])
    return n, (max(0, n - 1) if meta.get("status") in ("ok", "repaired") else 0)


def cmd_recompute(slugs: list[str]) -> None:
    rows = []
    for ex_dir in sorted((ROOT / "api" / "fixtures").glob("showcase_*")):
        if slugs and ex_dir.name[len("showcase_"):] not in slugs:
            continue
        r = recompute_one(ex_dir)
        rows.append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)


def cmd_migrate(slugs: list[str]) -> None:
    """Fixture-only refresh (no DB, no LLM): project name = brief product name, engineering cache, gallery card."""
    for ex_dir in sorted((ROOT / "api" / "fixtures").glob("showcase_*")):
        slug = ex_dir.name[len("showcase_"):]
        if slugs and slug not in slugs:
            continue
        pj = json.loads((ex_dir / "project.json").read_text())
        brief = json.loads((ex_dir / "01_brief.json").read_text())
        if brief.get("product_name") and pj["name"] != brief["product_name"]:
            pj["name"] = brief["product_name"]
            (ex_dir / "project.json").write_text(json.dumps(pj, indent=1, ensure_ascii=False))
        from api.cad.build import PREBUILT_DIR

        eng, card = finish_fixture(slug, ex_dir, PREBUILT_DIR / ex_dir.name)
        print(json.dumps({"slug": slug, "name": pj["name"], "unit_basis": card.unit_basis, "card": card.one_line_result}, ensure_ascii=False))


def cmd_export(slugs: list[str]) -> None:
    runs = _load_runs()
    for slug in slugs or [s for s in SHOWCASES if s in runs]:
        if slug not in runs:
            print(f"{slug}: no recorded run")
            continue
        print(json.dumps(export_one(slug, runs[slug]["pid"]), ensure_ascii=False))


# --------------------------------------------------------------------------- W27 product photos


def _current(ex_dir: Path) -> tuple[dict, dict]:
    vj = json.loads((ex_dir / "versions.json").read_text())
    return vj, next(v for v in vj["versions"] if v["version"]["n"] == vj["current"])


def cmd_photos(slugs: list[str], budget: float, lifestyle: set[str] | None) -> None:
    """hero_studio (+ lifestyle) of the current version, reference = hero_v<n>.png. Manifest: prebuilt/…/photos.json."""
    from api.cad import renders
    from api.cad.build import PREBUILT_DIR
    from api.cad.photos import engine as E
    from api.cad.photos import shots as S
    from PIL import Image

    model = os.getenv("LLM_IMAGE_MODEL_SHOWCASE") or renders.image_model()
    base = key_usage()
    spent = 0.0
    for ex_dir in sorted((ROOT / "api" / "fixtures").glob("showcase_*")):
        slug = ex_dir.name[len("showcase_"):]
        if slugs and slug not in slugs:
            continue
        pre = PREBUILT_DIR / ex_dir.name
        _, cur = _current(ex_dir)
        n = cur["version"]["n"]
        ref = pre / f"hero_v{n}.png"
        category = json.loads((ex_dir / "example.json").read_text())["category"]
        man_f = pre / "photos.json"
        manifest = json.loads(man_f.read_text()) if man_f.exists() else {}
        for shot in ["hero_studio"] + (["lifestyle"] if lifestyle is None or slug in lifestyle else []):
            if spent >= budget - 0.12:
                print(f"budget reached (${spent:.4f} / ${budget:.2f}) — stopping", flush=True)
                return
            kind = "cad_render" if ref.exists() else "none"
            prompt = S.shot_prompt(shot, category) if ref.exists() else S.fallback_prompt(shot, category, cur["version"]["summary"])
            t0 = time.time()
            try:
                raw = E._generate(prompt, ref.read_bytes() if ref.exists() else None, S.SHOTS[shot].aspect_ratio, model,
                                  time.monotonic() + 150)
            except E.PhotoFailed as e:
                print(f"  {slug} {shot}: FAILED {e.reason}", flush=True)
                if e.status == 402:
                    return
                continue
            cost = renders.last_cost() or 0.0
            spent += cost
            name = f"photo_v{n}_{shot}.png"
            tmp = pre / (name + ".full.png")
            E._save(raw, tmp, S.SHOTS[shot].aspect_ratio)
            Image.open(tmp).convert("RGB").quantize(256, dither=Image.Dither.FLOYDSTEINBERG).save(pre / name, optimize=True)
            tmp.unlink()
            manifest[shot] = {"file": name, "reference": kind, "model": model, "version": n, "cost_usd": round(cost, 4),
                              "seconds": round(time.time() - t0, 1)}
            man_f.write_text(json.dumps(manifest, indent=1))
            print(f"  {slug} {shot}: {time.time() - t0:.1f}s ${cost:.4f} (session ${spent:.4f})", flush=True)
    print(f"key usage: ${base:.4f} → ${key_usage():.4f}; per-request costs sum ${spent:.4f}", flush=True)


def apply_photos(ex_dir: Path) -> list:
    """Fixture photo fields from prebuilt/…/photos.json: current version preview.photos + render_url (= hero_studio),
    the chosen direction's render_url (02_design + version snapshot), stage 13 listing_photos, assumption a2_photo."""
    from api.cad.build import PREBUILT_DIR
    from api.cad.photos.engine import label_for
    from api.cad.photos.shots import SHOTS
    from contracts.artifacts import ProductPhoto

    slug = ex_dir.name[len("showcase_"):]
    pid = f"demo_{slug}"
    man_f = PREBUILT_DIR / ex_dir.name / "photos.json"
    if not man_f.exists():
        return []
    manifest = json.loads(man_f.read_text())
    photos = [ProductPhoto(shot=shot, url=f"/files/{pid}/{m['file']}", label=label_for(shot, m["reference"]),
                           reference=m["reference"], aspect_ratio=SHOTS[shot].aspect_ratio, staged=SHOTS[shot].staged,
                           model=m["model"], version=m["version"], created_at="2026-09-27T12:00:00Z")
              for shot, m in sorted(manifest.items(), key=lambda kv: list(SHOTS).index(kv[0]))]
    pj = [p.model_dump(mode="json") for p in photos]
    hero = next((p for p in photos if p.shot == "hero_studio"), None)
    vj, cur = _current(ex_dir)
    pv = cur["version"]["preview"]
    pv["photos"] = pj
    note = ("Product photos: AI images photo-styled from the Blender render of the CAD (geometry from our CAD; light, "
            "surface and framing by the image model). Lifestyle scenes are staged — illustrative.")

    def patch_design(d: dict) -> None:
        if hero is None:
            return
        chosen = next((x for x in d["directions"] if x["id"] == d.get("chosen_direction_id")), d["directions"][0])
        chosen["render_url"] = hero.url
        if not any(a["id"] == "a2_photo" for a in d["assumptions"]):
            d["assumptions"].append({"id": "a2_photo", "label": "estimate", "text": note, "source": None, "stage": 2})

    if hero is not None:
        pv["render_url"] = hero.url
        if "2" in cur["snapshot"]:
            patch_design(cur["snapshot"]["2"])
    (ex_dir / "versions.json").write_text(json.dumps(vj, ensure_ascii=False))
    f2 = ex_dir / "02_design.json"
    d2 = json.loads(f2.read_text())
    patch_design(d2)
    f2.write_text(json.dumps(d2, indent=1, ensure_ascii=False))
    f13 = ex_dir / "13_brand.json"
    if f13.exists():
        d13 = json.loads(f13.read_text())
        d13["listing_photos"] = [p for p in pj if p["shot"] in ("packshot_white", "lifestyle", "in_hand_scale", "detail_macro")]
        f13.write_text(json.dumps(d13, indent=1, ensure_ascii=False))
    return photos


def cmd_apply_photos(slugs: list[str]) -> None:
    from api.cad.build import PREBUILT_DIR

    for ex_dir in sorted((ROOT / "api" / "fixtures").glob("showcase_*")):
        slug = ex_dir.name[len("showcase_"):]
        if slugs and slug not in slugs:
            continue
        photos = apply_photos(ex_dir)
        eng, card = finish_fixture(slug, ex_dir, PREBUILT_DIR / ex_dir.name)
        print(json.dumps({"slug": slug, "photos": [p.shot for p in photos], "hero": card.hero_image_url}), flush=True)


def cmd_w29(slugs: list[str]) -> None:
    """W29 regeneration (no LLM, no network): GLBs in the W29 conventions, /parts extras baked, anatomy precomputed.
    Run with scratch DB_PATH / FILES_DIR / FACTORY_MCP_DB (it calls /demo/reset on that DB)."""
    from api.cad._w29_regen import bake, regen_demo, regen_showcase

    slugs = slugs or [*SHOWCASES, "desk_lamp", "tracker_card"]
    sizes: dict = {}
    for s in slugs:
        t0 = time.monotonic()
        sizes[s] = regen_demo(s) if s in ("desk_lamp", "tracker_card") else regen_showcase(s)
        print(json.dumps({"slug": s, "seconds": round(time.monotonic() - t0, 1), "glb_bytes_before_after": sizes[s]}), flush=True)
    pids = [f"demo_{s}" for s in slugs]
    print(json.dumps(bake(pids), indent=1), flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    budget = 3.0
    if "--budget" in args:
        i = args.index("--budget")
        budget = float(args[i + 1])
        del args[i:i + 2]
    if args[0] == "run":
        cmd_run(args[1:] or list(SHOWCASES), budget)
    elif args[0] == "export":
        cmd_export(args[1:])
    elif args[0] == "recompute":
        cmd_recompute(args[1:])
    elif args[0] == "migrate":
        cmd_migrate(args[1:])
    elif args[0] == "photos":
        life = None
        if "--lifestyle" in args:
            i = args.index("--lifestyle")
            life = set(args[i + 1].split(","))
            del args[i:i + 2]
        cmd_photos(args[1:], budget, life)
    elif args[0] == "apply-photos":
        cmd_apply_photos(args[1:])
    elif args[0] == "w29":  # W29: named-part GLBs + parts extras + anatomy, deterministic (no LLM)
        cmd_w29(args[1:])
    elif args[0] == "usage":
        print(f"key usage: ${key_usage():.4f}")
    else:
        raise SystemExit(__doc__)
