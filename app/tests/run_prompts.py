"""Run the 10 test prompts of PRD Appendix A against a running API and write a Markdown report.

    uv run python tests/run_prompts.py                      # http://localhost:8000
    uv run python tests/run_prompts.py --base-url http://localhost:8106 --only 1,2,7

Per prompt: POST /projects → POST /autorun (202, async; polled every 2 s until stages 1-7 are done = "wow time") → stage 8 → stage 8 approve →
stages 9-13 → GET /factory-pack → GET /export. Per step: HTTP status, schema validity (contracts/artifacts.py),
fallback flag + reason, seconds. Prompts 7 and 8 run in prototype mode with a pasted BOM.

Exit code: non-zero on any 5xx, timeout, connection error, invalid artifact or empty PDF.
A stage that fell back to its cached fixture is a PASS but is counted and listed in the report.
Report: tests/results/<timestamp>.md
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from contracts.artifacts import STAGE_TITLES, AutorunResult, FactoryPack, Project, StageResult  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"

BOM_SMART_RING = """Part,Qty,Unit price (USD),Note
nRF52840 BLE SoC (aQFN-73),1,3.40,BLE 5 + Thread
BMA400 accelerometer,1,0.85,motion / sleep staging
MAX86141 optical AFE (PPG),1,2.10,heart rate + SpO2
MAX30208 skin temperature sensor,1,1.05,
Li-Po pouch cell 18 mAh,1,0.90,3.7 V
BQ25120A charger PMIC,1,0.95,
Flex PCB 4-layer polyimide,1,1.60,wraps inside the band
Titanium shell + epoxy potting,1,4.50,sizes 6-12
Charging contacts (gold pogo),2,0.10,
Charging cradle with USB-C,1,1.80,
"""

BOM_EINK_PHONE = """Part,Qty,Unit price (USD),Note
Rockchip RK3566 SoC,1,8.50,quad A55
4 GB LPDDR4X + 64 GB eMMC,1,9.20,
6.13 in e-ink display 1404x1872 with touch,1,38.00,greyscale
Quectel EC25-A LTE modem,1,14.50,Cat 4
Wi-Fi/BT module AP6256,1,3.20,
PMIC RK817,1,1.40,
Li-ion cell 3000 mAh pouch,1,3.10,UN38.3
USB-C connector 24P,1,0.20,
Aluminium unibody 6063 CNC,1,9.50,anodised
Front-light LED strip + light guide,1,1.10,
SIM tray + antenna set,1,1.70,
"""

PROMPTS: list[dict] = [
    {"n": 1, "mode": "idea", "prompt": "Magnetic rechargeable desk lamp, minimalist, sold €89"},
    {"n": 2, "mode": "idea", "prompt": "Bluetooth tracker card for wallets"},
    {"n": 3, "mode": "idea", "prompt": "Smart dog bowl that weighs food, Wi-Fi"},
    {"n": 4, "mode": "idea", "prompt": "Mechanical keyboard with hot-swap switches, aluminium case"},
    {"n": 5, "mode": "idea", "prompt": "Portable espresso maker, manual pump, no electronics"},
    {"n": 6, "mode": "idea", "prompt": "Kids' audio player with NFC figurines"},
    {"n": 7, "mode": "prototype", "prompt": "Smart ring measuring sleep", "pasted_bom": BOM_SMART_RING},
    {"n": 8, "mode": "prototype", "prompt": "E-ink phone, minimalist", "pasted_bom": BOM_EINK_PHONE},
    {"n": 9, "mode": "idea", "prompt": "Bike light with brake detection"},
    {"n": 10, "mode": "idea", "prompt": "Desktop air-quality monitor with CO2 sensor"},
]


@dataclass
class Step:
    name: str
    http: int | str = "-"
    valid: bool = True
    fallback: bool = False
    reason: str = ""
    seconds: float = 0.0
    failed: bool = False
    note: str = ""

    @property
    def status(self) -> str:
        return "FAIL" if self.failed else ("PASS (fallback)" if self.fallback else "PASS")


@dataclass
class PromptRun:
    n: int
    prompt: str
    mode: str
    project_id: str = ""
    steps: list[Step] = field(default_factory=list)
    wow_seconds: float | None = None
    total_seconds: float = 0.0

    @property
    def failed(self) -> bool:
        return any(s.failed for s in self.steps)

    @property
    def fallbacks(self) -> int:
        return sum(1 for s in self.steps if s.fallback)


class Runner:
    def __init__(self, base_url: str, timeout: float):
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=httpx.Timeout(timeout))

    def call(self, run: PromptRun, name: str, method: str, path: str, **kw) -> tuple[Step, httpx.Response | None]:
        step = Step(name)
        run.steps.append(step)
        t = time.perf_counter()
        resp: httpx.Response | None = None
        try:
            resp = self.client.request(method, path, **kw)
            step.http = resp.status_code
            if resp.status_code >= 500:
                step.failed, step.note = True, f"HTTP {resp.status_code}: {resp.text[:200]}"
            elif resp.status_code >= 400:
                step.failed, step.note = True, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except httpx.TimeoutException:
            step.http, step.failed, step.note = "timeout", True, "timeout"
        except httpx.HTTPError as e:
            step.http, step.failed, step.note = "error", True, f"{type(e).__name__}: {e}"
        step.seconds = time.perf_counter() - t
        return step, resp

    def autorun(self, run: PromptRun, pid: str) -> tuple[Step, dict | None]:
        """Async autorun as the web app does it: POST → 202, poll GET /projects/{id} every 2 s, then read stages 1-7."""
        step, resp = self.call(run, "autorun 1-7 (wow)", "POST", f"/projects/{pid}/autorun")
        if resp is None or step.failed:
            return step, None
        t = time.perf_counter() - step.seconds
        state = "running"
        while state == "running" and time.perf_counter() - t < 600:
            time.sleep(2)
            try:
                state = ((self.client.get(f"/projects/{pid}").json().get("autorun") or {}).get("state")) or "running"
            except (httpx.HTTPError, ValueError):
                pass
        step.seconds = time.perf_counter() - t
        if state != "done":
            step.failed, step.note = True, f"autorun state {state} after {step.seconds:.0f} s"
            return step, None
        results = []
        for n in range(1, 8):
            r = self.client.get(f"/projects/{pid}/stages/{n}")
            if r.status_code != 200:
                step.failed, step.note = True, f"stage {n} missing after autorun (HTTP {r.status_code})"
                return step, None
            results.append(r.json())
        return step, {"project_id": pid, "results": results}

    @staticmethod
    def check_stage(step: Step, resp: httpx.Response | None, stage: int | None = None) -> StageResult | None:
        if resp is None or step.failed:
            return None
        try:
            res = StageResult.model_validate(resp.json())
            if stage is not None and (res.stage != stage or res.artifact.stage != stage):
                raise ValueError(f"stage mismatch: expected {stage}, got {res.stage}/{res.artifact.stage}")
        except (ValidationError, ValueError) as e:
            step.valid, step.failed, step.note = False, True, f"invalid artifact: {str(e)[:300]}"
            return None
        step.fallback = bool(res.fallback)
        step.reason = (res.artifact.fallback_reason or "")[:160] if res.fallback else ""
        return res

    def run_prompt(self, spec: dict) -> PromptRun:
        run = PromptRun(spec["n"], spec["prompt"], spec["mode"])
        t_all = time.perf_counter()
        body = {"mode": spec["mode"], "prompt": spec["prompt"]}
        if spec.get("pasted_bom"):
            body["pasted_bom"] = spec["pasted_bom"]
        step, resp = self.call(run, "create project", "POST", "/projects", json=body)
        if step.failed or resp is None:
            run.total_seconds = time.perf_counter() - t_all
            return run
        try:
            run.project_id = Project.model_validate(resp.json()).id
        except ValidationError as e:
            step.valid, step.failed, step.note = False, True, f"invalid project: {str(e)[:200]}"
            run.total_seconds = time.perf_counter() - t_all
            return run
        pid = run.project_id

        # autorun (stages 1-7) = wow time
        step, resp = self.autorun(run, pid)
        run.wow_seconds = step.seconds
        if resp is not None and not step.failed:
            try:
                auto = AutorunResult.model_validate(resp)
                fb = [r for r in auto.results if r.fallback]
                if [r.stage for r in auto.results][-6:] != [2, 3, 4, 5, 6, 7]:
                    raise ValueError(f"unexpected stages {[r.stage for r in auto.results]}")
                step.fallback = bool(fb)
                step.reason = ("fallback stages " + ", ".join(str(r.stage) for r in fb) + ": " + (fb[0].artifact.fallback_reason or "")[:120]) if fb else ""
                for r in auto.results:
                    if r.fallback:
                        run.steps.append(Step(f"  autorun stage {r.stage} {STAGE_TITLES[r.stage]}", 200, True, True, (r.artifact.fallback_reason or "")[:160], 0.0, note="counted in autorun step"))
            except (ValidationError, ValueError) as e:
                step.valid, step.failed, step.note = False, True, f"invalid autorun result: {str(e)[:300]}"

        # stage 8 → approve
        step, resp = self.call(run, "stage 8 RFQ + negotiation", "POST", f"/projects/{pid}/stages/8/run", json={"inputs": {}})
        res = self.check_stage(step, resp, 8)
        quote_id = res.artifact.recommendation.quote_id if res is not None else None
        inputs = {"approve": True, **({"quote_id": quote_id} if quote_id else {})}
        step, resp = self.call(run, "stage 8 approve", "POST", f"/projects/{pid}/stages/8/run", json={"inputs": inputs})
        res = self.check_stage(step, resp, 8)
        if res is not None and not res.artifact.user_approved:
            step.note = "approve input not applied (user_approved=false)"

        for n in range(9, 14):
            step, resp = self.call(run, f"stage {n} {STAGE_TITLES[n]}", "POST", f"/projects/{pid}/stages/{n}/run", json={"inputs": {}})
            self.check_stage(step, resp, n)

        step, resp = self.call(run, "factory pack", "GET", f"/projects/{pid}/factory-pack")
        if resp is not None and not step.failed:
            try:
                fp = FactoryPack.model_validate(resp.json())
                step.fallback = fp.fallback
                step.reason = "pack has sections from a cached example" if fp.fallback else ""
                if not any(q.cn for q in fp.questions):
                    step.note = "no Chinese questions"
            except ValidationError as e:
                step.valid, step.failed, step.note = False, True, f"invalid factory pack: {str(e)[:300]}"

        step, resp = self.call(run, "export PDF", "GET", f"/projects/{pid}/export")
        if resp is not None and not step.failed:
            data = resp.content
            step.note = f"{len(data):,} bytes"
            if data[:4] != b"%PDF" or len(data) < 1500:
                step.valid, step.failed, step.note = False, True, f"empty or invalid PDF ({len(data)} bytes)"
        run.total_seconds = time.perf_counter() - t_all
        return run


def render(runs: list[PromptRun], base_url: str, started: datetime) -> str:
    fails = [r for r in runs if r.failed]
    lines = [
        f"# Prompt run — {started:%Y-%m-%d %H:%M:%S}",
        "",
        f"API: `{base_url}` · prompts run: {len(runs)} · passed: {len(runs) - len(fails)} · failed: {len(fails)} · "
        f"prompts with at least one fallback: {sum(1 for r in runs if r.fallbacks)}",
        "",
        "Fallback = pass but counted (stage served from its cached fixture). Wow time = `/autorun` (stages 1-7).",
        "",
        "| # | Prompt | Mode | Result | Wow time (s) | Total (s) | Fallback steps |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        lines.append(f"| {r.n} | {r.prompt[:60]} | {r.mode} | {'FAIL' if r.failed else 'PASS'} | {r.wow_seconds:.1f} | {r.total_seconds:.1f} | {r.fallbacks} |" if r.wow_seconds is not None else f"| {r.n} | {r.prompt[:60]} | {r.mode} | FAIL | – | {r.total_seconds:.1f} | {r.fallbacks} |")
    for r in runs:
        lines += ["", f"## Prompt {r.n} — {r.prompt}", "", f"Project `{r.project_id or '-'}` · mode {r.mode} · {'FAIL' if r.failed else 'PASS'}", "",
                  "| Step | HTTP | Schema | Result | Fallback reason / note | Seconds |", "|---|---|---|---|---|---|"]
        for s in r.steps:
            detail = (s.reason or s.note or "").replace("|", "/").replace("\n", " ")
            lines.append(f"| {s.name} | {s.http} | {'valid' if s.valid else 'INVALID'} | {s.status} | {detail} | {s.seconds:.2f} |")
    if fails:
        lines += ["", "## Failures", ""]
        for r in fails:
            for s in r.steps:
                if s.failed:
                    lines.append(f"- Prompt {r.n}, {s.name}: HTTP {s.http} — {s.note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:8000", help="API base URL (default: http://localhost:8000)")
    ap.add_argument("--only", default="", help="comma-separated prompt numbers to run, e.g. 1,2,7 (default: all 10)")
    ap.add_argument("--timeout", type=float, default=180.0, help="per-request timeout in seconds (default 180)")
    ap.add_argument("--out-dir", default=str(RESULTS_DIR), help="where to write the Markdown report")
    args = ap.parse_args()

    wanted = {int(x) for x in args.only.split(",") if x.strip()} if args.only else None
    specs = [p for p in PROMPTS if wanted is None or p["n"] in wanted]
    if not specs:
        print("no prompts selected", file=sys.stderr)
        return 2

    runner = Runner(args.base_url, args.timeout)
    try:
        runner.client.get("/health", timeout=10).raise_for_status()
    except httpx.HTTPError as e:
        print(f"API not reachable at {args.base_url}: {e}", file=sys.stderr)
        return 2

    started = datetime.now()
    runs: list[PromptRun] = []
    for spec in specs:
        print(f"[{spec['n']:>2}] {spec['prompt'][:70]} ...", flush=True)
        run = runner.run_prompt(spec)
        runs.append(run)
        print(f"     {'FAIL' if run.failed else 'PASS'} · wow {run.wow_seconds if run.wow_seconds is None else round(run.wow_seconds, 1)}s · total {run.total_seconds:.1f}s · fallbacks {run.fallbacks}", flush=True)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{started:%Y%m%d-%H%M%S}.md"
    path.write_text(render(runs, args.base_url, started))
    failed = sum(1 for r in runs if r.failed)
    print(f"\n{len(runs) - failed}/{len(runs)} passed · fallbacks in {sum(1 for r in runs if r.fallbacks)} prompts · report: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
