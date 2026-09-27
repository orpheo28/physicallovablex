"""Structured part edits (W29): POST /projects/{id}/parts/{part_id}/edit — a deterministic refine, no LLM.

    submit(pid, part_id, PartEditRequest) -> n     # validates (Invalid → 422), queues version n on the Studio worker

Three kinds, one version each (FIFO with the prompt refines, same commit / photo / background / engineering path):
- look of a body part (the product colour / material): the refine ops set_color / set_material, applied by
  api.studio.apply exactly like a prompt ("Top shell colour → Sage (#9DB09A)");
- look of any other part (strap, window, button…): a per-part override baked into the version's GLB (`v<n>_ai.glb`
  or `v<n>.glb`; stored in the GLB root extras so later recolours keep it); a material change re-costs the matching
  spec part (stage 5 code, Estimate) — no matching part → cost unchanged, said so;
- a parameter: the AI CAD program's `P[...]` literal (re-run in the sandbox, measured) and / or the family / enclosure
  parameter it drives → CAD, spec, DFM, costs, shortlist recomputed by api.studio.apply ("Pod thickness 10.0 → 9.0 mm
  (Measured)").
"""

from __future__ import annotations

import ast
import json
import logging
import re
import time

from api.cad import glb
from api.cad.build import project_dir, publish
from api.stages import runner
from api.studio import engine as E
from api.studio import product as P
from api.studio import store
from api.studio.parts import ENCLOSURE_SYNC, look_of, param_spec, version_context
from contracts.artifacts import Label, PartEditRequest, Version, VersionChange, VersionStatus

log = logging.getLogger("studio.edit")


class Invalid(ValueError):
    pass


# --------------------------------------------------------------------------- helpers


def colour_name(hex_: str) -> str:
    """'#9DB09A' → 'Sage' (exact or nearest named colour within a small distance), else 'Custom'."""
    from api.cad.look import COLOURS

    h = hex_.upper()
    for name, v in COLOURS.items():
        if v.upper() == h:
            return name.title()
    rgb = [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    best = min(COLOURS.items(), key=lambda kv: sum((int(kv[1][i:i + 2], 16) - c) ** 2 for i, c in zip((1, 3, 5), rgb)))
    d = sum((int(best[1][i:i + 2], 16) - c) ** 2 for i, c in zip((1, 3, 5), rgb)) ** 0.5
    return best[0].title() if d < 24 else "Custom"


def _short(material: str | None) -> str:
    return (material or "").split(" (")[0].strip() or "—"


def _money(v: float) -> str:
    return f"{'+' if v >= 0 else '−'}${abs(v):,.2f}"


def _ref_unit(costs) -> float | None:
    r = P._ref_unit(costs)
    return r[0] if r else None


def _hex(v: str | None) -> str | None:
    if v is None:
        return None
    if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", v.strip()):
        raise Invalid(f"colour_hex {v!r} is not #RRGGBB")
    return "#" + v.strip().lstrip("#").upper()


def set_program_param(code: str, key: str, value: float) -> str:
    """Rewrite the literal of `P["key"]` in the program's top-level `P = {...}` dict (formatting elsewhere untouched)."""
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "P" for t in node.targets) \
                and isinstance(node.value, ast.Dict):
            for k, v in zip(node.value.keys, node.value.values):
                if isinstance(k, ast.Constant) and k.value == key:
                    lines = code.splitlines(keepends=True)
                    if v.lineno != v.end_lineno:
                        raise Invalid(f"parameter {key!r} is not a simple literal")
                    old = ast.literal_eval(v)
                    lit = str(int(round(value))) if isinstance(old, int) and not isinstance(old, bool) else repr(round(float(value), 3))
                    ln = lines[v.lineno - 1]
                    b = len(ln.encode()[:v.col_offset].decode())
                    e = len(ln.encode()[:v.end_col_offset].decode())
                    lines[v.lineno - 1] = ln[:b] + lit + ln[e:]
                    return "".join(lines)
    raise Invalid(f"parameter {key!r} is not in the program's P dict")


# --------------------------------------------------------------------------- validation → plan


