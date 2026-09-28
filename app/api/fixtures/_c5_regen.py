"""C5: regenerate the 11 showcases + 2 demos at CAD_DETAIL_LEVEL=pro (deterministic, no LLM, photos kept).

    DB_PATH=$(mktemp -d)/c5.db FILES_DIR=$(mktemp -d) FACTORY_MCP_DB=$(mktemp -d)/n.db OPENROUTER_API_KEY= \\
        uv run python -m api.fixtures._c5_regen [slugs…]

Per showcase: the recorded AI programs get their seed family's pro block when the C2 assembly gate accepts it
(api.cad._pro_regen), every GLB / labelled STEP is rebuilt (api.cad._w29_regen), the stage-3 BOM of every version
gets the hardware counted on its CAD (ids hw…), costs and the cost-dependent stages are recomputed
(_showcase.recompute_one). Demos: the chosen direction is rebuilt with its enclosure hardware (api.cad._prebuild).
Then parts extras + anatomy are baked, the engineering cache refreshed and the Factory Packs get the engineering
(assembly group) and the 2D drawings. Prints one JSON report line per project and a summary table.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from api.fixtures._showcase import ROOT, SHOWCASES, finish_fixture, recompute_one

FIX = ROOT / "api" / "fixtures"
DEMOS = ("desk_lamp", "tracker_card")
DEMO_PARAMS = {
    "desk_lamp": dict(family=0, length=120, width=120, height=22, fillet=20, edge_fillet=3, wall=2.2),
    "tracker_card": dict(family=2, length=85.6, width=54.0, height=2.8, fillet=3.5, edge_fillet=0.3, wall=0.5,
                         draft_deg=1.0, boss_count=0, split_ratio=0.5),
}


def _ex_dir(slug: str) -> Path:
    return FIX / (slug if slug in DEMOS else f"showcase_{slug}")


def _unit_at_ref(ex: Path) -> float | None:
    c = json.loads((ex / "05_costs.json").read_text())
    t = next((t for t in c.get("tiers", []) if t["quantity"] == c.get("reference_quantity")), None)
    return round(t["unit_cost"]["value"], 2) if t else None


def _glb_mb(slug: str) -> dict[str, float]:
    from api.cad.build import PREBUILT_DIR

    pre = PREBUILT_DIR / f"{'demo' if slug in DEMOS else 'showcase'}_{slug}"
    return {f.name: round(f.stat().st_size / 1e6, 2) for f in sorted(pre.glob("*.glb")) if not f.name.startswith("anatomy_")}


def demo_bom(example: str) -> dict:
    """Demo stage-3 BOM + the chosen direction's enclosure hardware (lamp base: screws + inserts; card: welded)."""
    from api.cad.spec import with_hardware
    from api.cad.stdparts import bom as hw_bom
    from api.cad.stdparts.enclosure import enclosure_details
    from contracts.artifacts import ARTIFACT_MODELS

    lines = hw_bom.bom_lines(enclosure_details(DEMO_PARAMS[example]))
    f3 = FIX / example / "03_cad_spec.json"
    spec = ARTIFACT_MODELS[3].model_validate_json(f3.read_text())
    spec.bom = with_hardware([b for b in spec.bom if not b.id.startswith("hw")], lines)
    f3.write_text(json.dumps(spec.model_dump(mode="json"), indent=1, ensure_ascii=False))
    return {"hw_lines": len(lines), "hw_parts": sum(int(r["qty"]) for r in lines)}


