"""Studio jobs (W17): start, refine, restore + guarded background work.

- One FIFO worker per project runs start/refine jobs in order (a refine sent while another runs just queues).
- A per-project write lock covers every commit. A job commits all of stages 1-7 at once, or nothing: the LLM patch and
  the CAD rebuild happen before the commit, into version-named files (v<n>.glb, v<n>_enclosure.*), so a failure
  leaves the previous version current and untouched.
- Background work (concept render, lazy directions d2/d3, stage 4 AI review, stage 6 plan → stage 7) always updates
  its own version's snapshot, and the live stage artifacts only while that version is still current.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from api.cad import directions as cad_directions
from api.cad import family_mode, renders
from api.cad.build import build_direction, normalize, project_dir, publish
from api.cad.look import build_assembly, features_for, look_for
from api.stages import runner
from api.stages.registry import STAGE_HANDLERS, StageContext
from api.studio import apply as A
from api.studio import cad as studio_cad
from api.studio import patch as patch_mod
from api.studio import product as P
from api.studio import store
from contracts.artifacts import ARTIFACT_MODELS, Assumption, CadFile, DesignArtifact, Version, VersionStatus

log = logging.getLogger("studio")

RENDER_BUDGET_S = 27.0
PATCH_BUDGET_S = 45.0
CAD_BUDGET_S = float(os.getenv("CODEGEN_BUDGET_S", "300"))  # one AI CAD job: LLM + sandbox + self-repair attempts
CAD_WAIT_S = 240.0  # a geometric refine waits this long for the version's pending AI CAD

_reg = threading.Lock()
_workers: dict[str, ThreadPoolExecutor] = {}
_locks: dict[str, threading.RLock] = {}
_bg = ThreadPoolExecutor(max_workers=8, thread_name_prefix="studio-bg")
_cad_events: dict[str, threading.Event] = {}  # set = no AI CAD job running for the project


class Conflict(Exception):
    pass


def _worker(pid: str) -> ThreadPoolExecutor:
    with _reg:
        if pid not in _workers:
            _workers[pid] = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"studio-{pid}")
        return _workers[pid]


def lock(pid: str) -> threading.RLock:
    with _reg:
        return _locks.setdefault(pid, threading.RLock())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _autorun_running(pid: str) -> bool:
    try:
        import api.main as m

        th = m._autorun_threads.get(pid)
        return th is not None and th.is_alive()
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------- version bookkeeping


def _update_version(pid: str, n: int, **fields) -> None:
    with lock(pid):
        v = store.get_version(pid, n)
        if v is None:
            return
        for k, val in fields.items():
            setattr(v, k, val)
        store.save_version(pid, v)


def _refresh_preview(pid: str, n: int) -> None:
    """Rebuild version n's preview from its snapshot; its product photos (W27, not part of the snapshot) are kept."""
    snap = store.load_snapshot(pid, n)
    if not snap:
        return
    with lock(pid):
        new = P.preview(snap)
        v = store.get_version(pid, n)
        if v is not None and v.preview is not None and v.preview.photos:
            new.photos = list(v.preview.photos)
        _update_version(pid, n, preview=new)


def _commit_bg(pid: str, n: int, arts: dict) -> bool:
    """Background result for version n: into its snapshot always, into the live artifacts only if n is still current."""
    with lock(pid):
        store.patch_snapshot(pid, n, arts)
        live = store.current(pid) == n
        if live:
            for k, a in arts.items():
                runner.save_artifact(pid, k, a, a.status if a.status != "not_started" else "draft")
    _refresh_preview(pid, n)
    return live


def _llm_error_text(e: Exception, base: int) -> str:
    s = f"{type(e).__name__}: {e}".lower()
    keep = f"Nothing changed — version {base} is still current."
    if "402" in s or "credit" in s:
        return f"The AI service is out of credits (HTTP 402), so this request could not be interpreted. {keep}"
    if "notconfigured" in s or "not configured" in s or "missing" in s and "key" in s:
        return f"The AI is not configured on this server, so prompts cannot be interpreted. {keep}"
    if "429" in s or "rate" in s and "limit" in s:
        return f"The AI service is rate-limiting requests right now. {keep} Try again in a minute."
    if "401" in s or "403" in s:
        return f"The AI service refused the request (authentication). {keep}"
    if "timeout" in s or "timed out" in s:
        return f"The AI took too long to answer. {keep} Try again."
    if "validation" in s or "invalid json" in s:
        return f"The AI's answer could not be understood. {keep} Try rephrasing."
    return f"The AI service failed ({type(e).__name__}). {keep}"


