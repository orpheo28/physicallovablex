"""FastAPI app. Owner: W0 — Wave 1 sessions never edit this file.

Run from mvp/:  uv run uvicorn api.main:app --reload --port 8000
Routes: contracts/api.md. Plug-ins: api/stages/registry.py (auto-discovered by api/discovery.py).
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

load_dotenv()

from contracts.artifacts import (  # noqa: E402
    Assumption,
    AutorunResult,
    AutorunState,
    AutorunStatus,
    CreateProjectRequest,
    Factory,
    FactoryPack,
    HealthResponse,
    Project,
    ProjectDetail,
    RegisterFactoryRequest,
    ResetResult,
    RFQWithQuotes,
    RunStageRequest,
    StageResult,
    StageStatus,
    UpdateStageRequest,
)

from api import db, llm, scope  # noqa: E402
from api.auth import Guards  # noqa: E402
from api.discovery import discover  # noqa: E402
from api.stages import defaults, runner  # noqa: E402
from api.stages.registry import PROVIDERS, STAGE_HANDLERS, StageContext  # noqa: E402

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("api")

VERSION = "0.1.0"
AUTORUN_STAGES = range(2, 8)



@asynccontextmanager
async def _lifespan(_: FastAPI):
    """Deployed (SEED_DEMO_ON_EMPTY=1): a fresh volume gets the two cached demo projects, an existing DB is left alone."""
    from api.housekeeping import prune_files

    prune_files()
    if os.getenv("SEED_DEMO_ON_EMPTY", "").lower() in ("1", "true", "yes"):
        try:
            if not runner.list_projects():
                from api.showcase import after_seed

                after_seed([runner.seed_example(ex) for ex in runner.available_examples()])
                log.info("empty database: seeded demo projects")
        except Exception as e:  # noqa: BLE001 — never block startup
            log.warning("demo seeding failed: %s", e)
    yield


app = FastAPI(title="PhysicalLovableX API", version=VERSION, lifespan=_lifespan)
app.add_middleware(Guards)  # added first = inner; CORS wraps it so 401/429 responses still carry CORS headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(runner.NotFound)
async def _not_found(_: Request, exc: runner.NotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


plugin_router = APIRouter()
DISCOVERED = discover(plugin_router)
app.include_router(plugin_router)
db.init_db()


# --------------------------------------------------------------------------- health


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        version=VERSION,
        llm_configured=llm.is_configured("main"),
        models=llm.configured_models(),
        registered_stages=sorted(STAGE_HANDLERS),
    )


# --------------------------------------------------------------------------- projects


@app.get("/projects", response_model=list[Project])
def list_projects() -> list[Project]:
    return runner.list_projects()


@app.post("/projects", response_model=Project, status_code=201)
def create_project(req: CreateProjectRequest) -> Project:
    if not req.example and not (req.pasted_bom or "").strip():  # a pasted BOM is already a physical product
        verdict = scope.check(req.prompt)
        if not verdict.in_scope:
            raise HTTPException(422, scope.message(verdict))
    project = Project(
        id=runner.new_project_id(),
        name=req.name or req.prompt.strip()[:60] or "Untitled product",
        mode=req.mode,
        prompt=req.prompt,
        pasted_bom=req.pasted_bom,
        example=req.example or defaults.guess_example(req.prompt),
    )
    return runner.save_project(project)


@app.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    stages = runner.stage_summaries(project_id)
    fallback_stages = [s.stage for s in stages if s.fallback]
    return ProjectDetail(project=runner.get_project(project_id), stages=stages, autorun=_load_autorun(project_id),
                         has_fallback=any(n <= 7 for n in fallback_stages), fallback_stages=fallback_stages)


def _check_stage(n: int) -> None:
    if not 1 <= n <= 13:
        raise HTTPException(404, f"stage {n} does not exist (1-13)")


@app.post("/projects/{project_id}/stages/{n}/run", response_model=StageResult)
def run_stage(project_id: str, n: int, req: RunStageRequest | None = None) -> StageResult:
    _check_stage(n)
    runner.get_project(project_id)
    if n == 7:  # matching consumes the Factory Pack (assembled from stages 1-6)
        runner.get_factory_pack(project_id, rebuild=True)
    artifact = runner.run_stage(project_id, n, (req or RunStageRequest()).inputs)
    return runner.to_result(project_id, n, artifact)


@app.get("/projects/{project_id}/stages/{n}", response_model=StageResult)
def get_stage(project_id: str, n: int) -> StageResult:
    _check_stage(n)
    runner.get_project(project_id)
    artifact = runner.get_artifact(project_id, n)
    if artifact is None:
        raise HTTPException(404, f"stage {n} not run yet")
    return runner.to_result(project_id, n, artifact)


@app.put("/projects/{project_id}/stages/{n}", response_model=StageResult)
def update_stage(project_id: str, n: int, req: UpdateStageRequest) -> StageResult:
    _check_stage(n)
    runner.get_project(project_id)
    if req.artifact.stage != n:
        raise HTTPException(422, f"artifact.stage={req.artifact.stage} does not match path stage {n}")
    artifact = req.artifact
    artifact.project_id = project_id
    status = StageStatus.validated if req.validate_stage else StageStatus(artifact.status)
    runner.save_artifact(project_id, n, artifact, status)
    return runner.to_result(project_id, n, runner.get_artifact(project_id, n))


# --------------------------------------------------------------------------- autorun (async)

_autorun_lock = threading.Lock()
_autorun_threads: dict[str, threading.Thread] = {}


def _load_autorun(project_id: str) -> AutorunStatus | None:
    with db.session() as sess:
        row = sess.get(db.AutorunRow, project_id)
        return AutorunStatus.model_validate_json(row.data) if row else None


def _save_autorun(project_id: str, st: AutorunStatus) -> None:
    with db.session() as sess:
        row = sess.get(db.AutorunRow, project_id) or db.AutorunRow(project_id=project_id, data="")
        row.data = st.model_dump_json()
        sess.add(row)
        sess.commit()


AUTOFILL_ASSUMPTION_ID = "a8_autofill"
AUTOFILL_ASSUMPTION_TEXT = "Auto-approved in autofill mode — review and change the selected factory before any real order"


def _autofill_approve(project_id: str) -> None:
    """Stage 8 approval of the recommended quote (same path as inputs {"approve": true, "quote_id": <recommended>}), then mark it."""
    neg = runner.get_artifact(project_id, 8)
    inputs: dict = {"approve": True}
    if neg is not None and getattr(neg, "recommendation", None) is not None:
        inputs["quote_id"] = neg.recommendation.quote_id
    art = runner.run_stage(project_id, 8, inputs)
    if not any(a.id == AUTOFILL_ASSUMPTION_ID for a in art.assumptions):
        art.assumptions.append(Assumption(id=AUTOFILL_ASSUMPTION_ID, text=AUTOFILL_ASSUMPTION_TEXT, label="estimate", stage=8))
    runner.save_artifact(project_id, 8, art, StageStatus.draft)


def _run_autorun(project_id: str, st: AutorunStatus) -> list[StageResult]:
    """Stage 1 if missing, then 2-7 with defaults; through=13 (autofill) continues with 8 (+ auto-approval), 9-13 and the
    Factory Pack. Each stage is capped by the runner (STAGE_TIMEOUT_S → fixture)."""
    results: list[StageResult] = []

    def step(n: int, inputs: dict | None = None) -> None:
        st.current_stage = n
        _save_autorun(project_id, st)
        if n == 7:  # matching consumes the Factory Pack (assembled from stages 1-6)
            runner.get_factory_pack(project_id, rebuild=True)
        results.append(runner.to_result(project_id, n, runner.run_stage(project_id, n, inputs)))
        st.completed_stages.append(n)
        _save_autorun(project_id, st)

    try:
        if runner.get_artifact(project_id, 1) is None:
            step(1)
        for n in AUTORUN_STAGES:
            inputs = {}
            if n == 3:  # sensible default: chosen, else first design direction
                design = runner.get_artifact(project_id, 2)
                if design is not None:
                    inputs["direction_id"] = design.chosen_direction_id or design.directions[0].id
            step(n, inputs)
        if st.through >= 13:
            for n in range(8, 14):
                step(n)
                if n == 8:
                    _autofill_approve(project_id)
                    results[-1] = runner.to_result(project_id, 8, runner.get_artifact(project_id, 8))
            runner.get_factory_pack(project_id, rebuild=True)
        st.state = AutorunState.done
    except Exception as e:  # noqa: BLE001 — only DB-level failures reach here (stages never raise)
        log.exception("autorun failed for %s", project_id)
        st.state, st.error = AutorunState.failed, f"{type(e).__name__}: {e}"[:300]
    st.current_stage, st.finished_at = None, datetime.now(timezone.utc)
    _save_autorun(project_id, st)
    return results


@app.post("/projects/{project_id}/autorun", response_model=AutorunResult, status_code=status.HTTP_202_ACCEPTED)
def autorun(project_id: str, wait: bool = False, through: int = 7) -> AutorunResult | JSONResponse:
    """Default: 202 at once, stages 1-7 run in a background thread; poll GET /projects/{id} (`autorun`, `stages`).
    `?through=13`: autofill — also stage 8 with the recommended quote auto-approved, stages 9-13 and the Factory Pack.
    `?wait=true`: synchronous (200 + all results) — scripts and tests."""
    runner.get_project(project_id)
    if through not in (7, 13):
        raise HTTPException(422, "through must be 7 or 13")
    with _autorun_lock:
        th = _autorun_threads.get(project_id)
        if th is not None and th.is_alive():  # idempotent: a second POST while running just reports progress
            return AutorunResult(project_id=project_id, autorun=_load_autorun(project_id))
        st = AutorunStatus(state=AutorunState.running, through=through, started_at=datetime.now(timezone.utc))
        _save_autorun(project_id, st)
        if wait:
            _autorun_threads.pop(project_id, None)
        else:
            th = threading.Thread(target=_run_autorun, args=(project_id, st), name=f"autorun-{project_id}", daemon=True)
            _autorun_threads[project_id] = th
            th.start()
            return AutorunResult(project_id=project_id, autorun=st)
    results = _run_autorun(project_id, st)
    body = AutorunResult(project_id=project_id, results=results, autorun=st)
    return JSONResponse(status_code=200, content=body.model_dump(mode="json"))


@app.get("/projects/{project_id}/factory-pack", response_model=FactoryPack)
def factory_pack(project_id: str, rebuild: bool = False) -> FactoryPack:
    runner.get_project(project_id)
    return runner.get_factory_pack(project_id, rebuild=rebuild)


@app.get("/projects/{project_id}/export")
def export(project_id: str) -> Response:
    runner.get_project(project_id)
    ctx = runner.build_context(project_id, 0)
    ctx.factory_pack = runner.get_factory_pack(project_id)
    fn = PROVIDERS.get("export_pdf")
    pdf: bytes
    try:
        if fn is None:
            raise LookupError("no export_pdf provider registered")
        pdf = fn(ctx)
    except Exception as e:  # noqa: BLE001
        if fn is not None:
            log.warning("export provider failed → stub PDF: %s", e)
        pdf = defaults.stub_pdf(ctx)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="launch-dossier-{project_id}.pdf"'},
    )


# --------------------------------------------------------------------------- demo


@app.post("/demo/reset", response_model=ResetResult)
def demo_reset() -> ResetResult:
    db.reset_db()
    try:  # the factory portal reads the MCP store: wipe live RFQs/quotes and re-seed the fictional partners (factories, integrator, installers)
        from factory_mcp import network

        network.reset()
    except Exception as e:  # noqa: BLE001 — the reset of the app DB must still succeed
        log.warning("factory network reset failed: %s", e)
    projects = [runner.seed_example(ex) for ex in runner.available_examples()]
    from api.showcase import after_seed  # W21: showcase Studio versions + engineering cache

    after_seed(projects)
    return ResetResult(projects=projects)


# --------------------------------------------------------------------------- factory portal


def _network():
    fn = PROVIDERS.get("network")
    if fn is not None:
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            log.warning("network provider failed → fixtures: %s", e)
    return defaults.FixtureNetwork()


@app.get("/factories", response_model=list[Factory])
def list_factories() -> list[Factory]:
    return _network().list_factories()


@app.post("/factories", response_model=Factory, status_code=201)
def register_factory(req: RegisterFactoryRequest) -> Factory:
    """Factory onboarding (PRD §10 `register_capacity`) → a new Fictional — demo data factory in the MCP store."""
    from factory_mcp import network

    fid = network.register_capacity(
        name=req.name, region=req.region, processes=[str(getattr(p, "value", p)) for p in req.processes],
        materials=req.materials, moq=req.moq, certifications=req.certifications, lead_time_days=req.lead_time_days,
        monthly_capacity=req.monthly_capacity, current_load_pct=req.current_load_pct, archetype=req.archetype,
        personality=req.personality,
    )
    return network.get_factory(fid)


@app.get("/factories/{factory_id}", response_model=Factory)
def get_factory(factory_id: str) -> Factory:
    f = _network().get_factory(factory_id)
    if f is None:
        raise HTTPException(404, f"factory {factory_id} not found")
    return f


@app.get("/factories/{factory_id}/rfqs", response_model=list[RFQWithQuotes])
def factory_rfqs(factory_id: str) -> list[RFQWithQuotes]:
    if _network().get_factory(factory_id) is None:
        raise HTTPException(404, f"factory {factory_id} not found")
    return _network().list_rfqs(factory_id)


__all__ = ["app", "StageContext"]
