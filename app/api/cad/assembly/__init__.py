"""Assemblies (C2, behind CAD_ASSEMBLY=1): a version's parts connected by build123d Joints, with measured checks.

    GET /projects/{id}/assembly?version=n  → ProjectAssembly (contracts/api.md "Assembly (C2)"); 404 while CAD_ASSEMBLY=0

Modules: engine.py (solids → joints → pose, motion study, interference / clearance / engagement), mates.py (mate rules from
the part roles, names and family), fasteners.py (screws / inserts, C1's api.cad.stdparts when present), checks.py
(EngineeringCheck rows, domain "assembly"), service.py (per-version cache + hooks for engineering, parts and costs).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException


def register(router: APIRouter) -> None:
    from contracts.artifacts import ProjectAssembly

    from api.cad.assembly import service
    from api.stages import runner

    @router.get("/projects/{project_id}/assembly", response_model=ProjectAssembly, tags=["assembly"])
    def get_assembly(project_id: str, version: int | None = None, refresh: bool = False) -> ProjectAssembly:
        if not service.enabled():
            raise HTTPException(404, "assembly checks are off (CAD_ASSEMBLY=0)")
        runner.get_project(project_id)  # 404 via runner.NotFound
        return service.assembly_for(project_id, version, force=refresh)
