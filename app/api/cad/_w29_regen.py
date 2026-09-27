"""W29 regeneration of the showcase + demo 3D files (deterministic, no LLM). Run via
`uv run python -m api.fixtures._showcase w29 [slugs…]` (see api/fixtures/_showcase.py).

Per project: every GLB the fixtures reference is rebuilt in the W29 conventions (named part nodes + PartMeta extras,
smooth normals, KHR materials): recorded AI CAD programs (model_v<k>.py) re-run in the sandbox (same code → same
geometry, new tessellation + part names from the label call sites), recoloured copies (v<n>_ai.glb) re-derived from
them, family / wearable viewer models rebuilt from the version's direction, other GLBs (enclosures, demo directions)
finished in place with their own materials. Then /parts extras are written into each version's GLB and the anatomy
(anatomy_v<n>.glb + .json) is precomputed. STEP / STL / photos are untouched (geometry is the same). CadFile.size_bytes
in the fixtures follow the new GLB sizes. Returns {file: (bytes before, bytes after)}.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from pathlib import Path

from api.cad import glb
from api.cad.build import PREBUILT_DIR

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "api" / "fixtures"


def _look_for_direction(d) -> dict:
    from api.cad import family_mode
    from api.cad.families import family_look
    from api.studio import product as P

    fin, _, hex_ = P.split_finish(d.finish)
    look = family_look(hex_, fin, d.material if family_mode.family_of(d) else P.material_key(d.material))
    look["_meta"] = {**look["_meta"], "material_text": d.material}
    return look


def _ai_look(d) -> dict:
    """The look studio_cad.recolour / codegen give an AI model (material key, finish, colour of the direction)."""
    from api.cad.families import family_look
    from api.studio import product as P

    fin, _, hex_ = P.split_finish(d.finish)
    return family_look(hex_, fin, P.material_key(d.material))


def _regen_program(pre: Path, k: int, look: dict) -> bool:
    from api.cad.build import publish
    from api.cad.codegen.engine import program_names
    from api.cad.codegen.sandbox import run_code

    code = (pre / f"model_v{k}.py").read_text(encoding="utf-8")
    res = run_code(code, timeout_s=90)
    if not res.get("ok"):
        print(f"   model_v{k}: sandbox failed ({(res.get('error') or '')[:120]}) — finished in place")
        return False
    dst = pre / f"model_v{k}.glb"
    publish(res["files"]["glb"], dst)
    glb.finalize(dst, look, names=program_names(code, res))
    shutil.rmtree(res.get("work_dir") or "/nonexistent", ignore_errors=True)
    return True


def _regen_family_glb(pid: str, d, brief, dst: Path) -> bool:
    from api.cad import family_mode
    from api.cad.build import FAMILIES, normalize, publish
    from api.cad.look import build_assembly, features_for, look_for

    fam = family_mode.family_of(d)
    if fam:
        with tempfile.TemporaryDirectory() as tmp:
            res = family_mode.export_product(pid, d, "full", out_dir=Path(tmp))
            publish(res["files"]["glb"], dst)
        return True
    p = normalize(d.cad_parameters or {})
    f17 = FAMILIES.get(int(p["family"]))
    with tempfile.TemporaryDirectory() as tmp:
        tmp_glb = Path(tmp) / "asm.glb"
        build_assembly(p, tmp_glb, look_for(d.material, d.finish), set() if f17 in ("wearable_band", "ring") else features_for(brief))
        publish(tmp_glb, dst)
    return True


def _finish_in_place(path: Path) -> None:
    from pygltflib import GLTF2

    from api.cad.parts import fixed_names

    g = GLTF2.load(str(path))
    if glb.is_finished(g):
        return
    glb.finalize(path, None, names=fixed_names([n.name for n in g.nodes if n.mesh is not None and n.name]))


def _update_sizes(obj, sizes: dict[str, int]):
    if isinstance(obj, dict):
        url = obj.get("url")
        if isinstance(url, str) and "size_bytes" in obj and url.rsplit("/", 1)[-1] in sizes:
            obj["size_bytes"] = sizes[url.rsplit("/", 1)[-1]]
        for v in obj.values():
            _update_sizes(v, sizes)
    elif isinstance(obj, list):
        for v in obj:
            _update_sizes(v, sizes)


def _rewrite_json(path: Path, sizes: dict[str, int]) -> None:
    """Update size_bytes in a fixture JSON, keeping its formatting (indent, trailing newline)."""
    text = path.read_text()
    indent = 2 if text.startswith("{\n  ") else (1 if text.startswith("{\n ") else None)
    obj = json.loads(text)
    _update_sizes(obj, sizes)
    out = json.dumps(obj, indent=indent, ensure_ascii=False) + ("\n" if text.endswith("\n") else "")
    if out != text:
        path.write_text(out)


def regen_showcase(slug: str) -> dict:
    from contracts.artifacts import ARTIFACT_MODELS
    from api.studio import cad as studio_cad
    from api.studio import product as P

    ex = FIXTURES / f"showcase_{slug}"
    pre = PREBUILT_DIR / f"showcase_{slug}"
    pid = f"demo_{slug}"
    raw = json.loads((ex / "versions.json").read_text())
    before = {f.name: f.stat().st_size for f in pre.glob("*.glb")}
    snaps = {e["version"]["n"]: {int(k): ARTIFACT_MODELS[int(k)].model_validate(a) for k, a in e["snapshot"].items()} for e in raw["versions"]}
    versions = {e["version"]["n"]: e["version"] for e in raw["versions"]}
    done: set[str] = set()
    # 1. AI programs, with the look of the first version that shows them
    for f in sorted(pre.glob("model_v*.py"), key=lambda p: int(re.sub(r"\D", "", p.stem))):
        k = int(re.sub(r"\D", "", f.stem))
        n = next((n for n, v in sorted(versions.items()) if (v.get("preview") or {}).get("glb_url", "").endswith(f"model_v{k}.glb")), None)
        n = n or min(versions)
        d = P.chosen(snaps[n][2])
        if (pre / f"model_v{k}.glb").exists() and _regen_program(pre, k, _ai_look(d)):
            done.add(f"model_v{k}.glb")
    # 2. per version: recoloured AI copies + the full-product GLB
    for n, snap in sorted(snaps.items()):
        d = P.chosen(snap[2])
        spec = snap.get(3)
        if (pre / f"v{n}_ai.glb").exists() and spec is not None and (k := studio_cad.current_model(spec)) is not None \
                and (pre / f"model_v{k}.glb").exists():
            shutil.copyfile(pre / f"model_v{k}.glb", pre / f"v{n}_ai.glb")
            glb.recolour(pre / f"v{n}_ai.glb", _ai_look(d), overrides={})
            done.add(f"v{n}_ai.glb")
        if (pre / f"v{n}.glb").exists():
            try:
                _regen_family_glb(pid, d, snap.get(1), pre / f"v{n}.glb")
                done.add(f"v{n}.glb")
            except Exception as e:  # noqa: BLE001
                print(f"   v{n}.glb rebuild failed ({e}) — finished in place")
    last = snaps[max(snaps)]
    for d in last[2].directions if last.get(2) is not None else []:
        f = pre / f"{d.id}.glb"
        if f.exists() and f.name not in done:
            try:
                _regen_family_glb(pid, d, last.get(1), f)
                done.add(f.name)
            except Exception as e:  # noqa: BLE001
                print(f"   {f.name} rebuild failed ({e}) — finished in place")
    # 3. everything else: finished in place (own materials)
    for f in pre.glob("*.glb"):
        if f.name not in done and not f.name.startswith("anatomy_"):
            _finish_in_place(f)
    after = {f.name: f.stat().st_size for f in pre.glob("*.glb") if not f.name.startswith("anatomy_")}
    for name in ("versions.json", "03_cad_spec.json", "02_design.json", "factory_pack.json"):
        if (ex / name).exists():
            _rewrite_json(ex / name, after)
    return {k: (before.get(k), after[k]) for k in sorted(after)}


def regen_demo(example: str) -> dict:
    pre = PREBUILT_DIR / f"demo_{example}"
    before = {f.name: f.stat().st_size for f in pre.glob("*.glb")}
    for f in pre.glob("*.glb"):
        if not f.name.startswith("anatomy_"):
            _finish_in_place(f)
    after = {f.name: f.stat().st_size for f in pre.glob("*.glb") if not f.name.startswith("anatomy_")}
    for name in ("03_cad_spec.json", "02_design.json", "factory_pack.json"):
        if (FIXTURES / example / name).exists():
            _rewrite_json(FIXTURES / example / name, after)
    return {k: (before.get(k), after[k]) for k in sorted(after)}


def bake(pids: list[str]) -> dict:
    """In an isolated app (DB seeded by /demo/reset): /parts extras into each version's GLB + anatomy precomputed into
    the prebuilt folder. Needs DB_PATH / FILES_DIR / FACTORY_MCP_DB pointing at scratch locations."""
    from fastapi.testclient import TestClient

    from api.cad import anatomy as A
    from api.main import app
    from api.showcase import alias_dir
    from api.studio import store
    from api.studio.parts import enriched, version_context

    c = TestClient(app)
    assert c.post("/demo/reset").status_code == 200
    out = {}
    for pid in pids:
        pre = alias_dir(pid) or (PREBUILT_DIR / pid)
        ns = [v.n for v in store.list_versions(pid) if v.status == "done"] or [0]
        for n in ns:
            t0 = time.monotonic()
            ctx = version_context(pid, n)
            parts = enriched(ctx)
            if ctx.path.resolve().parent == pre.resolve():
                glb.set_extras(ctx.path, {p["part_id"]: p for p in parts})
            ctx = version_context(pid, n)
            an = A.build(ctx, out_dir=pre)
            out[f"{pid} v{n}"] = {"parts": len(parts), "anatomy_parts": len(an.parts), "layers": len(an.layers), "steps": len(an.steps),
                                  "anatomy_kb": (pre / f"anatomy_v{n}.glb").stat().st_size // 1024, "seconds": round(time.monotonic() - t0, 2)}
    return out


__all__ = ["regen_showcase", "regen_demo", "bake"]
