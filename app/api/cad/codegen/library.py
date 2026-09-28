"""Curated build123d example library for retrieval-augmented codegen (C4, behind CODEGEN_RAG).

    load_examples() -> list[Example]        # examples/*.py + measured facts from examples/index.json
    python -m api.cad.codegen.library --seeds     # (re)write examples/seed_<family>_<variant>.py from api.cad.families
    python -m api.cad.codegen.library --reindex   # run every example in the codegen sandbox, write index.json
    python -m api.cad.codegen.library --check a b  # run just these examples, print bbox / error (no write)

Every example is a complete sandbox-valid program (same conventions as the codegen prompt: `import math`,
`from build123d import *`, a `P` dict, `build()` returning labelled solids, Z up, on z=0). Its module docstring is
the retrieval metadata:

    \"\"\"<Title>.

    <one to three sentences: what it shows and when to use the idiom>
    tags: comma, separated, keywords
    \"\"\"

Sources: `seed_*` = our parametric families (api/cad/families), `generic_*` = the engine's generic seed, the rest are
hand-written idioms for this library. Ideas from Zero-To-CAD-1m / Text-to-CadQuery (CadQuery) were translated, never
copied — see examples/README.md for licences.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"
INDEX = EXAMPLES_DIR / "index.json"

# family -> variants worth keeping as distinct seeds (the geometry code is shared, proportions differ)
SEED_VARIANTS = {"board": ("surf", "kite"), "furniture": ("changing_table", "activity_table"),
                 "stick_vacuum": ("stick",), "home_robot": ("helper", "compact"), "irrigation": ("kit",),
                 "solar_array": ("roof",), "drone": ("follow", "mini"), "hair_dryer": ("pistol", "compact"),
                 "camera": ("compact", "instant"), "smartphone": ("slab", "mini")}
SEED_TAGS = {
    "board": "surfboard, kiteboard, board, hull, loft, rocker, rails, fins, hydrodynamic, sport",
    "furniture": "furniture, table, changing table, child, legs, rails, shelf, wood, frame",
    "stick_vacuum": "vacuum, cleaner, stick, wand, cyclone, bin, handle, floor head, appliance",
    "home_robot": "robot, home robot, wheels, torso, head, visor, arm, gripper, mast",
    "irrigation": "irrigation, controller, valve, probe, garden, housing, display, pipe",
    "solar_array": "solar, panel, pv, roof, array, rails, frame, cells",
    "drone": "drone, quadcopter, arms, propellers, motors, gimbal, camera, battery, skids, uav",
    "hair_dryer": "hair dryer, barrel, nozzle, handle, fan, duct, appliance, pistol grip",
    "camera": "camera, lens, barrel, grip, display, shutter, dial, viewfinder, instant, flash",
    "smartphone": "smartphone, phone, slab, glass, camera bump, buttons, usb-c, handheld",
}


@dataclass
class Example:
    id: str
    title: str
    description: str
    tags: list[str]
    code: str
    source: str  # seed | generic | idiom
    family: str | None = None
    facts: dict = field(default_factory=dict)  # bbox_mm, volume_mm3, n_parts, seconds, ok (from index.json)

    @property
    def bbox_mm(self) -> list[float] | None:
        return self.facts.get("bbox_mm")


def parse_header(code: str) -> tuple[str, str, list[str]]:
    """(title, description, tags) from the module docstring."""
    doc = ast.get_docstring(ast.parse(code)) or ""
    lines = [ln.strip() for ln in doc.splitlines()]
    tags: list[str] = []
    body: list[str] = []
    for ln in lines:
        if ln.lower().startswith("tags:"):
            tags = [t.strip().lower() for t in ln[5:].split(",") if t.strip()]
        else:
            body.append(ln)
    text = " ".join(x for x in body if x).strip()
    title, _, rest = text.partition(". ")
    return title.rstrip("."), rest.strip(), tags


@lru_cache(maxsize=1)
def _load() -> tuple[Example, ...]:
    facts = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    out = []
    for f in sorted(EXAMPLES_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        code = f.read_text(encoding="utf-8")
        title, desc, tags = parse_header(code)
        eid = f.stem
        source = "seed" if eid.startswith("seed_") else ("generic" if eid.startswith("generic_") else "idiom")
        family = next((k for k in SEED_VARIANTS if eid.startswith(f"seed_{k}_")), None) if source == "seed" else None
        fx = facts.get(eid, {})
        if fx and not fx.get("ok", True):
            continue  # a broken example must never be shown to the model
        out.append(Example(eid, title, desc, tags, code, source, family, fx))
    return tuple(out)


def load_examples() -> list[Example]:
    return list(_load())


# --------------------------------------------------------------------------- maintenance (CLI)


def write_seeds() -> list[Path]:
    from api.cad import families

    written = []
    for fam, variants in SEED_VARIANTS.items():
        m = families.module(fam)
        for v in variants:
            code = families.seed_code(m, families.params_for(fam, v))
            doc = (f'"""{fam.replace("_", " ").title()} ({v.replace("_", " ")}) — seed program of our parametric family.\n\n'
                   f"{m.DESCRIPTION} Full product: parameters dict P, geometry helpers, labelled parts.\n"
                   f"tags: {SEED_TAGS[fam]}, {v.replace('_', ' ')}\n\"\"\"\n")
            # replace the family's own one-line docstring with the library header
            body = code.split('"""', 2)[2].lstrip("\n")
            p = EXAMPLES_DIR / f"seed_{fam}_{v}.py"
            p.write_text(doc + body, encoding="utf-8")
            written.append(p)
    from api.cad.codegen.engine import GENERIC_SEED

    gen = ('"""Generic device — the engine\'s minimal conventions example.\n\n'
           "Rounded two-tone handheld device with a button and a status LED: rounded-rectangle extrusions, a top "
           "fillet in try/except, role labels.\n"
           "tags: generic, device, handheld, rounded, two-tone, button, led, enclosure, conventions\n\"\"\"\n"
           + GENERIC_SEED.split('"""', 2)[2].lstrip("\n"))
    (EXAMPLES_DIR / "generic_device.py").write_text(gen, encoding="utf-8")
    written.append(EXAMPLES_DIR / "generic_device.py")
    return written


