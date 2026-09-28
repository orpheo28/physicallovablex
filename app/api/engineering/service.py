"""Engineering layer entry points. Owner: W20.

    get_engineering(project_id) -> EngineeringArtifact        # cached while the project state is unchanged
    recompute_engineering(project_id, llm_firmware=True)       # call after each Studio refine (W17/W21)
    engineering_for_ctx(ctx, llm_firmware=False)               # from an existing StageContext (Factory Pack, PDF)

Inputs: stage 1 (brief), 2 (chosen direction → shape family), 3 (measured CAD bbox, STEP volume, weight, BOM).
Cache: FILES_DIR/<project_id>/engineering.json keyed by `inputs_digest`; firmware.zip + firmware.json next to it.
The firmware is written from the template at once; with an LLM key an LLM version ("fast" route) is generated in the
background and replaces it (FirmwareProject.pending_llm tells the UI to re-GET).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from functools import lru_cache
from pathlib import Path

from contracts.artifacts import (
    Assumption,
    BOMItem,
    EngineeringArtifact,
    FirmwareProject,
    Label,
    LabeledValue,
)

from api import llm
from api.engineering import category as cat
from api.engineering import electronics, firmware, physics, prototype, site_install, solar, strategy
from api.engineering._util import lv

log = logging.getLogger("engineering")

ENGINE_VERSION = "w21e.1"
FAMILIES = {3: "wearable_band", 4: "ring"}  # api/cad/wearables.py shape families
_VOLUME_RE = re.compile(r"volume\s+([\d.]+)\s*cm³\s*\(measured\)", re.I)
_locks: dict[str, threading.Lock] = {}
_reg = threading.Lock()


def _lock(pid: str) -> threading.Lock:
    with _reg:
        return _locks.setdefault(pid, threading.Lock())


def files_dir(pid: str) -> Path:
    from api.cad.build import files_root

    return files_root() / pid


def firmware_url(pid: str) -> str:
    return f"/files/{pid}/firmware.zip"


# --------------------------------------------------------------------------- inputs


@lru_cache(maxsize=64)
def _step_volume_cm3(path: str, mtime: float) -> float:
    from build123d import import_step

    shape = import_step(path)
    solids = shape.solids() or [shape]
    return sum(abs(s.volume) for s in solids) / 1000.0


def measured_volume(pid: str, spec) -> LabeledValue | None:
    """Solid volume of the moulded parts: stage 3's measured figure, else re-measured on the STEP file."""
    m = _VOLUME_RE.search(spec.weight.source_or_assumption or "")
    if m:
        return lv(float(m.group(1)), "cm³", "measured", "Enclosure solid volume measured on the STEP (stage 3)", nd=1)
    step = next((c for c in sorted(spec.cad_files, key=lambda c: "enclosure" not in c.url) if c.format == "step"), None)
    if step is None:
        return None
    try:
        from api.cad.files import resolve_file

        parts = step.url.strip("/").split("/")
        path = resolve_file(parts[-2], parts[-1]) if len(parts) >= 3 else None
        if path is None:
            return None
        vol = _step_volume_cm3(str(path), path.stat().st_mtime)
        return lv(vol, "cm³", "measured", f"Solid volume of {path.name} (build123d / OCCT)", nd=1)
    except Exception as e:  # noqa: BLE001
        log.info("STEP volume unavailable for %s: %s", pid, e)
        return None


def _direction(design):
    if design is None or not design.directions:
        return None
    return next((x for x in design.directions if x.id == design.chosen_direction_id), design.directions[0])


def _family(design) -> str | None:
    """W17 wearable family (wearable_band / ring) or W21 product family (board, drone …) of the chosen direction."""
    from api.cad.family_mode import family_of

    d = _direction(design)
    if d is None:
        return None
    if (fam := family_of(d)) is not None:
        return fam
    try:
        return FAMILIES.get(int((d.cad_parameters or {}).get("family", 0)))
    except (TypeError, ValueError):
        return None


