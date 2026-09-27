"""GET /projects/{project_id}/cad/code/{n} — the AI-written build123d program model_v{n}.py (W19).

files.py whitelists CAD/image suffixes only, so the program is served by this tiny route instead (text/x-python,
same lookup rules: api/data/files/<pid>/ then api/cad/prebuilt/<pid>/, safe names, path must stay in its base).
Hook-up (W21, api/main.py): `from api.cad.codegen.routes import register as register_codegen; register_codegen(router)`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from api.cad.files import SAFE


def resolve_code(project_id: str, n: int):
    if not SAFE.match(project_id or "") or not (0 < n < 10_000):
        return None
    from api.cad.files import roots

    for root in roots(project_id):  # generated, prebuilt, W21 showcase alias
        candidate = (root / f"model_v{n}.py").resolve()
        if candidate.parent == root and candidate.is_file():
            return candidate
    return None


def register(router: APIRouter) -> None:
    @router.api_route("/projects/{project_id}/cad/code/{n}", methods=["GET", "HEAD"], tags=["files"])
    def get_cad_code(project_id: str, n: int) -> Response:
        path = resolve_code(project_id, n)
        if path is None:
            raise HTTPException(status_code=404, detail=f"CAD program v{n} not found for project {project_id}")
        return Response(content=path.read_bytes(), media_type="text/x-python; charset=utf-8", headers={
            "Content-Disposition": f'inline; filename="{path.name}"', "Cache-Control": "no-store"})


router = APIRouter()
register(router)