def reindex(only: list[str] | None = None, write: bool = True) -> dict:
    """Run each example in the real sandbox (same policy as AI code) and store its measured facts."""
    import shutil

    from api.cad.codegen.sandbox import run_code

    facts = json.loads(INDEX.read_text()) if INDEX.exists() and only else {}
    for f in sorted(EXAMPLES_DIR.glob("*.py")):
        if f.name.startswith("_") or (only and f.stem not in only):
            continue
        res = run_code(f.read_text(encoding="utf-8"), timeout_s=25.0)
        row = {"ok": bool(res.get("ok")), "seconds": res.get("seconds_total", res.get("seconds"))}
        if res.get("ok"):
            row.update(bbox_mm=res["bbox_mm"], volume_mm3=res["volume_mm3"], n_parts=len(res["parts"]))
        else:
            row["error"] = (res.get("error") or "")[:400]
        facts[f.stem] = row
        print(f"{'ok ' if row['ok'] else 'ERR'} {f.stem:40s} {row.get('bbox_mm', row.get('error', ''))}")
        if res.get("work_dir"):
            shutil.rmtree(res["work_dir"], ignore_errors=True)
    if write:
        INDEX.write_text(json.dumps(facts, indent=1, sort_keys=True), encoding="utf-8")
        _load.cache_clear()
    return facts


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--seeds" in args:
        for p in write_seeds():
            print("wrote", p.name)
    if "--reindex" in args or "--check" in args:  # --check: run + print, index.json untouched
        rest = [a for a in args if not a.startswith("--")]
        facts = reindex(rest or None, write="--reindex" in args)
        bad = [k for k, v in facts.items() if not v["ok"]]
        print(f"{len(facts) - len(bad)}/{len(facts)} examples ok" + (f"; FAILED: {bad}" if bad else ""))