def _fail(pid: str, n: int, error: str) -> None:
    log.warning("studio v%d for %s failed: %s", n, pid, error)
    _update_version(pid, n, status=VersionStatus.failed, error=error[:500], finished_at=_now(), render_pending=False,
                    background_pending=False)


# --------------------------------------------------------------------------- renders


def _render(pid: str, n: int, brief, direction, family: str) -> None:
    """Concept render of version n → v<n>.png, patched into the version (and stage 2 if n is current)."""
    try:
        _, cname, _ = P.split_finish(direction.finish)
        extra = "" if family_mode.family_of(direction) else A.render_extra(family, normalize(direction.cad_parameters), brief)
        prompt = renders.build_prompt(brief, direction, cname, extra)
        ref = project_dir(pid) / f"ref_v{n}.png"  # W27 viewer capture of this version: the render follows the real shape
        reference = ref.read_bytes() if ref.is_file() else None
        if reference is not None:
            prompt = renders.REFERENCE_NOTE + prompt
        ok = renders.render(prompt, project_dir(pid) / f"v{n}.png", time.monotonic() + RENDER_BUDGET_S, reference=reference)
    except Exception as e:  # noqa: BLE001 — a missing render never fails a version
        log.warning("studio render v%d failed: %s", n, e)
        ok = False
    url = f"/files/{pid}/v{n}.png" if ok else None
    if url:
        snap = store.load_snapshot(pid, n)
        design = snap.get(2)
        if design is not None:
            d = P.chosen(design)
            d.render_url = url
            if not any(a.id == "a2_render" for a in design.assumptions):
                design.assumptions.append(Assumption(id="a2_render", label="estimate", stage=2,
                                                     text=f"{renders.RENDER_CAPTION}. Generated by an AI image model from the direction's shape, dimensions, material, finish and colour; the 3D model is the CAD."))
            _commit_bg(pid, n, {2: design})
    _update_version(pid, n, render_pending=False)


def carry_photos(pid: str, src: int, dst: int) -> int:
    """W21e: same look → version dst reuses version src's product photos (and viewer reference): files copied under dst's
    names, labels and references unchanged, no image call. Returns how many photos were carried."""
    import shutil

    from api.cad.photos import engine as photos

    prev = store.get_version(pid, src)
    if prev is None or prev.preview is None or not prev.preview.photos:
        return 0
    pdir = project_dir(pid)
    from api.cad.files import resolve_file

    if (ref := resolve_file(pid, f"ref_v{src}.png")) is not None and not (pdir / f"ref_v{dst}.png").exists():
        shutil.copyfile(ref, pdir / f"ref_v{dst}.png")
    n = 0
    for p in prev.preview.photos:
        name = p.url.rsplit("/", 1)[-1]
        path = resolve_file(pid, name)
        if path is None:
            continue
        new = f"photo_v{dst}_{p.shot}.png"
        shutil.copyfile(path, pdir / new)
        photos.attach_photo(pid, dst, p.model_copy(update={"url": f"/files/{pid}/{new}", "version": dst}))
        n += 1
    return n


def _schedule_render(pid: str, n: int, arts: dict) -> bool:
    if not renders.is_configured():
        return False
    d = P.chosen(arts[2])
    _bg.submit(_render, pid, n, arts[1], d.model_copy(deep=True), P.family_of(normalize(d.cad_parameters)))
    return True


# --------------------------------------------------------------------------- background stages


def _run_handler(pid: str, n: int, stage: int, arts: dict, **ctx_extra):
    """Run a stage handler on version n's artifacts (not the DB's), capped; fixture on failure like the runner."""
    project = runner.get_project(pid)
    ctx = StageContext(project=project, stage=stage, inputs={}, artifacts=dict(arts), **ctx_extra)
    try:
        handler = STAGE_HANDLERS[stage]
        res = runner.call_with_timeout(handler, ctx)
        art = ARTIFACT_MODELS[stage].model_validate(res.model_dump() if hasattr(res, "model_dump") else res)
        art.project_id = pid
    except Exception as e:  # noqa: BLE001
        log.warning("studio bg stage %d for %s v%d → fixture: %s", stage, pid, n, e)
        art = runner.load_fixture(project.example, stage, pid)
        art.fallback, art.fallback_reason = True, f"{type(e).__name__}: {e}"[:500]
    return art


