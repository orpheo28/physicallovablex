"""Reference-based AI product photos + listing kit (W27).

    render_product_photo(project_id, version, shot, reference_png=None) -> ProductPhoto   (raises PhotoFailed)
    start_job(project_id, version, shots, reference_png=None) -> PhotoJob                  (background thread)
    project_photos(project_id) -> ProjectPhotos                                            (GET /projects/{id}/photos)

Reference, in order: (a) the PNG/JPEG the client captured from the 3D viewer (validated, saved as ref_v<n>.png so
later shots reuse it); (b) the Blender render of the CAD (hero_v<n>.png, or hero_<dN>.png of the chosen direction for
version 1 / non-Studio projects); (c) none → text-only prompt (product described from the design direction).
With a reference the prompt directs light / surface / lens / framing only (api/cad/photos/shots.py).

A photo is written to photo_v<n>_<shot>.png only on success (tmp + rename): a failed shot (timeout, 402, no image)
keeps the previous file and the previous entry in Version.preview.photos. hero_studio also becomes preview.render_url.
Kit shots are attached to stage 13 (BrandArtifact.listing_photos) when it exists; the dossier prints them.
"""

from __future__ import annotations

import io
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from api.cad import renders
from api.cad.photos import shots as S
from contracts.artifacts import PhotoJob, ProductPhoto, ProjectPhotos

log = logging.getLogger("cad.photos")

LABEL_REF = "Photo-styled from the CAD (AI image, geometry from our CAD)"
LABEL_NOREF = "AI concept image (no CAD reference)"
LABEL_STAGED = "Staged scene — illustrative"
MAX_UPLOAD = 2 * 1024 * 1024
TIMEOUT_S = float(os.getenv("PHOTO_TIMEOUT_S", "60"))
LONG_EDGE = 1280


class PhotoFailed(Exception):
    def __init__(self, reason: str, status: int | None = None):
        super().__init__(reason)
        self.reason, self.status = reason, status


class BadImage(ValueError):
    def __init__(self, reason: str, status: int = 415):
        super().__init__(reason)
        self.reason, self.status = reason, status


class Conflict(Exception):
    pass


# --------------------------------------------------------------------------- labels / validation


def label_for(shot: str, reference: str) -> str:
    base = LABEL_NOREF if reference == "none" else LABEL_REF
    return f"{base} · {LABEL_STAGED}" if S.SHOTS[shot].staged else base


def validate_image(raw: bytes) -> bytes:
    """Client capture → PNG bytes. ≤ 2 MB, PNG or JPEG by magic bytes AND decodable, 64-4096 px a side."""
    if not raw:
        raise BadImage("empty image", 422)
    if len(raw) > MAX_UPLOAD:
        raise BadImage(f"image is {len(raw) / 1e6:.1f} MB — 2 MB max", 413)
    if not (raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:3] == b"\xff\xd8\xff"):
        raise BadImage("only PNG or JPEG images are accepted", 415)
    from PIL import Image

    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:  # noqa: BLE001
        raise BadImage(f"image could not be decoded ({type(e).__name__})", 415) from None
    if not (64 <= min(im.size) and max(im.size) <= 4096):
        raise BadImage(f"image is {im.size[0]}×{im.size[1]} px — 64 to 4096 px a side", 422)
    if im.mode in ("RGBA", "LA", "P"):  # transparent viewer canvas → the studio background, not black
        bg = Image.new("RGB", im.size, (0xF4, 0xF1, 0xEA))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    out = io.BytesIO()
    im.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()


# --------------------------------------------------------------------------- context


def _files(pid: str, name: str) -> Path | None:
    from api.cad.files import resolve_file

    return resolve_file(pid, name)


def _versions(pid: str):
    from api.studio import store

    return store


def _design(pid: str, n: int | None):
    from api.stages import runner

    if n is not None:
        snap = _versions(pid).load_snapshot(pid, n)
        if snap.get(2) is not None:
            return snap.get(1) or runner.get_artifact(pid, 1), snap[2]
    return runner.get_artifact(pid, 1), runner.get_artifact(pid, 2)


