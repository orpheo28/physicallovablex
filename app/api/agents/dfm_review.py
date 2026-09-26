"""AI-reviewed DFM issues (stage 4 helper called by W2). Owner: W4.

    ai_review(spec, bom, measured) -> list[DFMIssue]      # method = ai_reviewed

The LLM reviews a checklist prompt; measured findings are given as facts and any LLM issue that contradicts
or duplicates one is dropped. Without a key (or on any LLM failure) a deterministic checklist runs instead,
so the function always returns something.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable

from contracts.artifacts import BOMItem, DFMIssue, DFMMethod, ProcessType, Severity, SpecArtifact, SpecPart
from pydantic import BaseModel, ConfigDict, Field

from api.agents._common import dump, render_prompt
from api.llm import complete_json

log = logging.getLogger("agents.dfm_review")

CATEGORY = str  # DFMIssue.category literal
_BATTERY_RE = re.compile(r"\b(18650|21700|li-?ion|li-?po|lipo|lithium|battery|cell)\b", re.I)
_PRIMARY_RE = re.compile(r"\b(cr20\d\d|coin cell|button cell|primary|non-?rechargeable)\b", re.I)
_ENCLOSURE_RE = re.compile(r"\b(shell|housing|case|cover|lid|base|enclosure|body|cap)\b", re.I)

# Typical injection-molding nominal wall ranges (mm) by resin family — Protolabs injection molding design guide.
WALL_RANGES_MM: list[tuple[re.Pattern[str], tuple[float, float], str]] = [
    (re.compile(r"pc\s*/\s*abs", re.I), (1.0, 3.6), "PC/ABS"),
    (re.compile(r"\babs\b", re.I), (1.1, 3.6), "ABS"),
    (re.compile(r"\b(pc|polycarbonate)\b", re.I), (1.0, 3.8), "PC"),
    (re.compile(r"\b(pp|polypropylene)\b", re.I), (0.9, 3.8), "PP"),
    (re.compile(r"\b(pa|nylon|pa6|pa66)\b", re.I), (0.8, 2.9), "nylon"),
    (re.compile(r"\b(pom|acetal)\b", re.I), (0.8, 3.0), "acetal/POM"),
    (re.compile(r"\b(tpu|tpe|silicone)\b", re.I), (0.5, 3.8), "TPE/TPU"),
]
WALL_SOURCE = "Protolabs injection molding design guide (typical nominal wall by resin)"


class _IssueDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    severity: Severity
    category: str
    part_id: str | None = None
    description: str
    fix: str
    rule_citation: str = ""


class _ReviewDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    issues: list[_IssueDraft] = Field(default_factory=list, max_length=12)


_CATEGORIES = {"draft", "undercut", "projection", "wall_thickness", "tolerance", "assembly", "material", "other"}
# Geometry checks owned by the measurement (api/dfm/measure.py): once the CAD has been measured, the AI never
# reports these categories — it cannot contradict (or re-guess) a measured fact.
GEOMETRY_CATEGORIES = {"draft", "undercut", "projection"}


def _process(part: SpecPart) -> str | None:
    return getattr(part.process_hint, "value", part.process_hint)


_NOT_BATTERY = re.compile(r"load[- ]?cells?|solar[- ]?cells?|peltier|cellular|cell phone", re.I)


def has_cell(bom: Iterable[BOMItem]) -> bool:
    """A battery/cell in the BOM (a load cell, solar cell or cellular modem is not one)."""
    return any(_BATTERY_RE.search(_NOT_BATTERY.sub(" ", f"{b.part} {b.description or ''}")) for b in bom)


def _cell_is_primary(bom: Iterable[BOMItem]) -> bool:
    return any(_PRIMARY_RE.search(f"{b.part} {b.description or ''}") for b in bom)


def _tolerance_mm(text: str | None) -> float | None:
    if not text:
        return None
    m = re.search(r"±\s*(\d+(?:\.\d+)?)\s*(mm|µm|um)?", text)
    if not m:
        return None
    val = float(m.group(1))
    return val / 1000 if m.group(2) in ("µm", "um") else val


def _battery_issue(bom: list[BOMItem], parts: list[SpecPart]) -> DFMIssue:
    enclosure = next((p for p in parts if _ENCLOSURE_RE.search(p.name)), parts[0] if parts else None)
    primary = _cell_is_primary(bom)
    std = "IEC 60086-4 (lithium primary batteries)" if primary else "IEC 62133-2 (secondary lithium cells)"
    return DFMIssue(
        id="",
        severity=Severity.critical,
        category="assembly",
        method=DFMMethod.ai_reviewed,
        part_id=enclosure.id if enclosure else None,
        description="A lithium cell is enclosed in the product: it needs a retention feature, clearance from heat sources and pinch-free assembly.",
        fix="Add a cell cradle with retention ribs and ≥2 mm clearance from the driver/charger area, keep the protection circuit on the cell path, and use a UL94 V-0 enclosure material.",
        rule_citation=f"{std} cell protection and thermal abuse clauses; UL 94 V-0 for battery enclosures",
    )


def checklist_review(spec: SpecArtifact, bom: list[BOMItem], measured: list[DFMIssue]) -> list[DFMIssue]:
    """Deterministic rule-of-thumb checklist (no LLM). Skips categories already covered by measured findings."""
    issues: list[DFMIssue] = []
    covered = {(m.part_id, m.category) for m in measured}

    def add(part: SpecPart | None, sev: Severity, cat: str, desc: str, fix: str, cite: str) -> None:
        if (part.id if part else None, cat) in covered or (measured and cat in GEOMETRY_CATEGORIES):
            return
        issues.append(
            DFMIssue(id="", severity=sev, category=cat, method=DFMMethod.ai_reviewed, part_id=part.id if part else None,  # type: ignore[arg-type]
                     description=desc, fix=fix, rule_citation=cite)
        )  # fmt: skip

    for part in spec.parts:
        proc = _process(part)
        wall = part.wall_thickness.value if part.wall_thickness else None
        if proc == ProcessType.injection_molding.value:
            rng = next((r for pat, r, name in WALL_RANGES_MM if pat.search(part.material)), None)
            name = next((n for pat, _, n in WALL_RANGES_MM if pat.search(part.material)), part.material)
            if wall is not None and rng and not (rng[0] <= wall <= rng[1]):
                add(part, Severity.major, "wall_thickness",
                    f"{part.name}: nominal wall {wall:g} mm is outside the typical {rng[0]:g}-{rng[1]:g} mm range for {name}.",
                    f"Move the nominal wall inside {rng[0]:g}-{rng[1]:g} mm and keep it uniform; core out thick sections.",
                    f"Typical wall range for {name} — {WALL_SOURCE}")  # fmt: skip
            elif wall is None:
                add(part, Severity.minor, "wall_thickness",
                    f"{part.name}: no nominal wall thickness is specified for an injection-molded part.",
                    "Specify a uniform nominal wall for the resin and avoid abrupt thick/thin transitions.",
                    f"Uniform wall thickness rule — {WALL_SOURCE}")  # fmt: skip
            add(part, Severity.minor, "wall_thickness",
                f"{part.name}: screw bosses and ribs can cause sink marks on cosmetic faces if too heavy.",
                "Keep boss wall ≤60% and rib thickness 50-60% of the nominal wall; add gussets instead of thickening.",
                "Boss wall ≤ 60% and rib thickness 50-60% of nominal wall — Protolabs injection molding design guide")  # fmt: skip
            if _ENCLOSURE_RE.search(part.name):
                add(part, Severity.major, "undercut",
                    f"{part.name}: snap-fits or side openings on an enclosure part usually create undercuts that need slides or lifters.",
                    "Use pass-through core openings under snap hooks, or move hooks to the parting line, to mold without side actions.",
                    "Snap-fit design and undercut avoidance — Protolabs injection molding design guide")  # fmt: skip
            tol = _tolerance_mm(part.tolerance)
            if tol is not None and tol < 0.1:
                add(part, Severity.major, "tolerance",
                    f"{part.name}: tolerance ±{tol:g} mm is tighter than typical injection-molding capability.",
                    "Relax to ±0.1 mm or better on non-critical faces, or plan a secondary machining step on the critical feature.",
                    "Commercial molding tolerance ≈ ±0.1 mm for small features — Protolabs / ISO 20457 guidance")  # fmt: skip
        elif proc == ProcessType.sheet_metal.value:
            add(part, Severity.minor, "material",
                f"{part.name}: bends and holes near edges can distort in sheet metal.",
                "Use an inside bend radius ≥ material thickness and keep holes ≥2× thickness from edges and bends.",
                "Sheet-metal DFM rules (bend radius ≥ thickness; hole-to-edge ≥ 2× thickness) — Protolabs sheet metal design guide")  # fmt: skip
        elif proc == ProcessType.die_casting.value:
            add(part, Severity.major, "draft",
                f"{part.name}: die-cast walls need draft and uniform thickness to avoid porosity.",
                "Add ≥1° draft on all walls, keep walls uniform (typ. 1.5-3 mm for zinc/aluminium), and round inner corners.",
                "Die casting design guidelines — NADCA product specification standards")  # fmt: skip
        if re.search(r"anodi[sz]", f"{part.finish} {part.material}", re.I):
            add(part, Severity.major, "tolerance",
                f"{part.name}: anodising adds coating build-up that can close tight fits and shift colour between lots.",
                "Toleranced dimensions apply after finishing; mask contact and threaded areas and approve colour against a golden sample.",
                "Type II anodising build-up (about half of the coating thickness grows outward) — MIL-A-8625")  # fmt: skip

    if len(spec.parts) >= 4:
        add(None, Severity.minor, "assembly",
            f"{len(spec.parts)} parts must be aligned and fastened: assembly time and error risk grow with part count and loose fasteners.",
            "Add locating features, use one screw size where possible and consider merging parts sharing a resin and process.",
            "DFA principles: minimise parts and fastener types — Boothroyd & Dewhurst")  # fmt: skip
    if has_cell(bom):
        issues.append(_battery_issue(bom, spec.parts))
    return issues


def _filter(drafts: list[_IssueDraft], spec: SpecArtifact, measured: list[DFMIssue]) -> list[DFMIssue]:
    """Drop LLM issues that are malformed, refer to unknown parts, or duplicate/contradict a measured finding."""
    part_ids = {p.id for p in spec.parts}
    measured_keys = {(m.part_id, m.category) for m in measured}
    measured_cats = {m.category for m in measured if m.part_id is None}
    out: list[DFMIssue] = []
    for d in drafts:
        cat = d.category if d.category in _CATEGORIES else "other"
        if d.part_id is not None and d.part_id not in part_ids:
            continue
        if not d.rule_citation.strip() or not d.description.strip() or not d.fix.strip():
            continue
        if (d.part_id, cat) in measured_keys or (d.part_id is None and cat in measured_cats):
            continue
        if measured and cat in GEOMETRY_CATEGORIES:
            continue
        out.append(
            DFMIssue(id="", severity=d.severity, category=cat, method=DFMMethod.ai_reviewed, part_id=d.part_id,  # type: ignore[arg-type]
                     description=d.description.strip(), fix=d.fix.strip(), rule_citation=d.rule_citation.strip())
        )  # fmt: skip
    return out


def _number(issues: list[DFMIssue]) -> list[DFMIssue]:
    for i, issue in enumerate(issues, 1):
        issue.id = f"ai{i}"
    return issues


def ai_review(spec: SpecArtifact, bom: list[BOMItem], measured: list[DFMIssue]) -> list[DFMIssue]:
    """AI-reviewed DFM issues for the spec. Never raises; falls back to the deterministic checklist."""
    measured = list(measured or [])
    bom = list(bom or spec.bom or [])
    issues: list[DFMIssue] = []
    try:
        prompt = render_prompt(
            "dfm_review",
            product=spec.product_name,
            parts=[
                {
                    "id": p.id, "name": p.name, "material": p.material, "finish": p.finish, "process": _process(p),
                    "tolerance": p.tolerance, "wall_mm": p.wall_thickness.value if p.wall_thickness else None,
                }
                for p in spec.parts
            ],  # fmt: skip
            tolerances=spec.tolerances,
            bom=[{"id": b.id, "part": b.part, "category": getattr(b.category, "value", b.category), "qty": b.qty} for b in bom],
            measured=[
                {"part_id": m.part_id, "category": m.category, "severity": getattr(m.severity, "value", m.severity),
                 "description": m.description, "measurement": dump(m.measurement) if m.measurement else None}
                for m in measured
            ],  # fmt: skip
        )
        draft = complete_json("main", prompt, _ReviewDraft, max_tokens=3000)
        issues = _filter(draft.issues, spec, measured)
        if issues and has_cell(bom) and not any(re.search(r"62133|60086|cell|batter", i.description + i.rule_citation, re.I) for i in issues):
            issues.append(_battery_issue(bom, spec.parts))
    except Exception as e:  # noqa: BLE001 — by contract this helper always returns something
        log.info("AI DFM review unavailable (%s: %s) → deterministic checklist", type(e).__name__, str(e)[:200])
        issues = []
    if not issues:
        issues = checklist_review(spec, bom, measured)
    if not issues:  # keep a non-empty answer even for trivial specs
        issues = [
            DFMIssue(id="", severity=Severity.minor, category="assembly", method=DFMMethod.ai_reviewed, part_id=None,
                     description="No product-specific risk found by the checklist; confirm assembly sequence and tolerances with the factory.",
                     fix="Ask the factory for a DFM report on the first article before tooling is released.",
                     rule_citation="Standard DFM sign-off before tool release — Protolabs / industry practice")  # fmt: skip
        ]
    return _number(issues)