def _background(pid: str, n: int, *, stage4: bool, ai_review: bool, replan: bool) -> None:
    """stage4: full stage 4 handler (start). ai_review: refresh only the AI-reviewed DFM issues. replan: stage 6 → 7."""
    try:
        project = runner.get_project(pid)
        arts = store.load_snapshot(pid, n)
        if stage4:
            arts[4] = _run_handler(pid, n, 4, arts)
            arts[5] = A.compute_costs(project, arts)  # certification budget now comes from stage 4
            _commit_bg(pid, n, {4: arts[4], 5: arts[5]})
        elif ai_review and arts.get(3) is not None and arts.get(4) is not None:
            from api.agents.dfm_review import ai_review as review

            dfm = arts[4]
            measured = [i for i in dfm.issues if str(getattr(i.method, "value", i.method)) == "measured"]
            ai = runner.call_with_timeout(review, arts[3], arts[3].bom, measured)
            dfm.issues = measured + [x.model_copy(update={"id": f"a{i}"}) for i, x in enumerate(ai, 1)]
            dfm.assumptions = [a for a in dfm.assumptions if a.id != "a4_studio"] + [Assumption(
                id="a4_studio", label="estimate", stage=4, text=f"Studio v{n}: measured checks and AI review re-run on this version")]
            _commit_bg(pid, n, {4: dfm})
        if replan or 6 not in arts:
            arts = store.load_snapshot(pid, n)
            arts[6] = _run_handler(pid, n, 6, arts)
            arts[7] = A.compute_match(project, arts)
            _commit_bg(pid, n, {6: arts[6], 7: arts[7]})
    except Exception as e:  # noqa: BLE001 — background refreshes never fail a version
        log.warning("studio background for %s v%d failed: %s", pid, n, e)
    finally:
        _update_version(pid, n, background_pending=False)


def _lazy_directions(pid: str, n: int, brief, items: list) -> None:
    """Build d2/d3 after version 1 answered; patch their glb_url into every snapshot and the live stage 2.
    Items: (did, proposal, params) for W2 directions, (did, DesignDirection, None) for product-family ones (W21)."""
    built = {}
    for did, prop, params in items:
        try:
            if params is None:  # W21 family direction
                family_mode.build_direction_files(pid, prop)
                built[did] = prop.glb_url
                continue
            d = cad_directions.direction_obj(pid, did, prop, params)
            build_direction(params, project_dir(pid), name=did)
            cad_directions.build_look(pid, d, params, features_for(brief))
            built[did] = d.glb_url
        except Exception as e:  # noqa: BLE001
            log.warning("studio lazy direction %s failed: %s", did, e)
    if not built:
        return
    with lock(pid):
        for v in store.list_versions(pid):
            snap = store.load_snapshot(pid, v.n)
            if 2 in snap:
                for d in snap[2].directions:
                    if d.id in built and not d.glb_url:
                        d.glb_url = built[d.id]
                store.patch_snapshot(pid, v.n, {2: snap[2]})
        live = runner.get_artifact(pid, 2)
        if live is not None and store.current(pid) > 0:
            for d in live.directions:
                if d.id in built and not d.glb_url:
                    d.glb_url = built[d.id]
            runner.save_artifact(pid, 2, live, live.status)


# --------------------------------------------------------------------------- AI CAD (W21) + engineering


def _cad_event(pid: str) -> threading.Event:
    with _reg:
        ev = _cad_events.get(pid)
        if ev is None:
            ev = _cad_events[pid] = threading.Event()
            ev.set()
        return ev


def _recompute_engineering(pid: str) -> None:
    try:
        from api.engineering.service import recompute_engineering

        recompute_engineering(pid)
    except Exception as e:  # noqa: BLE001 — engineering is a read model: GET /engineering recomputes on demand
        log.warning("engineering recompute for %s failed: %s", pid, e)


