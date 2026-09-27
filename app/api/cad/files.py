"""GET /files/{project_id}/{filename} — CAD files referenced by CadFile.url and DesignDirection.glb_url. Owner: W2.

Lookup order: api/data/files/<project_id>/ (generated, FILES_DIR override) → api/cad/prebuilt/<project_id>/
(committed, so the demo shows 3D right after /demo/reset) → 404. Names are whitelisted (no path separators,
no leading dot) and the resolved path must stay inside its base directory.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from api.cad.build import PREBUILT_DIR, files_root

SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
MEDIA = {
    ".glb": "model/gltf-binary",
    ".step": "model/step",
    ".stp": "model/step",
    ".stl": "model/stl",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
}


def resolve_file(project_id: str, filename: str) -> Path | None:
    if not SAFE.match(project_id or "") or not SAFE.match(filename or "") or ".." in filename:
        return None
    if Path(filename).suffix.lower() not in MEDIA:
        return None
    for root in roots(project_id):
        candidate = (root / filename).resolve()
        if candidate.parent == root and candidate.is_file():
            return candidate
    return None


def roots(project_id: str) -> list[Path]:
    """Generated folder, committed prebuilt folder, and (W21 showcases) demo_<slug> → prebuilt/showcase_<slug>."""
    from api.showcase import alias_dir

    out = [(files_root() / project_id).resolve(), (PREBUILT_DIR / project_id).resolve()]
    if (alias := alias_dir(project_id)) is not None:
        out.append(alias.resolve())
    return out


def register(router: APIRouter) -> None:
    @router.api_route("/files/{project_id}/{filename}", methods=["GET", "HEAD"], tags=["files"])
    def get_file(project_id: str, filename: str) -> Response:
        path = resolve_file(project_id, filename)
        if path is None:
            raise HTTPException(status_code=404, detail=f"file {filename} not found for project {project_id}")
        disposition = "inline" if path.suffix.lower() in (".glb", ".png", ".svg", ".pdf") else "attachment"
        try:  # one read = one consistent snapshot: Content-Length always matches the body, even while stage 2/3 republish
            body = path.read_bytes()
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"file {filename} not found for project {project_id}") from None
        return Response(content=body, media_type=MEDIA[path.suffix.lower()], headers={
            "Content-Disposition": f'{disposition}; filename="{path.name}"',
            # generated files are rebuilt in place when a stage re-runs: never let a browser/proxy serve a stale copy
            "Cache-Control": "no-cache" if project_id.startswith("demo_") else "no-store",
        })
