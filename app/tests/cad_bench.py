"""CAD codegen benchmark (C4): 20 fixed prompts, CODEGEN_RAG=0 vs 1, same model, live. Not collected by pytest.

    uv run python tests/cad_bench.py run --rag 0 [--only id,id] [--budget 0.70] [--workers 5]
    uv run python tests/cad_bench.py run --rag 1
    uv run python tests/cad_bench.py render        # Blender renders → docs/screens/cad_bench/<id>_rag{0,1}.png + sheet
    uv run python tests/cad_bench.py report        # table → docs/CAD_BENCH.md (between the BENCH markers)

The LLM call mirrors api.llm.complete_text (route "main", max_tokens 7000, same reasoning setting) but asks
OpenRouter for per-call usage so the cost of every run is exact. Each prompt runs the real engine
(api.cad.codegen.generate_cad: sandbox, validation, up to 2 repairs, fallback) with the target size given.

Metrics per mode: valid first try (status ok), valid after repair (ok | repaired), mean repairs (attempts - 1),
bbox within ±25 % of the target on every sorted extent (AI result only; a fallback counts as a miss), seconds, $.
Raw rows: tests/results/cad_bench/rag{0,1}.json (plus the generated programs + GLBs next to them).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "tests" / "results" / "cad_bench"
SCREENS = ROOT / "docs" / "screens" / "cad_bench"
DOC = ROOT / "docs" / "CAD_BENCH.md"
TOL = 0.25
SUF = os.getenv("CAD_BENCH_RUN", "")  # e.g. "_r2": a repeat run with its own rows, programs, renders and judge keys

# id, brief, (L, W, H) mm. 11 product categories + 9 harder mechanical parts.
PROMPTS: list[tuple[str, str, tuple[float, float, float]]] = [
    ("changing_table", "Compact wall-side baby changing table with raised safety edges, a padded top and one open shelf",
     (800, 520, 950)),
    ("stick_vacuum", "Lightweight cordless stick vacuum with a clear dust bin, pistol grip and a slim floor head",
     (250, 240, 1150)),
    ("home_robot", "Friendly wheeled home assistant robot with a round head, screen face and one arm", (450, 420, 950)),
    ("irrigation", "Solar garden irrigation controller with a small display, a solenoid valve and a soil probe",
     (420, 90, 220)),
    ("surfboard", "Shortboard surfboard with three fins and a rounded squash tail", (1830, 510, 150)),
    ("desk_lamp", "Minimal LED desk lamp with a round weighted base, a slim upright arm and a flat circular head",
     (220, 180, 420)),
    ("ble_tag", "Bluetooth key finder tag with a keyring hole, a press button and a status LED", (42, 42, 9)),
    ("drone", "Foldable camera drone with four arms, propellers, a gimbal camera and landing skids", (330, 360, 110)),
    ("hair_dryer", "Travel hair dryer with a folding-style handle, a concentrator nozzle and an intake filter",
     (220, 75, 200)),
    ("camera", "Retro instant camera with a big lens, a flash window, a viewfinder and a print slot", (150, 115, 120)),
    ("smartphone", "Compact smartphone with a triple camera bump, side buttons and a USB-C port", (70, 145, 9)),
    # harder mechanical parts
    ("hinge", "Stainless butt hinge: two leaves with three alternating knuckles, a pin and countersunk screw holes",
     (76, 64, 6)),
    ("threaded_cap", "Screw cap for a 38 mm bottle neck with an internal thread and grip ribs around the outside",
     (44, 44, 20)),
    ("gear", "Spur gear, 24 teeth, module 2, with a bore, a keyway and a raised hub", (52, 52, 16)),
    ("curved_handle", "Curved cabinet pull handle: a round bar swept along an arc with two mounting posts",
     (160, 25, 35)),
    ("vented_grille", "Rectangular fan grille plate with a grid of rounded vent slots and four corner screw holes",
     (120, 120, 4)),
    ("battery_door", "Battery compartment door for a remote: sliding cover with a latch tab and finger grip ridges",
     (45, 30, 4)),
    ("cable_gland", "M20 cable gland: hex body, threaded stem, domed sealing cap nut", (28, 28, 40)),
    ("spring_clip", "Snap-on spring clip for a 20 mm tube: C-shaped jaws with a flat screw-mount base", (32, 24, 30)),
    ("shelf_bracket", "Steel shelf bracket: L-shaped with a diagonal gusset and two screw holes on each leg",
     (150, 30, 200)),
]


# must-have visible features per prompt, scored blind on the render by a vision judge (another model family)
FEATURES: dict[str, list[str]] = {
    "changing_table": ["raised safety edges around the top", "padded changing top", "open shelf below", "legs or side panels"],
    "stick_vacuum": ["long slim wand", "floor head at the bottom", "dust bin", "pistol-style handle"],
    "home_robot": ["wheeled base", "round head", "screen face", "an arm"],
    "irrigation": ["controller housing with a display", "valve body with pipe ports", "soil probe / spike"],
    "surfboard": ["pointed-nose board outline", "three fins", "squash (blunt rounded) tail"],
    "desk_lamp": ["round base", "slim upright arm", "flat circular lamp head"],
    "ble_tag": ["small flat tag", "keyring hole", "button", "status LED"],
    "drone": ["four arms", "four propellers", "gimbal camera", "landing skids"],
    "hair_dryer": ["barrel", "handle", "concentrator nozzle", "intake filter at the back"],
    "camera": ["large lens", "flash window", "viewfinder", "print slot"],
    "smartphone": ["thin slab", "camera bump with three lenses", "side buttons", "USB-C port"],
    "hinge": ["two flat leaves", "alternating knuckles", "pin along the knuckles", "countersunk screw holes"],
    "threaded_cap": ["round cap", "grip ribs around the outside", "thread (visible inside or implied)"],
    "gear": ["spur gear teeth all around", "central bore", "keyway", "raised hub"],
    "curved_handle": ["curved round bar", "two mounting posts"],
    "vented_grille": ["flat rectangular plate", "grid of rounded slots", "four corner screw holes"],
    "battery_door": ["thin flat cover", "latch tab", "finger grip ridges"],
    "cable_gland": ["hex body", "threaded stem", "domed cap nut"],
    "spring_clip": ["C-shaped jaws", "flat base", "screw hole in the base"],
    "shelf_bracket": ["L-shape with two legs", "diagonal gusset", "screw holes on each leg"],
}
JUDGE_MODEL = os.getenv("CAD_BENCH_JUDGE", "google/gemini-3.8-flash")


class BenchLLM:
    """(prompt, system) -> text, like api.llm.complete_text('main', …, max_tokens=7000), recording usage and cost."""

    def __init__(self, budget: float):
        self.budget, self.spent, self.calls = budget, 0.0, []
        self.lock = threading.Lock()
        self.local = threading.local()  # .rows: the calls made by the current thread's prompt

    def __call__(self, prompt: str, system: str) -> str:
        from api.llm import LLMBudgetExceeded, LLMError, _client, _count_request, _reasoning, model_for

        with self.lock:
            if self.spent >= self.budget:
                raise LLMBudgetExceeded("main", f"bench budget ${self.budget:.2f} reached")
        _count_request("main")
        extra = _reasoning().get("extra_body", {})
        t = time.monotonic()
        try:
            resp = _client().chat.completions.create(
                model=model_for("main"), max_tokens=min(7000, int(os.getenv("LLM_MAX_TOKENS", "8000"))),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                extra_body={**extra, "usage": {"include": True}})
        except Exception as e:  # noqa: BLE001
            raise LLMError("main", f"request failed: {e}") from e
        u = getattr(resp, "usage", None)
        cost = float(getattr(u, "cost", 0) or (u.model_extra or {}).get("cost", 0) if u else 0)
        row = {"seconds": round(time.monotonic() - t, 1), "prompt_tokens": getattr(u, "prompt_tokens", None),
               "completion_tokens": getattr(u, "completion_tokens", None), "cost": cost, "prompt_chars": len(prompt),
               "system_chars": len(system)}
        with self.lock:
            self.spent += cost
            self.calls.append(row)
        getattr(self.local, "rows", []).append(row)
        content = resp.choices[0].message.content if resp.choices else None
        if not content:
            raise LLMError("main", "empty completion")
        return content


def within(bbox, dims, tol=TOL) -> bool:
    return all(abs(g - w) <= tol * w for g, w in zip(sorted(bbox), sorted(dims)))


def run_one(pid: str, brief: str, dims, rag: int, budget_llm: BenchLLM) -> dict:
    from api.cad.codegen import generate_cad

    out = OUT / f"rag{rag}{SUF}" / pid
    if out.exists():
        for f in out.iterdir():
            f.unlink()
    t = time.monotonic()
    calls: list[dict] = []
    budget_llm.local.rows = calls
    try:
        r = generate_cad(brief, dims=dims, out_dir=out, llm=budget_llm, max_repairs=2)
    except Exception as e:  # noqa: BLE001
        r = {"status": "error", "notes": [f"{type(e).__name__}: {e}"], "attempts": []}
    ok = r.get("status") in ("ok", "repaired")
    bbox = r.get("bbox_mm")
    return {
        "id": pid, "rag": rag, "status": r.get("status"), "first_try": r.get("status") == "ok", "valid": ok,
        "repairs": max(0, len(r.get("attempts") or []) - 1), "bbox_mm": bbox, "target_mm": list(dims),
        "bbox_ok": bool(ok and bbox and within(bbox, dims)), "seconds": round(time.monotonic() - t, 1),
        "cost": round(sum(c["cost"] for c in calls), 5), "calls": calls, "examples": (r.get("rag") or {}).get("examples"),
        "errors": [(a.get("error_kind"), (a.get("error") or "")[:500]) for a in r.get("attempts") or [] if a.get("error")],
        "n_parts": len(r.get("parts") or []),
        "invalid_parts": sum(1 for q in r.get("parts") or [] if q.get("valid") is False), "glb": (r.get("files") or {}).get("glb"), "notes": r.get("notes"),
    }


def cmd_run(a) -> None:
    os.environ["CODEGEN_RAG"] = str(a.rag)
    from api.cad.codegen import retrieval

    retrieval.reset()
    only = set(a.only.split(",")) if a.only else None
    todo = [p for p in PROMPTS if not only or p[0] in only]
    llm = BenchLLM(a.budget)
    path = OUT / f"rag{a.rag}{SUF}.json"
    rows = {r["id"]: r for r in json.loads(path.read_text())} if (only and path.exists()) else {}
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(run_one, pid, brief, dims, a.rag, llm): pid for pid, brief, dims in todo}
        for f in as_completed(futs):
            r = f.result()
            rows[r["id"]] = r
            print(f"[rag{a.rag}{SUF}] {r['id']:15s} {r['status']:9s} repairs={r['repairs']} bbox_ok={r['bbox_ok']} "
                  f"{r['seconds']:5.1f}s ${r['cost']:.4f}  spent=${llm.spent:.3f}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    order = [p[0] for p in PROMPTS]
    path.write_text(json.dumps(sorted(rows.values(), key=lambda r: order.index(r["id"])), indent=1, default=str))
    print(f"rag{a.rag}{SUF}: spent ${llm.spent:.3f} over {len(llm.calls)} calls → {path}")


def summary(rows: list[dict], judged: dict | None = None) -> dict:
    n = len(rows) or 1
    js = [judged[f"{r['id']}_rag{r['rag']}{SUF}"] for r in rows if judged and f"{r['id']}_rag{r['rag']}{SUF}" in judged]
    return {"coverage": sum(j["coverage"] for j in js) / max(1, len(js)) if js else None,
            "recognisable": sum(float(j["recognisable"] or 0) for j in js) / max(1, len(js)) if js else None,
            "n": len(rows), "first_try": sum(r["first_try"] for r in rows) / n, "valid": sum(r["valid"] for r in rows) / n,
            "repairs": sum(r["repairs"] for r in rows) / n, "bbox_ok": sum(r["bbox_ok"] for r in rows) / n,
            "seconds": sum(r["seconds"] for r in rows) / n,
            "all_valid": sum(1 for r in rows if r["valid"] and not r.get("invalid_parts")) / n, "cost": sum(r["cost"] for r in rows),
            "prompt_tokens": sum(c.get("prompt_tokens") or 0 for r in rows for c in r["calls"]) / max(1, sum(len(r["calls"]) for r in rows))}


def cmd_render(a) -> None:
    from PIL import Image, ImageDraw

    SCREENS.mkdir(parents=True, exist_ok=True)
    rows = {rag: {r["id"]: r for r in json.loads((OUT / f"rag{rag}{SUF}.json").read_text())} for rag in (0, 1)
            if (OUT / f"rag{rag}{SUF}.json").exists()}
    jobs = []
    for rag, rr in rows.items():
        for pid, r in rr.items():
            png = SCREENS / f"{pid}_rag{rag}{SUF}.png"
            if r.get("glb") and Path(r["glb"]).exists() and (a.force or not png.exists()):
                jobs.append((r["glb"], png))

    def render(job):
        glb, png = job
        for _ in range(3):  # a parallel Blender run occasionally exits without writing; retry
            subprocess.run(["blender", "-b", "-P", str(ROOT / "api/cad/_blender_render.py"), "--", glb, str(png), "480",
                            "12"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240)
            if png.exists():
                break
        return png

    with ThreadPoolExecutor(3) as ex:
        for png in ex.map(render, jobs):
            print("rendered", png.name, png.exists())
    # contact sheet: one row per prompt, RAG=0 | RAG=1
    cell, pad = 240, 26
    sheet = Image.new("RGB", (2 * cell + 170, len(PROMPTS) * (cell + 4) + pad), "#F7F6F3")
    d = ImageDraw.Draw(sheet)
    d.text((180, 6), "CODEGEN_RAG=0", fill="#222")
    d.text((180 + cell, 6), "CODEGEN_RAG=1", fill="#222")
    for i, (pid, *_rest) in enumerate(PROMPTS):
        y = pad + i * (cell + 4)
        d.text((8, y + cell // 2 - 6), pid, fill="#222")
        for j, rag in enumerate((0, 1)):
            r = rows.get(rag, {}).get(pid)
            png = SCREENS / f"{pid}_rag{rag}{SUF}.png"
            x = 170 + j * cell
            if png.exists():
                sheet.paste(Image.open(png).convert("RGB").resize((cell, cell)), (x, y))
            if r:
                tag = {"ok": "first try", "repaired": f"repaired x{r['repairs']}"}.get(r["status"], r["status"])
                d.text((x + 6, y + 6), tag + ("" if r["bbox_ok"] else " · size off"), fill="#B00" if not r["valid"] else "#060")
    sheet.save(SCREENS / f"sheet{SUF}.png")
    print("sheet →", SCREENS / f"sheet{SUF}.png")


def cmd_judge(a) -> None:
    """Blind vision judge: for each render, which must-have features are visible + how recognisable (1-5)."""
    import base64

    from api.llm import _client

    path = OUT / "judge.json"
    done = json.loads(path.read_text()) if path.exists() and not a.force else {}
    briefs = {pid: brief for pid, brief, _ in PROMPTS}
    jobs = [(pid, rag) for pid in FEATURES for rag in (0, 1)
            if (SCREENS / f"{pid}_rag{rag}{SUF}.png").exists()
            and (done.get(f"{pid}_rag{rag}{SUF}") or {}).get("recognisable") is None]
    spent = [0.0]

    def judge(job):
        pid, rag = job
        img = base64.b64encode((SCREENS / f"{pid}_rag{rag}{SUF}.png").read_bytes()).decode()
        feats = FEATURES[pid]
        q = (f"This is a render of a 3D CAD model. It was meant to be: \"{briefs[pid]}\".\n"
             "Judge only what is visible. For each feature answer true if it is clearly present in the model, false "
             "otherwise. Then rate how recognisable the object is as the intended product from 1 (not at all) to 5 "
             "(instantly). Reply with JSON only: {\"features\": {<feature>: true|false, ...}, \"recognisable\": n, "
             "\"comment\": \"<max 15 words>\"}.\nFeatures: " + json.dumps(feats))
        for _ in range(3):  # an empty / truncated reply is retried
            d = ask(q, img)
            if isinstance(d.get("recognisable"), (int, float)):
                break
        vals = [bool(d.get("features", {}).get(f)) for f in feats]
        return f"{pid}_rag{rag}{SUF}", {"features": dict(zip(feats, vals)), "coverage": sum(vals) / len(vals),
                                   "recognisable": d.get("recognisable"), "comment": d.get("comment")}

    def ask(q, img):
        resp = _client().chat.completions.create(
            model=JUDGE_MODEL, temperature=0, max_tokens=2000, extra_body={"usage": {"include": True}},
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": [{"type": "text", "text": q}, {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{img}"}}]}])
        u = resp.usage
        spent[0] += float(getattr(u, "cost", 0) or (u.model_extra or {}).get("cost", 0) or 0)
        txt = resp.choices[0].message.content or "{}"
        try:
            return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        except ValueError:
            return {}

    with ThreadPoolExecutor(6) as ex:
        for key, v in ex.map(judge, jobs):
            done[key] = v
            print(key, f"{v['coverage']:.2f}", v["recognisable"], v["comment"])
    path.write_text(json.dumps(done, indent=1, sort_keys=True))
    print(f"judge spent ${spent[0]:.4f}")


def cmd_report(a) -> None:
    rows = {rag: json.loads((OUT / f"rag{rag}{SUF}.json").read_text()) for rag in (0, 1) if (OUT / f"rag{rag}{SUF}.json").exists()}
    jp = OUT / "judge.json"
    judged = json.loads(jp.read_text()) if jp.exists() else {}
    s = {rag: summary(r, judged) for rag, r in rows.items()}
    pct = lambda v: f"{100 * v:.0f} %"  # noqa: E731
    lines = ["| metric | CODEGEN_RAG=0 | CODEGEN_RAG=1 |", "|---|---|---|"]
    for key, label, fmt in (("n", "prompts", str), ("first_try", "valid first try", pct), ("valid", "valid after repair", pct),
                            ("repairs", "mean repairs", lambda v: f"{v:.2f}"),
                            ("bbox_ok", f"bbox within ±{int(TOL * 100)} % of target", pct),
                            ("all_valid", "all parts pass OCCT is_valid", pct),
                            ("coverage", "must-have features visible (vision judge)", lambda v: "—" if v is None else pct(v)),
                            ("recognisable", "recognisable, 1–5 (vision judge)", lambda v: "—" if v is None else f"{v:.2f}"),
                            ("seconds", "mean seconds / prompt", lambda v: f"{v:.0f}"),
                            ("prompt_tokens", "mean prompt tokens / call", lambda v: f"{v:,.0f}"),
                            ("cost", "total cost (USD)", lambda v: f"${v:.3f}")):
        lines.append(f"| {label} | " + " | ".join(fmt(s[r][key]) if r in s else "—" for r in (0, 1)) + " |")
    per = ["", "| prompt | target mm | RAG=0 | RAG=1 | examples retrieved (RAG=1) |", "|---|---|---|---|---|"]
    by = {rag: {r["id"]: r for r in rr} for rag, rr in rows.items()}

    def cell(r):
        if not r:
            return "—"
        st = {"ok": "✅ first try", "repaired": f"🔧 {r['repairs']} repair{'s' if r['repairs'] > 1 else ''}"}.get(
            r["status"], f"❌ {r['status']}")
        size = "" if not r.get("bbox_mm") else f" · {'/'.join(str(round(v)) for v in r['bbox_mm'])}" + ("" if r["bbox_ok"] else " ⚠")
        j = judged.get(f"{r['id']}_rag{r['rag']}{SUF}")
        feat = f" · feat {sum(j['features'].values())}/{len(j['features'])}" if j else ""
        return f"{st}{size}{feat} · {r['seconds']:.0f}s"

    for pid, _b, dims in PROMPTS:
        r1 = by.get(1, {}).get(pid)
        ex = ", ".join(f"`{e}`" for e in (r1 or {}).get("examples") or []) or "—"
        per.append(f"| {pid} | {'/'.join(str(round(v)) for v in dims)} | {cell(by.get(0, {}).get(pid))} | {cell(r1)} | {ex} |")
    table = "\n".join(lines + per)
    start, end = f"<!-- BENCH{SUF}:START -->", f"<!-- BENCH{SUF}:END -->"
    txt = DOC.read_text() if DOC.exists() else ""
    if start not in txt:
        txt += f"\n{start}\n{end}\n"
    head, _, rest = txt.partition(start)
    _, _, tail = rest.partition(end)
    DOC.write_text(f"{head}{start}\n{table}\n{end}{tail}")
    print(table)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("--rag", type=int, choices=(0, 1), required=True)
    r.add_argument("--only", default="")
    r.add_argument("--budget", type=float, default=0.70)
    r.add_argument("--workers", type=int, default=5)
    rr = sp.add_parser("render")
    rr.add_argument("--force", action="store_true")
    j = sp.add_parser("judge")
    j.add_argument("--force", action="store_true")
    sp.add_parser("report")
    a = ap.parse_args()
    {"run": cmd_run, "render": cmd_render, "judge": cmd_judge, "report": cmd_report}[a.cmd](a)