def _schedule_engineering(pid: str) -> None:
    _bg.submit(_recompute_engineering, pid)


def _schedule_cad(pid: str, n: int) -> None:
    """Version n's AI CAD model in the background (AI on), or the family program recorded at once (AI off)."""
    if not studio_cad.enabled():
        try:
            res = studio_cad.family_code(pid, store.load_snapshot(pid, n))
            if res is not None:
                _patch_cad(pid, n, res)
        except Exception as e:  # noqa: BLE001
            log.warning("family program for %s v%d not recorded: %s", pid, n, e)
        _update_version(pid, n, cad_pending=False)
        return
    ev = _cad_event(pid)
    ev.clear()
    _bg.submit(_cad_job, pid, n)


def _cad_job(pid: str, n: int) -> None:
    t0 = time.monotonic()
    note, res = None, None
    try:
        res = runner.call_with_timeout(studio_cad.generate, pid, store.load_snapshot(pid, n), timeout=CAD_BUDGET_S)
        if res.get("status") == "failed" or not studio_cad.ai_entries(pid, res):
            note = "The AI CAD model could not be generated; the parametric model stays the 3D model of this version."
        elif res.get("status") == "fallback":
            note = ("The AI CAD program failed its checks after self-repair: the parametric family program is shown "
                    "instead (Parametric family CAD).")
        if studio_cad.ai_entries(pid, res):
            _patch_cad(pid, n, res)
        log.info("studio AI CAD %s v%d: %s in %.1fs (%d attempt(s))", pid, n, res.get("status"), time.monotonic() - t0,
                 len(res.get("attempts") or []))
    except Exception as e:  # noqa: BLE001 — an AI CAD failure never fails a version
        log.warning("studio AI CAD for %s v%d failed: %s", pid, n, e)
        note = f"The AI CAD model could not be generated ({type(e).__name__}); the parametric model stays the 3D model."
    finally:
        _update_version(pid, n, cad_pending=False, cad_note=note, **_attempts(res))
        _cad_event(pid).set()


def _attempts(res) -> dict:
    """cad_attempts / cad_repairs of a generate_cad / refine_cad result (W21c)."""
    if not isinstance(res, dict) or not res.get("attempts"):
        return {}
    n = len([a for a in res["attempts"] if "llm_seconds" in a or a.get("error")])
    ok = res.get("status") in ("ok", "repaired")
    return {"cad_attempts": n, "cad_repairs": max(0, n - 1) if ok else 0}


def _patch_cad(pid: str, n: int, res: dict) -> None:
    """AI entries of version n → its snapshot, and every later version still without an AI model (same geometry:
    geometric refines wait for this job), recoloured to each version's look; live stage 3 when one of them is current."""
    entries = studio_cad.ai_entries(pid, res)
    touched = []
    with lock(pid):
        cur = store.current(pid)
        for v in store.list_versions(pid):
            if v.n < n:
                continue
            snap = store.load_snapshot(pid, v.n)
            spec = snap.get(3)
            if spec is None or (v.n != n and studio_cad.split(spec.cad_files)[0]):
                continue
            studio_cad.attach(spec, [e.model_copy() for e in entries])
            d = P.chosen(snap.get(2))
            if v.n != n and d is not None:
                studio_cad.recolour(pid, v.n, spec, d)
            store.patch_snapshot(pid, v.n, {3: spec})
            touched.append(v.n)
            if v.n == cur:
                runner.save_artifact(pid, 3, spec, spec.status if spec.status != "not_started" else "draft")
    for m in touched:
        _refresh_preview(pid, m)
    if cur in touched:
        _schedule_engineering(pid)