def finish_pack(slug: str) -> dict:
    """Assembly + drawings of the current version; the Factory Pack's BOM / costs (stage 3 / 5), engineering (with
    the assembly group) and drawings."""
    from api.cad.assembly import service as asm
    from api.cad.drawings import drawings
    from api.engineering.service import engineering_for_ctx
    from api.stages import runner
    from contracts.artifacts import FactoryPack

    pid = f"demo_{slug}"
    out: dict = {}
    try:
        a = asm.assembly_for(pid)
        bad = [f"{x.a} × {x.b}" for x in a.interferences if x.kind == "interference"]
        out.update(parts=len(a.nodes), interferences=len(bad), interference_pairs=bad,
                   assembly_fasteners=sum(int(b.qty) for b in a.fasteners), assembly=a.summary)
    except Exception as e:  # noqa: BLE001
        out["assembly_error"] = str(e)[:200]
    sheets: list = []
    try:
        sheets = drawings(pid)
        out["drawing_sheets"] = len(sheets)
    except Exception as e:  # noqa: BLE001
        out["drawings_error"] = str(e)[:200]
    f = _ex_dir(slug) / "factory_pack.json"
    if f.exists():
        fp = FactoryPack.model_validate_json(f.read_text())
        ctx = runner.build_context(pid, runner.FACTORY_PACK_STAGE)
        spec, costs = ctx.artifact(3), ctx.artifact(5)
        if spec is not None and costs is not None:
            lines = {ln.bom_item_id: ln for ln in costs.bom_lines}
            old = {b.id: b for b in fp.bom}
            bom = []
            for it in spec.bom:
                it = it.model_copy(deep=True)
                if it.id in old and old[it.id].risk is not None:
                    it.risk = old[it.id].risk
                if (ln := lines.get(it.id)) is not None:
                    it.unit_cost_est, it.lcsc_pn = ln.unit_price, ln.lcsc_pn
                bom.append(it)
            fp.bom, fp.cost_estimate, fp.target_quantities = bom, list(costs.tiers), [t.quantity for t in costs.tiers]
        fp.engineering = engineering_for_ctx(ctx)
        fp.drawings = sheets
        f.write_text(json.dumps(fp.model_dump(mode="json"), indent=1, ensure_ascii=False))
        out["pack"] = "engineering + drawings"
    return out


def run(slugs: list[str]) -> list[dict]:
    from api.cad import _prebuild
    from api.cad import _pro_regen as R
    from api.cad._w29_regen import bake, regen_demo, regen_showcase
    from api.cad.build import PREBUILT_DIR
    from api.cad.stdparts import is_pro

    if not is_pro():
        raise SystemExit("CAD_DETAIL_LEVEL is not pro — nothing to regenerate")
    slugs = slugs or [*SHOWCASES, *DEMOS]
    shows = [s for s in slugs if s in SHOWCASES]
    demos = [s for s in slugs if s in DEMOS]
    rep: dict[str, dict] = {s: {"slug": s, "unit_before": _unit_at_ref(_ex_dir(s)), "glb_mb_before": _glb_mb(s)} for s in slugs}
    for s in shows:
        t0 = time.monotonic()
        rep[s]["programs"] = R.pro_programs(s)
        regen_showcase(s)
        rep[s]["bom"] = R.merge_fixture_bom(s)
        rep[s]["cad_seconds"] = round(time.monotonic() - t0, 1)
        print(json.dumps({"step": "cad", "slug": s, "programs": [(p["program"], p["verdict"]) for p in rep[s]["programs"]],
                          "bom": rep[s]["bom"]}), flush=True)
    for s in demos:
        getattr(_prebuild, s)()
        regen_demo(s)
        rep[s]["bom"] = demo_bom(s)
        print(json.dumps({"step": "cad", "slug": s, "bom": rep[s]["bom"]}), flush=True)
    for s in shows:  # costs, stages 4/5/8/11/12, versions, engineering cache, gallery card (seeds its own project)
        r = recompute_one(_ex_dir(s))
        print(json.dumps({"step": "recompute", "slug": s, "unit": r["after"]["unit"]}), flush=True)
    print(json.dumps({"step": "bake", "projects": bake([f"demo_{s}" for s in slugs])}), flush=True)
    # demos keep their recorded stage 5: re-costing them with today's engine moves them for reasons unrelated to C5
    # (their costs predate the current price model); the counted hardware is in their stage-3 BOM and Factory Pack
    for s in slugs:  # after the bake (GLB extras rewritten): engineering cache + card, then the Factory Pack
        if s in SHOWCASES:
            finish_fixture(s, _ex_dir(s), PREBUILT_DIR / f"showcase_{s}")
        rep[s].update(finish_pack(s))
        rep[s]["unit_after"] = _unit_at_ref(_ex_dir(s))
        rep[s]["glb_mb_after"] = _glb_mb(s)
        print(json.dumps(rep[s], ensure_ascii=False), flush=True)
    return list(rep.values())


if __name__ == "__main__":
    rows = run(sys.argv[1:])
    print("\n| showcase | unit @ ref before → after | max GLB MB | interferences | drawing sheets | programs |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        progs = ", ".join(f"{p['program']}: {p['verdict']}" for p in r.get("programs", [])) or "—"
        print(f"| {r['slug']} | {r['unit_before']} → {r['unit_after']} | {max(r['glb_mb_after'].values(), default=0)} | "
              f"{r.get('interferences', r.get('assembly_error', '—'))} | {r.get('drawing_sheets', r.get('drawings_error', '—'))} | {progs} |")
