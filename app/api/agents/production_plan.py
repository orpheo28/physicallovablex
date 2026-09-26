"""Stage 6 — Production plan. Owner: W4.

Python decides process (spec hint, else material heuristic / LLM proposal), region cluster, lead times and the
critical-path total; the LLM (route "fast") only writes the reason per part and the assembly notes.
If the LLM is unavailable the plan is still produced from code-written reasons (generated_by = "code").
"""

from __future__ import annotations

import logging
import re
from typing import Literal

from contracts.artifacts import Label, ProcessStep, ProcessType, ProductionPlanArtifact, SpecArtifact, SpecPart
from pydantic import BaseModel, ConfigDict, Field

from api.agents import _planning as plan
from api.agents._common import AssumptionLog, estimate, llm_tag, render_prompt
from api.agents.dfm_review import has_cell
from api.llm import complete_json
from api.stages.registry import StageContext, stage_handler

log = logging.getLogger("agents.production_plan")

ProcessName = Literal["injection_molding", "cnc", "sheet_metal", "die_casting", "extrusion", "pcba", "assembly", "other"]


class _StepDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    part_id: str
    process: ProcessName | None = None
    reason: str = ""


class PlanDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    steps: list[_StepDraft] = Field(default_factory=list)
    assembly_notes: list[str] = Field(default_factory=list, max_length=6)


_HEURISTICS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(fr-?4|pcb|pcba|mcpcb)\b", re.I), "pcba"),
    (re.compile(r"\b(abs|pc|pp|pa\d*|nylon|pom|tpu|tpe|silicone|polycarbonate|resin|plastic)\b", re.I), "injection_molding"),
    (re.compile(r"\b(6063|extru\w*)\b", re.I), "extrusion"),
    (re.compile(r"\b(spcc|steel|stainless|sheet|zinc-plated)\b", re.I), "sheet_metal"),
    (re.compile(r"\b(zinc alloy|zamak|adc12|die[- ]?cast\w*|magnesium)\b", re.I), "die_casting"),
    (re.compile(r"\b(aluminium|aluminum|6061|7075|brass|titanium)\b", re.I), "cnc"),
]

_REASON_BY_PROCESS = {
    "injection_molding": "Plastic part with repeatable geometry; a mold pays back against CNC or printing at this quantity.",
    "cnc": "Metal part with tight features at low-to-mid volume; CNC avoids tooling cost and holds tolerance.",
    "sheet_metal": "Flat or bent metal part; stamping or laser + press-brake is the cheapest route at this quantity.",
    "die_casting": "Complex metal housing at volume; die casting gives near-net shape after a tool investment.",
    "extrusion": "Constant cross-section profile; extrusion + cut + finish is cheapest for this shape.",
    "pcba": "Electronics assembled by SMT from the BOM; turnkey PCBA keeps sourcing, placement and test in one place.",
    "assembly": "Assembly operation performed by the final-assembly line.",
    "other": "Process to confirm with the factory during RFQ.",
}


def choose_process(part: SpecPart) -> str:
    hint = getattr(part.process_hint, "value", part.process_hint)
    if hint:
        return hint
    text = f"{part.material} {part.name}"
    for pat, proc in _HEURISTICS:
        if pat.search(text):
            return proc
    return ProcessType.other.value