def _geometry_edit(pid: str, n: int, message: str, patch) -> dict | None:
    """Refine ops that change geometry beyond parameters (regenerate_geometry, set_shape_family, set_dimensions) edit
    the version's AI CAD program (refine_cad). Waits for a pending AI CAD job first. None: nothing to edit."""
    geo = [o for o in patch.ops if o.op in studio_cad.GEO_OPS]
    if not geo or not studio_cad.enabled():
        return None
    if not _cad_event(pid).wait(CAD_WAIT_S):
        log.warning("studio %s v%d: AI CAD still pending after %.0fs, geometry edit skipped", pid, n, CAD_WAIT_S)
        return None
    arts = store.live_artifacts(pid)
    k = studio_cad.current_model(arts.get(3))
    if k is None:
        return None
    instr = "; ".join(o.instruction for o in geo if o.op == "regenerate_geometry") or message
    _update_version(pid, n, cad_pending=True)
    try:
        return runner.call_with_timeout(studio_cad.edit, pid, k, instr, arts, timeout=CAD_BUDGET_S)
    except Exception as e:  # noqa: BLE001 — the parametric part of the refine still applies
        log.warning("studio AI CAD edit %s v%d failed: %s", pid, n, e)
        return None
    finally:
        _update_version(pid, n, cad_pending=False)


def _cad_change(before: dict, after: dict, patch) -> list:
    from contracts.artifacts import Label, VersionChange

    kb, ka = studio_cad.current_model(before.get(3)), studio_cad.current_model(after.get(3))
    if ka is None or ka == kb:
        return []
    instr = "; ".join(o.instruction for o in patch.ops if o.op == "regenerate_geometry")
    return [VersionChange(area="shape", label="AI CAD program", before=f"v{kb}" if kb else None,
                          after=f"v{ka}" + (f" — {instr[:120]}" if instr else " — edited by the AI"), label_kind=Label.measured)]


# --------------------------------------------------------------------------- start


def _family_design(pid: str, project, brief, hit) -> tuple[DesignArtifact, None, list]:
    """W21: stage 2 of a product-family project — d1 built now (< 1 s, published as v1.glb), d2/d3 lazily."""
    from api.cad.directions import family_assumptions

    dirs, notes = family_mode.family_directions(pid, brief, project.prompt, hit, build=("d1",))
    d1 = dirs[0]
    pdir = project_dir(pid)
    for ext in ("glb", "step", "stl"):
        publish(pdir / f"d1.{ext}", pdir / f"v1.{ext}")
    d1.glb_url = f"/files/{pid}/v1.glb"
    design = DesignArtifact(project_id=pid, generated_by="code", assumptions=family_assumptions(hit, notes), directions=dirs,
                            chosen_direction_id="d1")
    return design, None, [(d.id, d.model_copy(deep=True), None) for d in dirs[1:]]


def _studio_design(pid: str, project, brief) -> tuple[DesignArtifact, str | None, list]:
    """Stage 2 with only d1 built now (in the Studio family for wearables); d2/d3 are returned for lazy building."""
    family = P.studio_family(brief, project.prompt)
    hit = None if family else family_mode.detect(brief, project.prompt)
    if hit is not None:
        return _family_design(pid, project, brief, hit)
    assumptions = [Assumption(id="a2_1", label="estimate", stage=2,
                              text="Two-shell injection-moulded enclosure, drafted walls, split line in the XY plane")]
    try:
        proposals, generated_by = runner.call_with_timeout(cad_directions._propose_llm, brief, timeout=12)
    except Exception as e:  # noqa: BLE001 — category presets are a first-class path
        proposals, generated_by = cad_directions._defaults(brief), "code"
        assumptions.append(Assumption(id="a2_2", label="estimate", stage=2,
                                      text=f"Names, colours and dimensions from '{cad_directions.preset_key(brief)}' category presets (LLM unavailable: {type(e).__name__})"))
    first = proposals[0]
    params = A.family_params(family, brief) if family else cad_directions.cad_params(first, brief)
    d1 = cad_directions.direction_obj(pid, "d1", first, params)
    if family:
        d1.shape, d1.description = P.FAMILY_SHAPE[family], P.FAMILY_TEXT[family]
        d1.material = P.MATERIALS["pc_abs"][0] if first.material != "aluminium" else d1.material
    d1.cad_parameters = {**params, "density_g_cm3": P.MATERIALS[P.material_key(d1.material)][1]}
    look = look_for(d1.material, d1.finish)
    build_assembly(params, project_dir(pid) / "v1.glb", look, features_for(brief))
    d1.glb_url = f"/files/{pid}/v1.glb"
    others = []
    rest = proposals[1:] if len(proposals) >= 3 else proposals[:2]
    dirs = [d1]
    for i, prop in enumerate(rest[:2], 2):
        p = cad_directions.cad_params(prop, brief)
        d = cad_directions.direction_obj(pid, f"d{i}", prop, p)
        d.glb_url = None  # built lazily after version 1 answered
        dirs.append(d)
        others.append((d.id, prop, p))
    design = DesignArtifact(project_id=pid, generated_by=generated_by, assumptions=assumptions, directions=dirs,
                            chosen_direction_id="d1")
    return design, family, others


