"""POST /projects/{project_id}/stages/2/render?direction_id=dN — on-demand AI concept render of one direction.

Stage 2 auto-renders only the first LLM_IMAGE_MAX_RENDERS directions (images are the largest LLM cost); the others are
rendered when the founder asks. Same 25 s call timeout / 27 s budget; a failed render returns the artifact unchanged.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from contracts.artifacts import StageResult


def register(router: APIRouter) -> None:
    @router.post("/projects/{project_id}/stages/2/render", response_model=StageResult, tags=["cad"])
    def render_direction_now(project_id: str, direction_id: str) -> StageResult:
        from api.cad.directions import render_on_demand
        from api.stages import runner

        runner.get_project(project_id)  # 404 via runner.NotFound
        try:
            art = render_on_demand(project_id, direction_id)
        except KeyError as e:
            raise HTTPException(404, f"direction {direction_id} not found") from e
        except LookupError as e:
            raise HTTPException(404, f"stage 2 not run yet for {project_id}") from e
        return runner.to_result(project_id, 2, art)
