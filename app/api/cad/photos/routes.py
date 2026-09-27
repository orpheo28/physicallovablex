"""Product photo routes (W27) — contract: contracts/api.md "Product photos".

    POST /projects/{id}/versions/{n}/photo?shot=hero_studio   body: optional viewer capture → 202 PhotoAccepted
    POST /projects/{id}/photos/kit[?version=n&detail=true]     body: optional viewer capture → 202 PhotoAccepted
    GET  /projects/{id}/photos                                 → ProjectPhotos (poll ~2 s while job.state == running)

The image body is optional and may be sent as multipart/form-data (field `image`), JSON {"image_base64": "..."} (a
data: URL prefix is accepted) or a raw image/png | image/jpeg body. ≤ 2 MB, PNG/JPEG (413 / 415 / 422 otherwise).
Guards: api/auth.py (PHOTO_RUN) — DEMO_READONLY=1 → 403; per-IP PHOTO_RATE_LIMIT_PER_DAY (default 30 photo jobs, only
with a key; 0 disables). Here: no image model configured → 503.
"""

from __future__ import annotations

import base64
import binascii
import os

from fastapi import APIRouter, HTTPException, Request, status

from api.cad.photos import engine as E
from api.cad.photos import shots as S
from contracts.artifacts import PhotoAccepted, ProjectPhotos

def _guard(request: Request) -> None:
    """Read-only demo and the per-IP photo cap are enforced by api/auth.py (Guards, PHOTO_RUN); here: an image model."""
    if not (os.getenv("OPENROUTER_API_KEY") and os.getenv("LLM_IMAGE_MODEL")):
        raise HTTPException(503, "No image model configured")


async def _image_body(request: Request) -> bytes | None:
    ctype = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype == "multipart/form-data":
        form = await request.form()
        f = form.get("image")
        if f is None or isinstance(f, str):
            return None
        return await f.read(E.MAX_UPLOAD + 1)
    body = await request.body()
    if not body:
        return None
    if ctype == "application/json":
        import json

        try:
            b64 = (json.loads(body) or {}).get("image_base64")
        except (ValueError, AttributeError):
            raise HTTPException(422, "invalid JSON body") from None
        if not b64:
            return None
        if b64.startswith("data:"):
            b64 = b64.split(",", 1)[-1]
        if len(b64) > E.MAX_UPLOAD * 4 // 3 + 8:
            raise HTTPException(413, "image is larger than 2 MB")
        try:
            return base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(422, "image_base64 is not valid base64") from None
    if ctype in ("image/png", "image/jpeg"):
        return body
    raise HTTPException(415, "send the image as multipart (field 'image'), JSON {image_base64} or image/png | image/jpeg")


def _version(project_id: str, n: int | None) -> int:
    from api.stages import runner
    from api.studio import store

    runner.get_project(project_id)  # 404 via runner.NotFound
    n = n or store.current(project_id)
    if not n or store.get_version(project_id, n) is None:
        raise HTTPException(404, f"version {n} not found — start the Studio first")
    return n


def _reused(project_id: str, n: int, shot: str) -> PhotoAccepted | None:
    """Version n kept the previous look (Version.look_changed False) and already carries this shot: no new image call."""
    from api.studio import store

    v = store.get_version(project_id, n)
    if v is None or v.look_changed or v.preview is None or not any(p.shot == shot for p in v.preview.photos):
        return None
    return PhotoAccepted(version=n, shots=[shot])


def _start(project_id: str, n: int, shots: list[str], ref: bytes | None, kit: bool) -> PhotoAccepted:
    try:
        E.start_job(project_id, n, shots, ref, kit=kit)
    except E.BadImage as e:
        raise HTTPException(e.status, e.reason) from None
    except E.Conflict as e:
        raise HTTPException(409, str(e)) from None
    return PhotoAccepted(version=n, shots=shots)


def register(router: APIRouter) -> None:
    @router.post("/projects/{project_id}/versions/{n}/photo", response_model=PhotoAccepted,
                 status_code=status.HTTP_202_ACCEPTED, tags=["photos"])
    async def version_photo(project_id: str, n: int, request: Request, shot: str = "hero_studio", force: bool = False) -> PhotoAccepted:
        if shot not in S.SHOTS:
            raise HTTPException(422, f"unknown shot '{shot}' — one of {', '.join(S.SHOTS)}")
        n = _version(project_id, n)
        if not force and (reused := _reused(project_id, n, shot)) is not None:  # W21e: same look → the carried photo stands
            return reused
        ref = await _image_body(request)
        _guard(request)
        return _start(project_id, n, [shot], ref, kit=False)

    @router.post("/projects/{project_id}/photos/kit", response_model=PhotoAccepted, status_code=status.HTTP_202_ACCEPTED,
                 tags=["photos"])
    async def photo_kit(project_id: str, request: Request, version: int | None = None, detail: bool = True) -> PhotoAccepted:
        n = _version(project_id, version)
        ref = await _image_body(request)
        _guard(request)
        shots = [s for s in S.LISTING_KIT if detail or s != "detail_macro"]
        return _start(project_id, n, shots, ref, kit=True)

    @router.get("/projects/{project_id}/photos", response_model=ProjectPhotos, tags=["photos"])
    def photos(project_id: str) -> ProjectPhotos:
        from api.stages import runner

        runner.get_project(project_id)
        return E.project_photos(project_id)