def plan(pid: str, part_id: str, req: PartEditRequest) -> dict:
    """What to do, validated against the current version (Invalid → 422, runner.NotFound → 404)."""
    if all(getattr(req, f) is None for f in ("colour_hex", "material", "finish", "param", "value")):
        raise Invalid("empty edit: give colour_hex, material, finish or param + value")
    if (req.param is None) != (req.value is None):
        raise Invalid("param and value go together")
    ctx = version_context(pid, None)
    if ctx.n == 0:
        raise E.Conflict("Start the Studio first: POST /projects/{id}/studio/start")
    from api.studio.parts import enriched

    parts = {p["part_id"]: p for p in enriched(ctx)}
    part = parts.get(part_id)
    if part is None:
        raise runner.NotFound(f"part {part_id!r} not found in version {ctx.n}")
    hx = _hex(req.colour_hex)
    if hx is not None and not part["colour_editable"]:
        raise Invalid(f"the colour of {part['name']} is not editable")
    if req.material is not None and req.material not in part["material_options"]:
        raise Invalid(f"material {req.material!r} not available for {part['name']} (options: {', '.join(part['material_options']) or 'none'})")
    if req.finish is not None and not (0 < len(req.finish.strip()) <= 60):
        raise Invalid("finish must be 1-60 characters")
    spec = None
    if req.param is not None:
        spec = next((s for s in part["editable"] if s["param"] == req.param), None)
        if spec is None:
            raise Invalid(f"{req.param!r} is not an editable parameter of {part['name']}")
        if not (spec["min"] - 1e-9 <= req.value <= spec["max"] + 1e-9):
            raise Invalid(f"{spec['label']} {req.value:g} {spec['unit']} is outside {spec['min']:g}–{spec['max']:g} {spec['unit']}")
        spec = param_spec(ctx, req.param)
    roles = glb.part_roles(ctx.path).get(part_id, [])
    return {"part": part, "colour_hex": hx, "material": req.material, "finish": req.finish.strip() if req.finish else None,
            "param": spec, "value": req.value, "body": "body" in roles, "base": ctx.n}


def submit(pid: str, part_id: str, req: PartEditRequest) -> int:
    runner.get_project(pid)
    if E._autorun_running(pid):
        raise E.Conflict("An autorun (Make it) is running for this project; edit after it finishes.")
    if any(v.status == VersionStatus.running for v in store.list_versions(pid)):
        raise E.Conflict("A Studio job is running for this project; edit after it finishes.")
    pl = plan(pid, part_id, req)
    msg = headline(pl)
    with E._reg:
        n = store.next_n(pid)
        store.save_version(pid, Version(n=n, message=msg, status=VersionStatus.running))
    E._worker(pid).submit(_job, pid, n, pl)
    return n


def headline(pl: dict) -> str:
    part = pl["part"]
    if pl["param"] is not None:
        s = pl["param"]
        return f"{s['label']} {s['value']:.1f} → {pl['value']:.1f} {s['unit']}"
    bits = []
    if pl["colour_hex"]:
        bits.append(f"{part['name']} colour → {colour_name(pl['colour_hex'])} ({pl['colour_hex']})")
    if pl["material"]:
        from api.cad.parts import PART_MATERIALS

        bits.append(f"{part['name']} material {_short(part['material'])} → {_short(PART_MATERIALS[pl['material']]['name'])}")
    if pl["finish"] and not pl["material"]:
        bits.append(f"{part['name']} finish → {pl['finish']}")
    return "; ".join(bits)


# --------------------------------------------------------------------------- the job


def _job(pid: str, n: int, pl: dict) -> None:
    t0 = time.monotonic()
    base = store.current(pid)
    if base != pl["base"]:
        pl["base"] = base
    try:
        project = runner.get_project(pid)
        with E.lock(pid):
            before = store.live_artifacts(pid)
        if pl["param"] is not None:
            applied, primary, look_changed = _param_edit(project, n, pl, before)
        elif pl["body"] and not _part_only(pl):
            applied, primary, look_changed = _body_look(project, n, pl, before)
        else:
            applied, primary, look_changed = _part_look(project, n, pl, before)
        with E.lock(pid):
            dup = {pl["param"]["label"]} if pl["param"] is not None else set()  # the primary line already says it (p2)
            chs = primary + [c for c in P.changes(before, applied.arts) + applied.notes
                             if not (c.area in ("color", "material") and pl["param"] is None) and c.label not in dup]
            store.write_artifacts(pid, applied.arts, drop=applied.drop)
            v = store.get_version(pid, n)
            v.status, v.finished_at, v.changes = VersionStatus.done, E._now(), chs
            v.summary = "; ".join(_summary_bits(primary))[:200] or v.message
            v.message = v.summary
            v.preview = P.preview(applied.arts)
            v.look_changed = look_changed
            v.render_pending = look_changed and applied.render and E.renders.is_configured()
            v.background_pending = applied.ai_review or applied.replan or 6 not in applied.arts
            photo_job = _photo_after_edit(pid, n, v) if look_changed else None
            store.save_version(pid, v, applied.arts)
            store.set_current(pid, n)
        log.info("part edit %s v%d in %.2fs: %s", pid, n, time.monotonic() - t0, v.summary)
        if photo_job is not None:
            _start_photo(pid, n, *photo_job)
        if v.render_pending:
            E._schedule_render(pid, n, applied.arts)
        elif not look_changed:
            E.carry_photos(pid, base, n)
        if v.background_pending:
            E._bg.submit(E._background, pid, n, stage4=False, ai_review=applied.ai_review, replan=applied.replan)
        E._schedule_engineering(pid)
    except Exception as e:  # noqa: BLE001 — same plain-language failure as a refine, nothing committed
        log.exception("part edit failed for %s", pid)
        E._fail(pid, n, f"The edit could not be applied ({type(e).__name__}: {str(e)[:160]}). "
                        f"Nothing changed — version {base} is still current.")


