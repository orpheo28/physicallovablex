"""C5: pro detail for the recorded showcase AI programs (deterministic, no LLM).

A showcase's AI CAD program (model_v<k>.py) was written by the LLM from its seed family's code. At
CAD_DETAIL_LEVEL=pro the seed family's `# === PRO DETAIL ===` block (api.cad.stdparts screws, inserts, nuts, bosses,
gaskets…) is appended to the program, with the family parameters the program does not define (plus per-showcase
`FIT` overrides that line the family formulas up with the program's own geometry). The result is accepted only when
it runs in the sandbox and the C2 assembly engine measures no new interference and no floating hardware; otherwise
the program stays as recorded (reported, never forced).

    augment(code, seed_family, variant, fit=None) -> str | None     # the pro program, or None (no pro block)
    check(code, family) -> {"ok", "error", "interferences", "floating", "hardware", "fasteners"}
"""

from __future__ import annotations

import re
import shutil
from typing import Any

MARK = "# === PRO DETAIL === (C5:"

# per showcase: family parameters that place the hardware on the program's geometry (program P wins otherwise)
FIT: dict[str, dict[str, float]] = {
    # program arms reach 110 mm from the centre (family: arm_length + 0.35 × min(L, W)); its hub sits 0.35 mm lower
    "drone_follow": {"arm_length": 110.0 - 54.0 * 0.35, "motor_height": 26.65},
}
# per showcase: corrections of the recorded concept's own parameters, found by the C2 motion study
EDIT: dict[str, dict[str, float]] = {
    # 5-inch props on 83 mm arms overlapped each other (motors 100 mm apart, Ø127 mm) and swept the top battery
    "drone_follow": {"arm_reach": 110.0},
}
# per showcase: pro parts the recorded concept already draws (regex: lines dropped from the pro block)
DROP: dict[str, list[str]] = {
    "stick_vacuum": [r"^\s*(release = |kit\.append\(named\(release)"],  # the concept has its own release button on the bin collar
    # hardware the recorded geometry cannot host where the family formula puts it (C2 measured it floating)
    "changing_table": [r"kit\.append\(cam\.along"],  # rails drawn elsewhere: no cam in material (dowels + screws kept)
    "surfboard_beginner": [r"kit\.append\(leash_plug\("],  # deck surface differs from the family's: plug would float
}


def augment(code: str, seed_family: str | None, variant: str | None = None, fit: dict | None = None,
            drop: list[str] | None = None) -> str | None:
    from api.cad import families
    from api.cad.families._common import geometry_source, pro_source

    if MARK in code:
        return code
    try:
        mod = families.module(seed_family or "")
    except KeyError:
        return None
    pro = pro_source(mod)
    if not pro:
        return None
    base = {k: round(float(v), 3) for k, v in families.params_for(seed_family, variant).items()}
    fit = {k: round(float(v), 3) for k, v in (fit or {}).items()}
    geo = geometry_source(mod)
    defs = {m.group(1): m.group(0).rstrip() for m in re.finditer(r"^def (\w+)\(.*?(?=^def |^# ===|\Z)", geo, re.M | re.S)}
    need, todo = set(), [pro]
    while todo:  # family helpers the pro block calls, and theirs (copied under a `_f_` prefix: never the program's)
        for name in re.findall(r"\b(\w+)\(", todo.pop()):
            if name in defs and name not in need:
                need.add(name)
                todo.append(defs[name])

    def ren(text: str) -> str:
        return re.sub(r"\b(" + "|".join(sorted(need)) + r")\(", r"_f_\1(", text) if need else text

    helpers = "".join(ren(defs[n]) + "\n\n\n" for n in sorted(need))
    pro = ren(pro)
    for rx in drop or []:  # lines of the pro block the recorded concept already covers
        pro = "\n".join(ln for ln in pro.splitlines() if not re.search(rx, ln))
    code, n = re.subn(r"^def build\(\):", "def _basic_build():", code, count=1, flags=re.M)
    if not n:
        return None
    return (code.rstrip() + "\n\n\n"
            f"{MARK} the seed family '{seed_family}' CAD_DETAIL_LEVEL=pro block, appended deterministically, no LLM)\n"
            f"P_PRO = {{**{base!r}, **P, **{fit!r}}}\n\n\n"
            + helpers + pro.rstrip() + "\n\n\n"
            "def build():\n"
            "    r = _basic_build()\n"
            "    r = r[1] if isinstance(r, tuple) else r\n"
            "    parts = pro_details(P_PRO, list(r) if isinstance(r, list) else list(r.children))\n"
            "    return parts\n")