def _version_files_v1(pid: str, spec) -> None:
    """Freeze stage 3's enclosure.* as v1_enclosure.* (later versions never overwrite a version's files)."""
    pdir = project_dir(pid)
    files = []
    for f in spec.cad_files:
        name = f.url.rsplit("/", 1)[-1]
        if name.startswith("enclosure.") and (pdir / name).exists():
            publish(pdir / name, pdir / f"v1_{name}")
            f = CadFile(format=f.format, url=f"/files/{pid}/v1_{name}", description=f.description, size_bytes=f.size_bytes)
        files.append(f)
    spec.cad_files = files


def _start_job(pid: str) -> None:
    t0 = time.monotonic()
    try:
        project = runner.get_project(pid)
        if runner.get_artifact(pid, 1) is None:
            runner.run_stage(pid, 1)
        brief = runner.get_artifact(pid, 1)
        design, family, others = _studio_design(pid, project, brief)
        runner.save_artifact(pid, 2, design)
        t_design = time.monotonic() - t0
        render_pending = _schedule_render_start(pid, brief, design, family)
        spec = runner.run_stage(pid, 3, {"direction_id": "d1"})
        if not spec.fallback:
            d1 = P.chosen(design)
            p = normalize(d1.cad_parameters)
            A.ensure_strap(spec, p, P.family_of(p), d1.material, d1.finish)
            _version_files_v1(pid, spec)
            runner.save_artifact(pid, 3, spec)
        runner.run_stage(pid, 5)
        arts = store.live_artifacts(pid)
        try:
            arts[7] = A.compute_match(project, arts)
        except Exception as e:  # noqa: BLE001
            log.warning("studio start shortlist → fixture: %s", e)
            arts[7] = runner.load_fixture(project.example, 7, pid)
            arts[7].fallback, arts[7].fallback_reason = True, f"{type(e).__name__}: {e}"[:500]
        runner.save_artifact(pid, 7, arts[7])
        arts = store.live_artifacts(pid)
        d1 = P.chosen(arts[2])
        _, cname, chex = P.split_finish(d1.finish)
        took = time.monotonic() - t0
        with lock(pid):
            v = store.get_version(pid, 1)
            v.status, v.finished_at = VersionStatus.done, _now()
            v.preview = P.preview(arts)
            shape = d1.shape if family_mode.family_of(d1) else P.FAMILY_SHAPE.get(P.family_of(normalize(d1.cad_parameters)), d1.shape)
            v.summary = (f"{brief.product_name}: {shape.lower()}, "
                         f"{cname or 'default colour'} — first version in {took:.0f} s")
            v.render_pending, v.background_pending = render_pending, True
            v.cad_pending = studio_cad.enabled()
            store.save_version(pid, v, arts)
            store.set_current(pid, 1)
        log.info("studio start %s: v1 in %.1fs (design %.1fs)", pid, took, t_design)
        _bg.submit(_lazy_directions, pid, 1, brief, others)
        _bg.submit(_background, pid, 1, stage4=True, ai_review=False, replan=True)
        _schedule_cad(pid, 1)
        _schedule_engineering(pid)
    except Exception as e:  # noqa: BLE001
        log.exception("studio start failed for %s", pid)
        _fail(pid, 1, f"The first version could not be built ({type(e).__name__}: {str(e)[:200]}).")