def _chosen(design):
    if design is None:
        return None
    return next((d for d in design.directions if d.id == design.chosen_direction_id), design.directions[0])


def find_reference(pid: str, n: int | None) -> tuple[bytes | None, str]:
    """(reference bytes, 'viewer' | 'cad_render' | 'none')."""
    if n is not None and (p := _files(pid, f"ref_v{n}.png")):
        return p.read_bytes(), "viewer"
    if n is not None and (p := _files(pid, f"hero_v{n}.png")):
        return p.read_bytes(), "cad_render"
    if n is None or n == 1:
        _, design = _design(pid, n)
        d = _chosen(design)
        if d is not None and (p := _files(pid, f"hero_{d.id}.png")):
            return p.read_bytes(), "cad_render"
    return None, "none"


def category_of(pid: str, n: int | None) -> str:
    from api.engineering.category import detect_category
    from api.stages import runner

    try:
        project = runner.get_project(pid)
        brief, design = _design(pid, n)
        d = _chosen(design)
        text = " ".join(filter(None, [project.prompt, project.name, getattr(brief, "one_liner", None),
                                      getattr(brief, "product_name", None)]))
        family = None
        if d is not None:
            from api.cad.family_mode import family_of

            family = family_of(d)
        return detect_category(text, getattr(brief, "category", None), family)
    except Exception as e:  # noqa: BLE001 — the generic scene is fine
        log.info("category for %s: %s", pid, e)
        return "generic"


def product_text(pid: str, n: int | None) -> str:
    """Text-only fallback: the product described from the design direction (what renders.build_prompt uses)."""
    brief, design = _design(pid, n)
    d = _chosen(design)
    what = (getattr(brief, "one_liner", "") or getattr(brief, "product_name", "") or "a small electronic product").rstrip(".")
    if d is None:
        return what + "."
    dm = d.dimensions
    return (f"{what}. {d.description.rstrip('.')}. Form: {d.shape}. Overall size {dm.length.value:.0f} × {dm.width.value:.0f}"
            f" × {dm.height.value:.0f} mm (L × W × H). Material: {d.material}. Finish and colour: {d.finish}.")


def build_prompt(shot: str, category: str | None, reference: str, pid: str | None = None, n: int | None = None) -> str:
    if reference != "none":
        return S.shot_prompt(shot, category)
    return S.fallback_prompt(shot, category, product_text(pid, n) if pid else "a consumer hardware product.")


# --------------------------------------------------------------------------- one photo