def _photo_after_edit(pid: str, n: int, v: Version):
    """M1 (W29b): a look change never leaves an older-look photo current. The version starts without photos and with
    render_url None; `photo_stale` stays true until a hero_studio photo of this version is attached. The auto
    hero_studio job (same path as a refine's) starts at once when a reference of THIS version is stored (viewer capture
    ref_v<n>.png or CAD render hero_v<n>.png) and an image model is configured; otherwise the Studio's own viewer-capture
    POST (or the UI's stale note) takes over. Returns (shots, reference) for the job, or None."""
    from api.cad.photos import engine as photos

    if v.preview is not None:
        v.preview.photos, v.preview.render_url, v.preview.photo_stale = [], None, True
    ref, kind = photos.find_reference(pid, n)
    configured = photos.project_photos(pid).configured
    return (["hero_studio"], ref) if configured and kind != "none" else None


def _start_photo(pid: str, n: int, shots: list[str], ref: bytes | None) -> None:
    from api.cad.photos import engine as photos

    try:
        photos.start_job(pid, n, shots, ref)
    except Exception as e:  # noqa: BLE001 — a photo job never fails an edit (409 = one already running)
        log.info("auto photo for %s v%d not started: %s", pid, n, e)


def _keep_plan(applied, before: dict) -> None:
    """m2 (W29b): a colour / material / finish edit keeps the production plan and the factory shortlist as they were."""
    for k in (6, 7):
        if k in before:
            applied.arts[k] = before[k].model_copy(deep=True)
    applied.replan = False
    applied.drop.discard(6)


def _summary_bits(primary: list[VersionChange]) -> list[str]:
    return [c.label for c in primary if c.label]


def _part_only(pl: dict) -> bool:
    """A body part whose material has no product-level meaning (e.g. a strap drawn with the body colour)."""
    return pl["part"]["role"] in ("strap", "window", "lens", "button", "diffuser")


# ---- look of a body part: the product colour / material (refine ops, full pipeline)


def _body_look(project, n: int, pl: dict, before: dict):
    from api.studio import apply as A
    from api.studio.patch import RefinePatch, SetColor, SetMaterial

    part = pl["part"]
    d = P.chosen(before.get(2))
    fin, cname, chex = P.split_finish(d.finish)
    ops = []
    if pl["colour_hex"]:
        ops.append(SetColor(op="set_color", hex=pl["colour_hex"], name=colour_name(pl["colour_hex"])))
    if pl["material"] or pl["finish"]:
        key = pl["material"] or P.material_key(d.material)
        ops.append(SetMaterial(op="set_material", material=key if key in P.MATERIALS else "pc_abs", finish=pl["finish"]))
    applied = A.apply(project, n, RefinePatch(ops=ops, summary=""), before)
    _keep_plan(applied, before)
    primary = []
    if pl["colour_hex"]:
        primary.append(VersionChange(area="color", label=f"{part['name']} colour → {colour_name(pl['colour_hex'])} ({pl['colour_hex']})",
                                     before=f"{cname or ''} {chex or ''}".strip() or None,
                                     after=f"{colour_name(pl['colour_hex'])} {pl['colour_hex']}", label_kind=Label.estimate))
    if pl["material"] or pl["finish"]:
        a = P.chosen(applied.arts[2])
        delta = _delta(before, applied.arts)
        what = f"{_short(d.material)} → {_short(a.material)}" if pl["material"] else f"{fin} → {pl['finish']}"
        primary.append(VersionChange(area="material", label=f"{part['name']} material {what} ({delta})" if pl["material"]
                                     else f"{part['name']} finish {what}", before=f"{d.material}, {fin}",
                                     after=f"{a.material}, {P.split_finish(a.finish)[0]}", label_kind=Label.estimate))
    return applied, primary, True


