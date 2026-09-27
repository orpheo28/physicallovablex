"""Studio routes (W17) — contract: contracts/api.md "Studio".

    POST /projects/{id}/studio/start          → 202 StudioAccepted {version: 1}
    POST /projects/{id}/refine {message}      → 202 StudioAccepted {version: n}
    GET  /projects/{id}/versions              → Version[] (poll every ~1-2 s while one is running)
    GET  /projects/{id}/versions/{n}          → Version
    POST /projects/{id}/versions/{n}/restore  → 200 Version (stage artifacts return to that version)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.stages import runner
from api.studio import engine, store
from contracts.artifacts import RefineRequest, StudioAccepted, Version


def register(router: APIRouter) -> None:
    @router.post("/projects/{project_id}/studio/start", response_model=StudioAccepted, status_code=status.HTTP_202_ACCEPTED,
                 tags=["studio"])
    def studio_start(project_id: str) -> StudioAccepted:
        runner.get_project(project_id)  # read-only demo / per-IP Studio cap: api/auth.py (Guards, STUDIO_RUN)
        try:
            return StudioAccepted(version=engine.start(project_id))
        except engine.Conflict as e:
            raise HTTPException(409, str(e)) from None

    @router.post("/projects/{project_id}/refine", response_model=StudioAccepted, status_code=status.HTTP_202_ACCEPTED,
                 tags=["studio"])
    def studio_refine(project_id: str, req: RefineRequest) -> StudioAccepted:
        runner.get_project(project_id)
        if not req.message.strip():
            raise HTTPException(422, "message is empty")
        try:
            return StudioAccepted(version=engine.refine(project_id, req.message))
        except engine.Conflict as e:
            raise HTTPException(409, str(e)) from None

    @router.get("/projects/{project_id}/versions", response_model=list[Version], tags=["studio"])
    def studio_versions(project_id: str) -> list[Version]:
        runner.get_project(project_id)
        return store.list_versions(project_id)

    @router.get("/projects/{project_id}/versions/{n}", response_model=Version, tags=["studio"])
    def studio_version(project_id: str, n: int) -> Version:
        runner.get_project(project_id)
        v = store.get_version(project_id, n)
        if v is None:
            raise HTTPException(404, f"version {n} not found")
        return v

    @router.post("/projects/{project_id}/versions/{n}/restore", response_model=Version, tags=["studio"])
    def studio_restore(project_id: str, n: int) -> Version:
        try:
            return engine.restore(project_id, n)
        except engine.Conflict as e:
            raise HTTPException(409, str(e)) from None