def edit_params(code: str, edits: dict[str, float]) -> str:
    """Set `"key": value` in the program's P dict (first occurrence), with a trailing note."""
    for k, v in edits.items():
        code, n = re.subn(rf'^(\s*"{k}":\s*)[-\d.]+,?[^\n]*$', rf'\g<1>{float(v)!r},  # C5: corrected (C2 motion study)',
                          code, count=1, flags=re.M)
        if not n:
            raise KeyError(f"{k} not in the program's P")
    return code


def prepare(slug: str, code: str, meta: dict) -> str | None:
    """The showcase program at pro: parameter corrections + the seed family's pro block (None: no pro block)."""
    if MARK in code:
        return code
    code = edit_params(code, EDIT.get(slug, {}))
    return augment(code, meta.get("seed_family"), meta.get("variant"), FIT.get(slug), DROP.get(slug))


def run(code: str, look: dict | None = None) -> tuple[dict, str | None]:
    """Sandbox run + finished GLB (names, look, hardware facts) in the sandbox work dir. (res, error)."""
    from pathlib import Path

    from api.cad.codegen.engine import finish_program_glb
    from api.cad.codegen.sandbox import run_code
    from api.cad.families import family_look

    res = run_code(code, timeout_s=120)
    if not res.get("ok"):
        return res, (res.get("error") or "sandbox failed")[:300]
    finish_program_glb(Path(res["files"]["glb"]), look or family_look(), code, res)
    return res, None


def measure(res: dict, family: str | None) -> dict[str, Any]:
    from api.cad.assembly import engine as E

    comps = E.load_step(res["files"]["step"], res["files"]["glb"])
    r = E.solve(comps, family)
    return {"interferences": sorted({f"{comps[x['a']].part_id} × {comps[x['b']].part_id}" for x in r.interferences
                                     if x["kind"] == "interference"}),
            "floating": sorted(comps[i].part_id for i in r.unsupported if comps[i].hardware),
            "hardware": sorted(c.part_id for c in comps if c.hardware),
            "fasteners": sum(u.qty for u in r.fastener_uses)}


def hardware_bom(res: dict) -> list[dict]:
    """BOM lines (api.cad.stdparts.bom.bom_lines) of the standard parts a sandbox run placed."""
    from types import SimpleNamespace

    from api.cad.stdparts.bom import bom_lines

    return bom_lines([SimpleNamespace(label=r["label"], std_meta=r["std_meta"]) for r in res.get("parts") or []
                      if isinstance(r.get("std_meta"), dict)])


def check(code: str, family: str | None) -> dict[str, Any]:
    res, err = run(code)
    try:
        if err:
            return {"ok": False, "error": err}
        return {"ok": True, "error": None, **measure(res, family), "bom": hardware_bom(res),
                "bbox_mm": res.get("bbox_mm"), "volume_mm3": res.get("volume_mm3"), "parts": res.get("parts")}
    finally:
        shutil.rmtree(res.get("work_dir") or "/nonexistent", ignore_errors=True)