def _is_shell(design) -> bool | None:
    """True: hollow moulded enclosure; False: solid body. W21 product families decide by family (a surfboard, a piece
    of furniture or a PV array is solid even though its direction carries W2 housing keys); W2/W17 directions carry a
    `wall`. None = unknown."""
    from api.cad.family_mode import SOLID, family_of

    d = _direction(design)
    if d is None or not d.cad_parameters:
        return None
    if (fam := family_of(d)) is not None:
        return fam not in SOLID
    return "wall" in d.cad_parameters


def _assembly_digest(ctx) -> str | None:
    """C2 assembly group: engine version + the current version (the model the group is measured on)."""
    try:
        from api.cad.assembly import engine as asm_engine
        from api.cad.assembly import service as asm_service
    except Exception:  # noqa: BLE001
        return None
    if not asm_service.enabled():
        return None
    try:
        from api.studio import store

        cur = store.current(ctx.project.id)
    except Exception:  # noqa: BLE001
        cur = None
    return f"{asm_engine.ENGINE}:v{cur}"


def _digest(ctx) -> str:
    keep = {n: ctx.artifact(n).model_dump(mode="json", exclude={"generated_at", "status"}) for n in (1, 2, 3) if ctx.artifact(n) is not None}
    data = {"v": ENGINE_VERSION, "p": ctx.project.prompt, "n": ctx.project.name, "a": keep}
    asm = _assembly_digest(ctx)
    if asm:  # C2: only when CAD_ASSEMBLY=1, so the digests of cached artifacts stay valid with the flag off
        data["asm"] = asm
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- firmware


def _fw_meta_path(pid: str) -> Path:
    return files_dir(pid) / "firmware.json"


def _load_meta(pid: str) -> dict:
    try:
        return json.loads(_fw_meta_path(pid).read_text())
    except (OSError, ValueError):
        return {}


def _save_meta(pid: str, meta: dict) -> None:
    p = _fw_meta_path(pid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta))


def _fw_project(pid: str, spec: firmware.FirmwareSpec, meta: dict) -> FirmwareProject:
    return FirmwareProject(framework=spec.framework, mcu_family=spec.mcu_family, connectivity=spec.connectivity, url=firmware_url(pid),
                           files=list(meta.get("files", [])), generated_by=meta.get("generated_by", "template"),
                           pending_llm=meta.get("llm_state") == "pending")


def generate_llm_firmware(pid: str, spec: firmware.FirmwareSpec, fdigest: str) -> bool:
    """Synchronous LLM generation (the background thread calls this; tests call it with a mocked LLM)."""
    try:
        files, tag = firmware.llm_files(spec)
    except Exception as e:  # noqa: BLE001 — any LLM failure keeps the template
        log.info("LLM firmware failed for %s → template kept: %s", pid, e)
        meta = _load_meta(pid)
        if meta.get("digest") == fdigest:
            meta["llm_state"] = "failed"
            _save_meta(pid, meta)
        return False
    if _load_meta(pid).get("digest") != fdigest:  # the product changed meanwhile: this code is stale
        return False
    names = firmware.write_zip(files, files_dir(pid) / "firmware.zip")
    _save_meta(pid, {"digest": fdigest, "generated_by": tag, "files": names, "llm_state": "done"})
    return True