def reference_quantity(ctx: StageContext) -> int:
    costs, brief = ctx.artifact(5), ctx.artifact(1)
    if costs is not None and getattr(costs, "reference_quantity", None):
        return int(costs.reference_quantity)
    vols = getattr(brief, "target_volumes", None) or []
    return int(vols[len(vols) // 2]) if vols else plan.DEFAULT_LOT


def build_steps(spec: SpecArtifact, reasons: dict[str, str], processes: dict[str, str]) -> list[ProcessStep]:
    steps = []
    for part in spec.parts:
        proc = processes.get(part.id) or choose_process(part)
        days = plan.LEAD_TIME_DAYS[proc]
        tooled = proc in plan.TOOLED
        steps.append(
            ProcessStep(
                part_id=part.id,
                part_name=part.name,
                process=proc,  # type: ignore[arg-type]
                reason=reasons.get(part.id) or _REASON_BY_PROCESS[proc],
                region=plan.REGION_BY_PROCESS[proc],
                lead_time_days=estimate(
                    days, "days",
                    f"Typical {proc.replace('_', ' ')} lead time incl. {'tooling and first shots' if tooled else 'setup and first article'} — planning assumption",
                ),  # fmt: skip
            )
        )
    return steps


@stage_handler(6)
def run_production_plan(ctx: StageContext) -> ProductionPlanArtifact:
    spec = ctx.artifact(3)
    if spec is None or not spec.parts:
        raise ValueError("stage 6 needs the stage 3 spec (no parts found)")
    qty = reference_quantity(ctx)
    log_ = AssumptionLog(6)
    reasons: dict[str, str] = {}
    processes: dict[str, str] = {}
    notes: list[str] = []
    generated_by = "code"
    try:
        prompt = render_prompt(
            "production_plan",
            product=spec.product_name,
            quantity=str(qty),
            parts=[
                {"id": p.id, "name": p.name, "material": p.material, "finish": p.finish,
                 "process_hint": getattr(p.process_hint, "value", p.process_hint), "tolerance": p.tolerance,
                 "wall_mm": p.wall_thickness.value if p.wall_thickness else None}
                for p in spec.parts
            ],  # fmt: skip
            electronics=[b.part for b in spec.bom if getattr(b.category, "value", b.category) == "electronic"][:12],
            battery=has_cell(spec.bom),
        )
        draft = complete_json("fast", prompt, PlanDraft, max_tokens=2500)
        valid = {p.id for p in spec.parts}
        for s in draft.steps:
            if s.part_id in valid:
                if s.reason.strip():
                    reasons[s.part_id] = s.reason.strip()
                if s.process:
                    processes[s.part_id] = s.process
        for p in spec.parts:  # a spec hint always wins over the LLM's proposal
            if getattr(p.process_hint, "value", p.process_hint):
                processes.pop(p.id, None)
        notes = [n.strip() for n in draft.assembly_notes if n.strip()]
        generated_by = llm_tag("fast")
    except Exception as e:  # noqa: BLE001 — planner text is optional; the numbers come from code
        log.info("planner LLM unavailable (%s) → code-written reasons", type(e).__name__)
        log_.add("Reasons and assembly notes are rule-written (LLM unavailable); processes come from the spec hints or a material heuristic.")

    steps = build_steps(spec, reasons, processes)
    if not notes:
        notes = ["Final assembly, functional test and burn-in at the main assembly supplier."]
        if has_cell(spec.bom):
            notes.append("Lithium cells ship by sea only (UN3481, packed with equipment) unless UN38.3 air documentation is in place.")
    pairs = [(s.process if isinstance(s.process, str) else s.process.value, int(s.lead_time_days.value)) for s in steps]
    t0, t1, golden, mass = plan.tooling_lead_days(pairs), plan.t1_days(pairs), plan.GOLDEN_SAMPLE_DAYS, plan.mass_days(qty)
    total = t0 + t1 + golden + mass
    log_.add(f"Lead times are typical values per process (tooling + first shots), not factory quotes; refined at stages 7-9 with the negotiated quote.", Label.estimate)
    log_.add(f"Mass production duration assumes {plan.UNITS_PER_DAY} units/day on one line for a {qty:,}-unit order.", Label.estimate)
    return ProductionPlanArtifact(
        project_id=ctx.project.id,
        generated_by=generated_by,
        assumptions=log_.items,
        steps=steps,
        assembly_notes=notes,
        total_lead_time_days=estimate(
            total, "days",
            f"Critical path from PO: slowest tooling/first article ({t0}) + tooling correction T1 ({t1}) + golden sample ({golden}) + mass production ({mass}) for {qty:,} units",
        ),
    )