def _schedule_render_start(pid: str, brief, design, family) -> bool:
    if not renders.is_configured():
        return False
    d = P.chosen(design).model_copy(deep=True)

    # start the image request now (in parallel with stage 3), patch it in once v1 is committed
    def early():
        _, cname, _ = P.split_finish(d.finish)
        fam = family or P.family_of(normalize(d.cad_parameters))
        extra = "" if family_mode.family_of(d) else A.render_extra(fam, normalize(d.cad_parameters), brief)
        prompt = renders.build_prompt(brief, d, cname, extra)
        ok = renders.render(prompt, project_dir(pid) / "v1.png", time.monotonic() + RENDER_BUDGET_S)
        for _ in range(240):
            if store.load_snapshot(pid, 1) or (store.get_version(pid, 1) or Version(n=1, message="")).status == "failed":
                break
            time.sleep(0.25)
        if ok and store.load_snapshot(pid, 1):
            snap = store.load_snapshot(pid, 1)
            design1 = snap[2]
            P.chosen(design1).render_url = f"/files/{pid}/v1.png"
            if not any(a.id == "a2_render" for a in design1.assumptions):
                design1.assumptions.append(Assumption(id="a2_render", label="estimate", stage=2,
                                                      text=f"{renders.RENDER_CAPTION}. Generated by an AI image model from the direction's shape, dimensions, material, finish and colour; the 3D model is the CAD."))
            _commit_bg(pid, 1, {2: design1})
        _update_version(pid, 1, render_pending=False)

    _bg.submit(early)
    return True


def start(pid: str) -> int:
    runner.get_project(pid)  # 404
    if _autorun_running(pid):
        raise Conflict("An autorun (Make it) is running for this project; wait for it to finish.")
    with _reg:
        vs = store.list_versions(pid)
        if vs and not (len(vs) == 1 and vs[0].status == VersionStatus.failed):
            return store.current(pid) or vs[0].n
        store.save_version(pid, Version(n=1, message="Studio start", status=VersionStatus.running))
    _worker(pid).submit(_start_job, pid)
    return 1


# --------------------------------------------------------------------------- refine


def state_for_llm(arts: dict) -> dict:
    brief, design, spec, costs = arts.get(1), arts.get(2), arts.get(3), arts.get(5)
    d = P.chosen(design)
    p = normalize(d.cad_parameters or {}) if d else {}
    pfam = family_mode.family_of(d) if d else None  # W21 product family
    fam = pfam or (P.family_of(p) if p else None)
    fin, cname, chex = P.split_finish(d.finish) if d else ("", None, None)
    dims = spec.overall_dimensions if spec else None
    out = {
        "product": brief.product_name if brief else None,
        "one_liner": brief.one_liner if brief else None,
        "category": brief.category if brief else None,
        "shape_family": fam,
        "measured_dimensions_mm": {"length": dims.length.value, "width": dims.width.value, "height": dims.height.value} if dims else None,
        "dimension_meaning": {"wearable_band": "pod length × width × thickness (strap separate)",
                              "ring": "outer diameter × outer diameter × band width"}.get(fam or "", "overall length × width × height"),
        "cad": ("AI-written build123d program: form changes go through regenerate_geometry"
                if studio_cad.current_model(spec) else "parametric CAD"),
        "colour": f"{cname or ''} {chex or ''}".strip(),
        "material": d.material if d else None, "finish": fin,
        "features": brief.key_features if brief else [],
        "requirements": brief.constraints if brief else [],
        "target_price": f"{brief.target_retail_price.value:g} {brief.target_retail_price.unit}" if brief else None,
        "markets": brief.target_markets if brief else [],
        "bom": [{"id": b.id, "part": b.part, "qty": b.qty, "category": str(getattr(b.category, "value", b.category))}
                for b in (spec.bom if spec else [])],
    }
    if costs and costs.tiers:
        out["unit_cost_usd"] = {t.quantity: round(t.unit_cost.value, 2) for t in costs.tiers}
    if p and fam == "wearable_band":
        out["strap_mm"] = {"width": p.get("strap_width"), "length": p.get("strap_length")}
    return out


