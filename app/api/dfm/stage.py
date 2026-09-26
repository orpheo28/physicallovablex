"""Stage 4 — DFM. Owner: W2 (measured) + W4/W3 helper functions.

1. Measured: api.dfm.measure on the stage-3 STEP (draft, undercut, projection → tonnage, sampled wall).
   If this part fails, the handler raises and the runner serves the fixture.
2. AI-reviewed issues: api.agents.dfm_review.ai_review (W4)
3. Certifications:     api.agents.certification.certification_map (W4)
4. Component risks:    api.costs.lcsc.component_risk (W3)
Sections 2-4 each run in their own try/except; on failure that section comes from the project's cached
example (api/fixtures/<example>/04_dfm.json) with an Assumption saying so. ≥3 issues are guaranteed.
"""

from __future__ import annotations

import logging

from api.stages.registry import StageContext, stage_handler
from contracts.artifacts import Assumption, DFMArtifact, DFMIssue, ProcessType

log = logging.getLogger("dfm.stage")

MIN_ISSUES = 3


def _step_path(spec):
    from api.cad.files import resolve_file

    for f in spec.cad_files:
        if f.format == "step":
            parts = f.url.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "files":
                path = resolve_file(parts[1], parts[2])
                if path is not None:
                    return path
    raise FileNotFoundError("no STEP file available for the spec")


def _moulded_part(spec):
    for p in spec.parts:
        if p.process_hint in (ProcessType.injection_molding, ProcessType.injection_molding.value):
            return p
    return spec.parts[0] if spec.parts else None


def _fixture(example: str | None, project_id: str) -> DFMArtifact:
    from api.stages.runner import load_fixture

    return load_fixture(example, 4, project_id)


@stage_handler(4)
def run(ctx: StageContext) -> DFMArtifact:
    from api.dfm.measure import measure

    spec, brief = ctx.artifact(3), ctx.artifact(1)
    if spec is None:
        raise LookupError("stage 4 needs the spec (stage 3)")
    part = _moulded_part(spec)
    measured = measure(_step_path(spec), (0, 0, 1), finish=part.finish if part else None,
                       material=part.material if part else None, part_id=part.id if part else None)

    assumptions = [Assumption(id="a4_1", label="estimate", stage=4,
                              text="Measured checks assume a straight two-half tool pulling along ±Z (split line in the XY plane)"),
                   Assumption(id="a4_2", label="estimate", stage=4,
                              text="Clamp tonnage = projected area (in²) × 3 t/in² (PC/ABS) × 1.1 safety")]
    cached: DFMArtifact | None = None

    def fixture() -> DFMArtifact:
        nonlocal cached
        if cached is None:
            cached = _fixture(ctx.project.example, ctx.project.id)
        return cached

    def note(section: str, e: Exception) -> None:
        log.warning("stage 4 %s section from cached example: %s", section, e)
        assumptions.append(Assumption(id=f"a4_{len(assumptions) + 1}", label="estimate", stage=4,
                                      text=f"{section} section from cached example: {type(e).__name__}: {str(e)[:160]}"))

    live_llm = False
    try:
        from api.agents.dfm_review import ai_review

        ai = list(ai_review(spec, spec.bom, measured))
        try:
            from api.llm import is_configured

            live_llm = is_configured("main")
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001
        note("AI-reviewed issues", e)
        ai = [i for i in fixture().issues if i.method == "ai_reviewed"]

    try:
        if brief is None:
            raise LookupError("no brief (stage 1)")
        from api.agents.certification import certification_map

        certs = list(certification_map(brief, spec))
    except Exception as e:  # noqa: BLE001
        note("Certifications", e)
        certs = list(fixture().certifications)

    try:
        from api.costs.lcsc import component_risk, match_bom

        risks = list(component_risk(match_bom(spec.bom)))  # match first: risk needs the LCSC part (stock, alternatives)
    except Exception as e:  # noqa: BLE001
        note("Component risks", e)
        risks = list(fixture().component_risks)

    if len(measured) + len(ai) < MIN_ISSUES:
        extra = [i for i in fixture().issues if i.method == "ai_reviewed" and i not in ai]
        need = MIN_ISSUES - len(measured) - len(ai)
        if extra[:need]:
            ai += extra[:need]
            note("Additional AI-reviewed issues", LookupError("fewer than 3 live issues"))

    issues: list[DFMIssue] = []
    for i, x in enumerate(measured, 1):
        issues.append(x.model_copy(update={"id": f"m{i}"}))
    for i, x in enumerate(ai, 1):
        issues.append(x.model_copy(update={"id": f"a{i}"}))
    order = {"critical": 0, "major": 1, "minor": 2}
    issues.sort(key=lambda x: (order.get(str(getattr(x.severity, "value", x.severity)), 3), x.method != "measured"))

    generated_by = "code"
    if live_llm:
        from api.llm import model_for

        generated_by = f"llm:{model_for('main')}"
    return DFMArtifact(project_id=ctx.project.id, generated_by=generated_by, assumptions=assumptions,
                       issues=issues, component_risks=risks, certifications=certs)