def ensure_firmware(pid: str, spec: firmware.FirmwareSpec, use_llm: bool = True, background: bool = True) -> FirmwareProject:
    fdigest = hashlib.sha1(json.dumps(spec.__dict__, sort_keys=True, default=str).encode()).hexdigest()[:16]
    zpath = files_dir(pid) / "firmware.zip"
    with _lock(pid):
        meta = _load_meta(pid)
        if meta.get("digest") != fdigest or not zpath.exists():
            names = firmware.write_zip(firmware.template_files(spec), zpath)
            meta = {"digest": fdigest, "generated_by": "template", "files": names, "llm_state": "none"}
            _save_meta(pid, meta)
        start = use_llm and llm.is_configured("fast") and meta.get("llm_state") == "none"
        if start:
            meta["llm_state"] = "pending"
            _save_meta(pid, meta)
    if start:
        if background:
            threading.Thread(target=generate_llm_firmware, args=(pid, spec, fdigest), name=f"firmware-{pid}", daemon=True).start()
        else:
            generate_llm_firmware(pid, spec, fdigest)
            meta = _load_meta(pid)
    return _fw_project(pid, spec, meta)


# --------------------------------------------------------------------------- compute


def _bom(ctx, spec) -> list[BOMItem]:
    from api.costs import lcsc

    brief = ctx.artifact(1)
    items = list(spec.bom) if spec is not None and spec.bom else list(getattr(brief, "pasted_bom", []) or [])
    try:
        return lcsc.match_bom(items, order_qty=5) if any(i.lcsc_pn is None for i in items) else items
    except Exception:  # noqa: BLE001
        return items


def compute(ctx, llm_firmware: bool = True, background: bool = True, with_firmware: bool = True) -> EngineeringArtifact:
    """`with_firmware=False` (W21b): figures only, no firmware zip written (Studio before/after comparisons)."""
    from api.stages.runner import load_fixture

    pid = ctx.project.id
    brief, design, spec = ctx.artifact(1), ctx.artifact(2), ctx.artifact(3)
    notes: list[Assumption] = []
    fallback, reason = False, None
    if spec is None:
        spec = load_fixture(ctx.project.example, 3, pid)
        fallback, reason = True, "stage 3 (CAD + spec) not run: geometry and BOM of the cached example"
    elif spec.fallback:
        fallback, reason = True, "stage 3 served a cached example"
    text = site_install.project_text(ctx)
    family = _family(design)
    key = cat.detect_category(text, getattr(brief, "category", None), family)
    pack = cat.load_pack(key)
    params = pack.get("params", {})
    notes.append(Assumption(id="e1", text=f"Engineering category '{pack['title']}' detected from the product description"
                            + (f" and the '{family}' shape family" if family else ""), label=Label.estimate, stage=None))

    volume = measured_volume(pid, spec)
    geo = physics.Geometry(length=spec.overall_dimensions.length, width=spec.overall_dimensions.width, height=spec.overall_dimensions.height,
                           mass=spec.weight, volume=volume, shell=_is_shell(design))
    bom = _bom(ctx, spec)
    bom_text = "\n".join(f"{b.part} {b.description or ''}" for b in bom)
    site = bool(pack.get("site_install"))
    sol = solar.solar_design(text) if site else None
    arch = None if site else electronics.architecture(bom, pack, text)
    if arch is not None and "(implied)" in arch.mcu_part:
        notes.append(Assumption(id="e2", text="Electronics architecture completed with the category's typical blocks (the BOM has no MCU)", label=Label.estimate))
    from api.cad.family_mode import family_of, fparams

    d = _direction(design)
    checks = physics.physics_checks(pack, geo, arch, text, bom_text, fparams(d) if d is not None and family_of(d) else None)
    if sol is not None:
        checks = solar.solar_checks(sol) + checks
        if sol.location_assumed:
            notes.append(Assumption(id="e3", text=f"Site location not in the prompt: {sol.location} used as the demo site", label=Label.estimate))
    fw = None
    if arch is not None and with_firmware:
        fspec = firmware.spec_from(arch, getattr(brief, "product_name", None) or ctx.project.name, params.get("connectivity", "BLE GATT service"))
        try:
            fw = ensure_firmware(pid, fspec, use_llm=llm_firmware, background=background)
        except Exception as e:  # noqa: BLE001 — the checks still stand without the zip
            log.warning("firmware zip failed for %s: %s", pid, e)
    vol_for_proto = volume or lv(geo.bbox_cm3 * 0.15, "cm³", "estimate", "No STEP volume: 15% of the bounding box (shell estimate)", nd=1)
    proto = prototype.prototype_path(pack, vol_for_proto, bom, arch, sol)
    installers = site_install.installers() if site else []
    notes.append(Assumption(id="e4", text="Physics checks are concept-level (rigid-body statics, rules of thumb): validate with the listed tests", label=Label.estimate))
    assembly = None
    group = _assembly_group(pid)
    if group is not None:  # C2 (CAD_ASSEMBLY=1): measured assembly checks, domain "assembly"
        checks = checks + group[0]
        assembly = group[1]
        notes.append(Assumption(id="e5", text="Assembly mates are inferred from the part roles and the product family (rules shown "
                                "per joint); interference, clearance and screw material are measured on the version's STEP",
                                label=Label.estimate))
    return EngineeringArtifact(
        project_id=pid, generated_by="code", fallback=fallback, fallback_reason=reason, assumptions=notes,
        category=key, category_title=pack["title"], partner_word=pack.get("partner_word", "factories"), site_install=site,
        product_name=getattr(brief, "product_name", None) or ctx.project.name, inputs_digest=_digest(ctx),
        standards=cat.standards_for(pack), risks=cat.risks_for(pack), tests=cat.tests_for(pack), checks=checks,
        electronics=arch, firmware=fw, prototype=proto, solar=sol, installers=installers,
        build_strategy=strategy.build_strategy(key, sol),
        unit_basis="per_installation" if site else "per_unit", installation_cost=_installed(ctx, sol), assembly=assembly,
    )