def _delta(before: dict, after: dict) -> str:
    b, a = _ref_unit(before.get(5)), _ref_unit(after.get(5))
    if b is None or a is None or abs(a - b) < 0.005:
        return "cost unchanged"
    return f"{_money(a - b)}/unit, Estimate"


# ---- look of another part: per-part override baked into the version GLB


def _part_look(project, n: int, pl: dict, before: dict):
    from api.cad.parts import PART_MATERIALS
    from api.studio import apply as A
    from api.studio import cad as studio_cad

    part = pl["part"]
    arts = {k: v.model_copy(deep=True) for k, v in before.items()}
    ctx = version_context(project.id, None)
    root = glb.root_extras(ctx.path)
    overrides = dict(root.get("overrides") or {})
    ov = dict(overrides.get(part["part_id"]) or {})
    for k in ("colour_hex", "material", "finish"):
        if pl[k]:
            ov[k] = pl[k]
    overrides[part["part_id"]] = ov
    pdir = project_dir(project.id)
    spec, design = arts[3], arts[2]
    d = P.chosen(design)
    ai, rest = studio_cad.split(spec.cad_files)
    ai_glb = next((f for f in ai if f.format == "glb"), None)
    dst = pdir / (f"v{n}_ai.glb" if ai_glb is not None else f"v{n}.glb")
    publish(ctx.path, dst)
    glb.recolour(dst, look_of(arts), overrides=overrides)
    url = f"/files/{project.id}/{dst.name}"
    if ai_glb is not None:
        ai_glb.url, ai_glb.size_bytes = url, dst.stat().st_size
        spec.cad_files = ai + rest
    else:
        for f in spec.cad_files:
            if f.format == "glb" and f.url == d.glb_url:
                f.url, f.size_bytes = url, dst.stat().st_size
        d.glb_url = url
    d.render_url = None  # never show the old look's render / photo for the new look
    applied = A.Applied(arts=arts, render=True)
    _keep_plan(applied, before)
    primary = []
    if pl["colour_hex"]:
        primary.append(VersionChange(area="color", label=f"{part['name']} colour → {colour_name(pl['colour_hex'])} ({pl['colour_hex']})",
                                     before=part["colour_hex"], after=pl["colour_hex"], label_kind=Label.estimate))
    if pl["material"] or pl["finish"]:
        new = PART_MATERIALS[pl["material"]]["name"] if pl["material"] else part["material"]
        sp = _spec_part(spec, part)
        note = "cost unchanged"
        if sp is not None and pl["material"]:
            sp.material = new
            if pl["finish"]:
                sp.finish = pl["finish"]
            arts[5] = A.compute_costs(project, arts)
            note = _delta(before, arts)
        elif pl["material"]:
            note = "cost unchanged — no cost line for this part"
        label = (f"{part['name']} material {_short(part['material'])} → {_short(new)} ({note})" if pl["material"]
                 else f"{part['name']} finish → {pl['finish']}")
        primary.append(VersionChange(area="material", label=label, before=part["material"], after=new, label_kind=Label.estimate))
    return applied, primary, True


def _spec_part(spec, part: dict):
    words = [w for w in re.findall(r"[a-z]{4,}", part["name"].lower())]
    for sp in spec.parts:
        low = sp.name.lower()
        if any(w.rstrip("s") in low for w in words):
            return sp
    return None


# ---- parameter: AI CAD program literal and / or family / enclosure parameter