def _save(raw: bytes, path: Path, aspect: str) -> None:
    """Centre-crop to the shot's aspect ratio, fit the long edge to LONG_EDGE, write atomically."""
    from PIL import Image

    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w_r, h_r = (int(x) for x in aspect.split(":"))
    target = w_r / h_r
    if abs(im.width / im.height - target) > 0.01:
        if im.width / im.height > target:
            w = round(im.height * target)
            im = im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, im.height))
        else:
            h = round(im.width / target)
            im = im.crop((0, (im.height - h) // 2, im.width, (im.height - h) // 2 + h))
    scale = LONG_EDGE / max(im.size)
    if scale < 1:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    tmp = path.with_suffix(".tmp")
    im.save(tmp, format="PNG", optimize=True)
    tmp.replace(path)


def _generate(prompt: str, reference: bytes | None, aspect: str, model: str | None, deadline: float) -> bytes:
    last: Exception | None = None
    for attempt in range(2):
        left = deadline - time.monotonic()
        if left < 5:
            break
        try:
            return renders._call(prompt, min(TIMEOUT_S, left), reference=reference, aspect_ratio=aspect, model=model)
        except Exception as e:  # noqa: BLE001
            last = e
            code = getattr(e, "status_code", None)
            log.warning("photo attempt %d failed: %s", attempt + 1, str(e)[:200])
            if code == 402:
                raise PhotoFailed("Image credits exhausted (HTTP 402) — the previous photo is kept.", 402) from None
            if code in (401, 403, 429) or "request cap" in str(e):
                raise PhotoFailed(f"The image service refused the request ({code or 'cap'}) — the previous photo is kept.", code) from None
    reason = "timed out" if last is None or "timeout" in str(last).lower() else f"failed ({type(last).__name__})"
    raise PhotoFailed(f"The image model {reason} — the previous photo is kept.")


def render_product_photo(project_id: str, version: int | None, shot: str, reference_png: bytes | None = None, *,
                         model: str | None = None, out_dir: Path | None = None, deadline: float | None = None,
                         attach: bool = True) -> ProductPhoto:
    """Generate one shot of `version` into photo_v<n>_<shot>.png. `reference_png` = client viewer capture (validated
    and saved as ref_v<n>.png); None → Blender CAD render when present → text-only. Raises PhotoFailed / BadImage."""
    if shot not in S.SHOTS:
        raise KeyError(shot)
    if not (model or renders.image_model()) or not os.getenv("OPENROUTER_API_KEY"):
        raise PhotoFailed("No image model configured (OPENROUTER_API_KEY / LLM_IMAGE_MODEL).", 503)
    from api.cad.build import project_dir

    out = Path(out_dir) if out_dir else project_dir(project_id)
    tag = f"v{version}" if version is not None else "v0"
    if reference_png is not None:
        ref, kind = validate_image(reference_png), "viewer"
        (out / f"ref_{tag}.png").write_bytes(ref)
    else:
        ref, kind = find_reference(project_id, version)
    cat = category_of(project_id, version)
    prompt = build_prompt(shot, cat, kind, project_id, version)
    spec = S.SHOTS[shot]
    raw = _generate(prompt, ref, spec.aspect_ratio, model, deadline or time.monotonic() + 2 * TIMEOUT_S)
    name = f"photo_{tag}_{shot}.png"
    _save(raw, out / name, spec.aspect_ratio)
    photo = ProductPhoto(shot=shot, url=f"/files/{project_id}/{name}", label=label_for(shot, kind), reference=kind,
                         aspect_ratio=spec.aspect_ratio, staged=spec.staged, model=model or renders.image_model(),
                         version=version)
    if attach and version is not None:
        attach_photo(project_id, version, photo)
    return photo


def merge_photos(photos: list[ProductPhoto], new: ProductPhoto) -> list[ProductPhoto]:
    order = list(S.SHOTS)
    out = [p for p in photos if p.shot != new.shot] + [new]
    return sorted(out, key=lambda p: order.index(p.shot))


_manifest_lock = threading.Lock()


def _manifest(pid: str) -> Path:
    from api.cad.build import project_dir

    return project_dir(pid) / "photos.json"  # not served (.json is not in the /files whitelist)


def manifest_photos(pid: str, n: int) -> list[ProductPhoto]:
    import json

    f = _manifest(pid)
    try:
        raw = json.loads(f.read_text()) if f.exists() else {}
    except ValueError:
        raw = {}
    return [ProductPhoto.model_validate(p) for p in raw.get(str(n), [])]


def _save_manifest(pid: str, n: int, photos: list[ProductPhoto]) -> None:
    import json

    f = _manifest(pid)
    try:
        raw = json.loads(f.read_text()) if f.exists() else {}
    except ValueError:
        raw = {}
    raw[str(n)] = [p.model_dump(mode="json") for p in photos]
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(raw))
    tmp.replace(f)


def attach_photo(pid: str, n: int, photo: ProductPhoto) -> None:
    """photos.json (source of truth for GET /photos) + Version.preview.photos (newest per shot). hero_studio also
    becomes preview.render_url and the chosen direction's render_url in the version snapshot (so a preview rebuilt
    from the snapshot keeps it)."""
    from api.studio.engine import lock

    store = _versions(pid)
    with _manifest_lock:
        _save_manifest(pid, n, merge_photos(manifest_photos(pid, n), photo))
    with lock(pid):
        v = store.get_version(pid, n)
        if v is None or v.preview is None:
            return
        v.preview.photos = merge_photos(list(v.preview.photos), photo)
        if photo.shot == "hero_studio":
            v.preview.render_url = photo.url
            design = store.load_snapshot(pid, n).get(2)
            if (d := _chosen(design)) is not None:
                d.render_url = photo.url
                store.patch_snapshot(pid, n, {2: design})
        store.save_version(pid, v)


def attach_listing(pid: str, photos: list[ProductPhoto]) -> bool:
    """Stage 13 (when it exists): BrandArtifact.listing_photos = the kit shots of the current version."""
    from api.stages import runner

    brand = runner.get_artifact(pid, 13)
    if brand is None:
        return False
    kit = [p for p in photos if p.shot in S.LISTING_KIT]
    if not kit:
        return False
    brand.listing_photos = kit
    runner.save_artifact(pid, 13, brand, brand.status)
    return True


# --------------------------------------------------------------------------- jobs (one per project, in-process)

_jobs: dict[str, PhotoJob] = {}
_jobs_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def job_of(pid: str) -> PhotoJob:
    with _jobs_lock:
        return (_jobs.get(pid) or PhotoJob()).model_copy(deep=True)


def start_job(pid: str, n: int, shots: list[str], reference_png: bytes | None = None, *, kit: bool = False,
              model: str | None = None, sync: bool = False) -> PhotoJob:
    """Validate now (so the client gets 413 / 415 / 422 synchronously), generate in a background thread."""
    ref = validate_image(reference_png) if reference_png is not None else None
    with _jobs_lock:
        cur = _jobs.get(pid)
        if cur is not None and cur.state == "running":
            raise Conflict(f"photos for version {cur.version} are still being generated")
        job = _jobs[pid] = PhotoJob(state="running", version=n, shots=list(shots), started_at=_now())
    if ref is not None:  # saved once; every shot of the job then finds it as the viewer reference
        from api.cad.build import project_dir

        (project_dir(pid) / f"ref_v{n}.png").write_bytes(ref)
    args = (pid, n, list(shots), kit, model)
    if sync:
        _run_job(*args)
    else:
        threading.Thread(target=_run_job, args=args, daemon=True, name=f"photos-{pid}").start()
    return job.model_copy(deep=True)


def _set(pid: str, **fields) -> None:
    with _jobs_lock:
        j = _jobs.get(pid)
        if j is not None:
            for k, v in fields.items():
                setattr(j, k, v)


def _run_job(pid: str, n: int, shots: list[str], kit: bool, model: str | None) -> None:
    from concurrent.futures import ThreadPoolExecutor

    done: list[str] = []
    failed: list[str] = []
    errors: list[str] = []

    def one(shot: str) -> None:
        try:
            render_product_photo(pid, n, shot, None, model=model)
            done.append(shot)
            _set(pid, done=list(done))
        except Exception as e:  # noqa: BLE001 — a failed shot never breaks the job or the version
            failed.append(shot)
            errors.append(getattr(e, "reason", None) or f"{type(e).__name__}: {str(e)[:160]}")
            _set(pid, failed=list(failed))

    with ThreadPoolExecutor(max_workers=min(4, len(shots) or 1)) as ex:
        list(ex.map(one, shots))
    if kit and done:
        try:
            attach_listing(pid, version_photos(pid, n))
        except Exception as e:  # noqa: BLE001
            log.warning("listing photos for %s not attached to stage 13: %s", pid, e)
    _set(pid, state="done" if done else "failed", error=errors[0] if errors else None, finished_at=_now())


def version_photos(pid: str, n: int) -> list[ProductPhoto]:
    """Manifest (live generations) merged over Version.preview.photos (recorded showcases, or a rebuilt preview)."""
    v = _versions(pid).get_version(pid, n)
    out = list(v.preview.photos) if v is not None and v.preview is not None else []
    for p in manifest_photos(pid, n):
        out = merge_photos(out, p)
    return out


def project_photos(pid: str) -> ProjectPhotos:
    store = _versions(pid)
    n = store.current(pid) or None
    photos = version_photos(pid, n) if n else []
    return ProjectPhotos(project_id=pid, version=n, photos=photos, job=job_of(pid),
                         configured=bool(os.getenv("OPENROUTER_API_KEY")) and bool(renders.image_model()))


__all__ = ["render_product_photo", "start_job", "project_photos", "validate_image", "label_for", "find_reference",
           "build_prompt", "PhotoFailed", "BadImage", "Conflict", "LABEL_REF", "LABEL_NOREF", "LABEL_STAGED", "MAX_UPLOAD"]