def pro_programs(slug: str) -> list[dict]:
    """Step 1 of the C5 regeneration: each recorded AI program of the showcase gets its seed family's pro block when
    the C2 gate accepts it (runs; no floating hardware; no more interferences than the recorded concept). The program
    file and its meta (hardware BOM lines, measured bbox / volume / parts) are rewritten in place."""
    import json

    from api.cad.build import PREBUILT_DIR

    out = []
    for f in sorted((PREBUILT_DIR / f"showcase_{slug}").glob("model_v*.py")):
        meta_f = f.with_suffix(".json")
        meta = json.loads(meta_f.read_text()) if meta_f.exists() else {}
        code = f.read_text(encoding="utf-8")
        row: dict[str, Any] = {"program": f.name, "family": meta.get("seed_family")}
        if MARK in code:
            row["verdict"] = "already pro"
            out.append(row)
            continue
        aug = prepare(slug, code, meta)
        if aug is None:
            row["verdict"] = "no pro block for this family"
            out.append(row)
            continue
        fam = meta.get("seed_family")
        basic, pro = check(code, fam), check(aug, fam)
        row.update(basic_interferences=basic.get("interferences"), pro_interferences=pro.get("interferences"),
                   floating=pro.get("floating"), hardware=pro.get("hardware"), error=pro.get("error"))
        ok = pro.get("ok") and not pro.get("floating") and len(pro["interferences"]) <= len(basic.get("interferences") or [])
        row["verdict"] = "pro" if ok else "kept basic"
        if ok:
            f.write_text(aug, encoding="utf-8")
            meta.update(detail_level="pro", hardware_bom=pro["bom"], bbox_mm=pro["bbox_mm"], volume_mm3=pro["volume_mm3"],
                        parts=pro["parts"])
            meta_f.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        out.append(row)
    return out


__all__ = ["pro_programs", "hardware_bom", "augment", "prepare", "edit_params", "run", "measure", "check", "FIT", "EDIT", "DROP", "MARK"]


# --------------------------------------------------------------------------- fixtures: hardware in the stage-3 BOM


def _lines_for(pre, spec, design) -> list[dict]:
    """Hardware lines of one Studio version: its AI program's placed parts, else its family CAD at pro."""
    import json

    from api.cad import family_mode
    from api.cad.spec import hardware_lines
    from api.studio import cad as studio_cad
    from api.studio import product as P

    k = studio_cad.current_model(spec)
    if k is not None:
        f = pre / f"model_v{k}.json"
        return (json.loads(f.read_text()).get("hardware_bom") or []) if f.exists() else []
    d = P.chosen(design) if design is not None else None
    fam = family_mode.family_of(d) if d is not None else None
    return hardware_lines(fam, d, {}) if fam else []


def _merged_bom(spec, lines: list[dict]) -> list:
    from api.cad.spec import with_hardware

    base = [b for b in spec.bom if not b.id.startswith("hw")]
    return with_hardware(base, lines) if lines else base


def merge_fixture_bom(slug: str) -> dict[str, Any]:
    """Stage-3 BOM of every Studio version (and of the top-level fixture) = recorded BOM + the hardware counted on
    that version's CAD (ids hw…); a lump fastener line is replaced. Idempotent (old hw lines dropped first)."""
    import json

    from api.cad.build import PREBUILT_DIR
    from contracts.artifacts import ARTIFACT_MODELS

    ex = ROOT_FIXTURES / f"showcase_{slug}"
    pre = PREBUILT_DIR / f"showcase_{slug}"
    raw = json.loads((ex / "versions.json").read_text())
    cur_lines: list[dict] = []
    for e in raw["versions"]:
        snap = e["snapshot"]
        if "3" not in snap:
            continue
        spec = ARTIFACT_MODELS[3].model_validate(snap["3"])
        design = ARTIFACT_MODELS[2].model_validate(snap["2"]) if "2" in snap else None
        lines = _lines_for(pre, spec, design)
        spec.bom = _merged_bom(spec, lines)
        snap["3"] = spec.model_dump(mode="json")
        if e["version"]["n"] == raw["current"]:
            cur_lines = lines
    (ex / "versions.json").write_text(json.dumps(raw, ensure_ascii=False))
    f3 = ex / "03_cad_spec.json"
    spec = ARTIFACT_MODELS[3].model_validate_json(f3.read_text())
    spec.bom = _merged_bom(spec, cur_lines)
    f3.write_text(json.dumps(spec.model_dump(mode="json"), indent=1, ensure_ascii=False))
    return {"hw_lines": len(cur_lines), "hw_parts": sum(int(r["qty"]) for r in cur_lines)}


def _root_fixtures():
    from pathlib import Path

    return Path(__file__).resolve().parents[2] / "api" / "fixtures"


ROOT_FIXTURES = _root_fixtures()