def _param_edit(project, n: int, pl: dict, before: dict):
    from api.cad import family_mode
    from api.studio import apply as A
    from api.studio.patch import RefinePatch

    s, value = pl["param"], float(pl["value"])
    key = s["param"]
    mod = {k: v.model_copy(deep=True) for k, v in before.items()}
    d = P.chosen(mod[2])
    fam = family_mode.family_of(d)
    cad_res = None
    ctx = version_context(project.id, None)
    old_parts = {p["part_id"]: p for p in glb.read_parts(ctx.path)}
    if s["target"] == "program" and ctx.program:
        cad_res = _program_edit(project.id, ctx, key, value, mod)
    synced = None
    if fam and key in family_mode.fparams(d):
        d.cad_parameters[family_mode.PREFIX + key] = value
        synced = f"family parameter {key}"
    elif not fam and (s["target"] == "enclosure" or ENCLOSURE_SYNC.get(key)):
        k2 = key if s["target"] == "enclosure" else ENCLOSURE_SYNC[key]
        if k2 in (d.cad_parameters or {}) or k2 in ("length", "width", "height", "strap_width", "strap_length"):
            d.cad_parameters = {**d.cad_parameters, k2: value}
            synced = f"enclosure {k2}"
    d.render_url = None
    applied = A.apply(project, n, RefinePatch(ops=[], summary=""), mod, cad_res=cad_res)
    applied.render = True
    new_path = _current_glb(project.id, applied.arts)
    new_parts = {p["part_id"]: p for p in glb.read_parts(new_path)} if new_path is not None else {}
    part = pl["part"]
    measured = new_parts.get(part["part_id"])
    primary = [VersionChange(area="dimensions", label=f"{s['label']} {s['value']:.1f} → {value:.1f} {s['unit']} (Measured)",
                             before=f"{s['value']:.1f} {s['unit']}", after=f"{value:.1f} {s['unit']}", label_kind=Label.measured)]
    if measured is not None and part["part_id"] in old_parts:
        b, a = old_parts[part["part_id"]]["measured_bbox_mm"], measured["measured_bbox_mm"]
        if any(abs(x - y) >= 0.05 for x, y in zip(a, b)):
            primary.append(VersionChange(area="dimensions", label=f"{part['name']} size (measured)",
                                         before=" × ".join(f"{x:.1f}" for x in b) + " mm", after=" × ".join(f"{x:.1f}" for x in a) + " mm",
                                         label_kind=Label.measured))
    if synced is None and cad_res is not None:
        applied.notes.append(VersionChange(area="dimensions", label="Note", after=(
            f"{s['label']} changes the AI CAD model only; the moulded parts used for DFM, weight and costs keep their size"),
            label_kind=Label.estimate))
    return applied, primary, True


def _current_glb(pid: str, arts: dict):
    from api.cad.files import resolve_file

    url = P._cad_fields(arts.get(3), P.chosen(arts.get(2)))["glb_url"]
    return resolve_file(pid, url.rsplit("/", 1)[-1]) if url else None


def next_program_version(pid: str) -> int:
    """Next free model_v<k> across the project's files AND its prebuilt folder (a showcase's recorded programs live
    there: a new program must never shadow one of them)."""
    from api.cad.files import roots

    nums = [int(m.group(1)) for r in roots(pid) if r.exists() for f in r.glob("model_v*.py")
            if (m := re.match(r"model_v(\d+)\.py$", f.name))]
    return max(nums, default=0) + 1


def _program_edit(pid: str, ctx, key: str, value: float, arts: dict) -> dict:
    """Edit P[key] in the version's program, run it in the sandbox, publish model_v<k'> (measured)."""
    import shutil

    from api.cad.codegen.engine import LABEL, _publish
    from api.cad.codegen.sandbox import run_code
    from api.cad.families import family_look
    from api.studio import cad as studio_cad

    code = set_program_param(ctx.program, key, value)
    res = run_code(code, timeout_s=40)
    if not res.get("ok"):
        raise RuntimeError(f"the CAD program failed with {key} = {value:g}: {(res.get('error') or '')[:200]}")
    out = project_dir(pid)
    k = next_program_version(pid)
    lk = studio_cad._look(arts.get(2))
    look = family_look(lk["colour"], lk["finish"], lk["material"])
    pub = _publish(res, code, out, k, look, pid)
    overrides = glb.root_extras(ctx.path).get("overrides") or {}
    if overrides:  # per-part looks survive the rebuild
        glb.recolour(pub["files"]["glb"], look, overrides=overrides)
    result = {"status": "ok", "version": k, "code": code, "source": f"param:{key}", "label": LABEL, "category": None,
              "files": {kk: str(v) for kk, v in pub["files"].items()}, "urls": pub["urls"],
              "code_url": f"/projects/{pid}/cad/code/{k}", "bbox_mm": res["bbox_mm"], "volume_mm3": res["volume_mm3"],
              "parts": res["parts"], "attempts": [], "notes": [f"P[{key!r}] {value:g} (deterministic part edit)"],
              "parent_version": ctx.program_k, "instruction": f"{key} = {value:g}"}
    meta = {kk: v for kk, v in result.items() if kk != "code"}
    (out / f"model_v{k}.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    shutil.rmtree(res.get("work_dir") or "/nonexistent", ignore_errors=True)
    return result


__all__ = ["submit", "plan", "Invalid", "colour_name", "set_program_param"]
