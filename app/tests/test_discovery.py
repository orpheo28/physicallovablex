"""A new stage module dropped in an owned folder is picked up without editing api/main.py."""

import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

from api.discovery import discover
from api.stages import runner
from api.stages.registry import STAGE_HANDLERS

PROBE = Path(__file__).resolve().parent.parent / "api" / "costs" / "zz_probe_stage.py"
CODE = '''
from api.stages.registry import stage_handler
from api.stages.runner import load_fixture

@stage_handler(13)
def probe(ctx):
    a = load_fixture("desk_lamp", 13, ctx.project.id)
    a.generated_by = "code"
    a.chosen_name = "PROBE"
    return a

def register(router):
    @router.get("/probe")
    def _probe():
        return {"ok": True}
'''


def test_new_module_is_discovered_and_used():
    previous = STAGE_HANDLERS.get(13)
    PROBE.write_text(CODE)
    try:
        router = APIRouter()
        assert "api.costs.zz_probe_stage" in discover(router)
        assert 13 in STAGE_HANDLERS
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        assert TestClient(app).get("/probe").json() == {"ok": True}

        runner.db.init_db()
        from contracts.artifacts import Project

        runner.save_project(Project(id="probe", name="probe", mode="idea", prompt="lamp", example="desk_lamp"))
        art = runner.run_stage("probe", 13)
        assert art.chosen_name == "PROBE" and art.fallback is False and art.generated_by == "code"
    finally:
        PROBE.unlink(missing_ok=True)
        sys.modules.pop("api.costs.zz_probe_stage", None)
        if previous is None:
            STAGE_HANDLERS.pop(13, None)
        else:
            STAGE_HANDLERS[13] = previous


def test_failing_handler_falls_back_to_fixture():
    from contracts.artifacts import Project

    previous = STAGE_HANDLERS.get(5)
    STAGE_HANDLERS[5] = lambda ctx: 1 / 0
    try:
        runner.db.init_db()
        runner.save_project(Project(id="boom", name="boom", mode="idea", prompt="x", example="desk_lamp"))
        art = runner.run_stage("boom", 5)
        assert art.fallback is True and "ZeroDivisionError" in art.fallback_reason
    finally:
        if previous is None:
            STAGE_HANDLERS.pop(5, None)
        else:
            STAGE_HANDLERS[5] = previous