def _refine_job(pid: str, n: int, message: str) -> None:
    t0 = time.monotonic()
    base = store.current(pid)
    if base == 0:
        return _fail(pid, n, "The first version could not be built, so there is nothing to refine yet. Start the Studio again.")
    try:
        before = store.live_artifacts(pid)
        try:
            p = runner.call_with_timeout(patch_mod.propose, message, state_for_llm(before), base, timeout=PATCH_BUDGET_S)
        except Exception as e:  # noqa: BLE001 — LLM / 402 / timeout: plain-language failure, nothing touched
            return _fail(pid, n, _llm_error_text(e, base))
        t_llm = time.monotonic() - t0
        project = runner.get_project(pid)
        cad_res, t_cad = _geometry_edit(pid, n, message, p), time.monotonic() - t0 - t_llm
        with lock(pid):
            before = store.live_artifacts(pid)  # background results may have landed while the LLM answered
            try:
                applied = A.apply(project, n, p, before, cad_res=cad_res)
            except Exception as e:  # noqa: BLE001
                log.exception("studio apply v%d failed for %s", n, pid)
                return _fail(pid, n, f"The product could not be rebuilt with this change ({type(e).__name__}: {str(e)[:160]}). "
                                     f"Nothing changed — version {base} is still current.")
            chs = P.changes(before, applied.arts) + applied.notes + _cad_change(before, applied.arts, p)
            if applied.battery:  # W21b: the runtime the battery change buys (engineering layer, before → after)
                from api.studio.battery import runtime_change

                chs = [c for c in chs if not (c.label == "Component added" and (c.after or "").startswith("Li-ion battery pack"))]
                if (rc := runtime_change(project, before, applied.arts)) is not None:
                    chs.append(rc)
            store.write_artifacts(pid, applied.arts, drop=applied.drop)
            took = time.monotonic() - t0
            v = store.get_version(pid, n)
            v.status, v.finished_at, v.changes = VersionStatus.done, _now(), chs
            v.summary = P.summarize(chs, p.summary)
            v.preview = P.preview(applied.arts)
            v.render_pending = applied.render and renders.is_configured()
            v.look_changed = applied.render  # colour / material / finish / shape / dimensions (W21e)
            for k, val in _attempts(cad_res).items():
                setattr(v, k, val)
            v.background_pending = applied.ai_review or applied.replan or 6 not in applied.arts
            store.save_version(pid, v, applied.arts)
            store.set_current(pid, n)
        log.info("studio refine %s v%d in %.1fs (llm %.1fs, cad %.1fs): %s", pid, n, took, t_llm, t_cad, v.summary)
        if applied.render:
            _schedule_render(pid, n, applied.arts)
        else:
            carry_photos(pid, base, n)
        if v.background_pending:
            _bg.submit(_background, pid, n, stage4=False, ai_review=applied.ai_review, replan=applied.replan)
        _schedule_engineering(pid)
    except Exception as e:  # noqa: BLE001
        log.exception("studio refine failed for %s", pid)
        _fail(pid, n, f"Unexpected error ({type(e).__name__}). Nothing changed — version {base} is still current.")


def refine(pid: str, message: str) -> int:
    runner.get_project(pid)  # 404
    first = store.get_version(pid, 1)
    if store.current(pid) == 0 and (first is None or first.status == VersionStatus.failed):
        raise Conflict("Start the Studio first: POST /projects/{id}/studio/start")  # (a running v1 → the refine queues)
    if _autorun_running(pid):
        raise Conflict("An autorun (Make it) is running for this project; refine after it finishes.")
    with _reg:
        n = store.next_n(pid)
        store.save_version(pid, Version(n=n, message=message.strip()[:1000], status=VersionStatus.running))
    _worker(pid).submit(_refine_job, pid, n, message)
    return n


# --------------------------------------------------------------------------- restore


def restore(pid: str, n: int) -> Version:
    runner.get_project(pid)
    v = store.get_version(pid, n)
    if v is None:
        raise runner.NotFound(f"version {n} not found")
    if v.status != VersionStatus.done:
        raise Conflict(f"version {n} is {v.status}: only a finished version can be restored")
    if any(x.status == VersionStatus.running for x in store.list_versions(pid)):
        raise Conflict("A refine is still running; restore after it finishes")
    if _autorun_running(pid):
        raise Conflict("An autorun (Make it) is running for this project")
    with lock(pid):
        snap = store.load_snapshot(pid, n)
        if not snap:
            raise Conflict(f"version {n} has no stored product")
        store.write_artifacts(pid, snap, drop=set(store.STUDIO_STAGES) - set(snap))
        store.set_current(pid, n)
    _schedule_engineering(pid)
    return store.get_version(pid, n)


__all__ = ["start", "refine", "restore", "Conflict", "state_for_llm", "lock"]