def _assembly_group(pid: str):
    try:
        from api.cad.assembly import service as asm_service
    except Exception:  # noqa: BLE001
        return None
    return asm_service.engineering_group(pid)


def _installed(ctx, sol):
    """W21e: the installed price of one installation, same source as stage 5 (battery included when the BOM has one)."""
    if sol is None:
        return None
    try:
        from api.costs.site import installed_price

        return installed_price(ctx, sol)[0]
    except Exception:  # noqa: BLE001
        return sol.install_cost


def _cache_path(pid: str) -> Path:
    return files_dir(pid) / "engineering.json"


def _refresh_firmware(art: EngineeringArtifact) -> EngineeringArtifact:
    """The background LLM may have replaced the zip since the artifact was cached."""
    if art.firmware is not None:
        meta = _load_meta(art.project_id)
        if meta:
            art.firmware.generated_by = meta.get("generated_by", art.firmware.generated_by)
            art.firmware.files = list(meta.get("files", art.firmware.files))
            art.firmware.pending_llm = meta.get("llm_state") == "pending"
    return art


def engineering_for_ctx(ctx, llm_firmware: bool = False, force: bool = False) -> EngineeringArtifact:
    pid = ctx.project.id
    digest = _digest(ctx)
    path = _cache_path(pid)
    if not force and path.exists():
        try:
            cached = EngineeringArtifact.model_validate_json(path.read_text())
            if cached.inputs_digest == digest:
                return _refresh_firmware(cached)
        except Exception:  # noqa: BLE001 — stale/old schema: recompute
            pass
    art = compute(ctx, llm_firmware=llm_firmware)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(art.model_dump_json())
    except OSError as e:
        log.warning("engineering cache not written for %s: %s", pid, e)
    return art


def get_engineering(project_id: str, force: bool = False) -> EngineeringArtifact:
    from api.stages import runner

    return engineering_for_ctx(runner.build_context(project_id, 0), llm_firmware=True, force=force)


def recompute_engineering(project_id: str, llm_firmware: bool = True) -> EngineeringArtifact:
    """Force a recompute from the current project state (call after each Studio refine / version restore)."""
    from api.stages import runner

    return engineering_for_ctx(runner.build_context(project_id, 0), llm_firmware=llm_firmware, force=True)
