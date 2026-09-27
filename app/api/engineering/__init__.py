"""Engineering layer (W20): category packs, physics checks on the measured CAD, electronics architecture, firmware
skeleton, prototype path and site-install mode (rooftop solar → installers).

Routes (auto-registered by api/discovery.py):
    GET  /projects/{id}/engineering            EngineeringArtifact, computed from the current project state (cached by digest)
    POST /projects/{id}/engineering/recompute  force a recompute (same as recompute_engineering)
    GET  /files/{id}/firmware.zip              generated firmware project ("Generated code — not compiled or tested")

Integration (W17 Studio / W21): call `recompute_engineering(project_id)` after each refine commit.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response


def register(router: APIRouter) -> None:
    from contracts.artifacts import EngineeringArtifact

    from api.engineering.service import files_dir, get_engineering, recompute_engineering
    from api.stages import runner

    @router.get("/projects/{project_id}/engineering", response_model=EngineeringArtifact, tags=["engineering"])
    def engineering(project_id: str, refresh: bool = False) -> EngineeringArtifact:
        runner.get_project(project_id)  # 404 via runner.NotFound
        return get_engineering(project_id, force=refresh)

    @router.post("/projects/{project_id}/engineering/recompute", response_model=EngineeringArtifact, tags=["engineering"])
    def engineering_recompute(project_id: str) -> EngineeringArtifact:
        runner.get_project(project_id)
        return recompute_engineering(project_id)

    def _zip(project_id: str) -> Response:
        if not project_id.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(404, "firmware not found")
        path = files_dir(project_id) / "firmware.zip"
        if not path.is_file():
            raise HTTPException(404, f"no firmware generated for project {project_id} — GET /projects/{project_id}/engineering first")
        return Response(content=path.read_bytes(), media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="firmware-{project_id}.zip"', "Cache-Control": "no-store"})

    @router.api_route("/files/{project_id}/firmware.zip", methods=["GET", "HEAD"], tags=["engineering"])
    def firmware_zip(project_id: str) -> Response:
        return _zip(project_id)

    # /files/{project_id}/{filename} (W2, api/cad/files.py) is registered earlier and only serves CAD/image types:
    # move this more specific route in front of it so firmware.zip resolves here.
    route = router.routes.pop()
    router.routes.insert(0, route)
