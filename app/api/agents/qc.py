"""Stage 10 — QC inspection plan. Owner: W4.

ISO 2859-1 (ANSI/ASQ Z1.4) General II, single sampling: sample size from the lot size (table in _planning.py),
AQL critical 0 / major 2.5 / minor 4.0. The LLM (route "fast") proposes defect classes; code validates that every
`spec_ref` resolves to an existing spec part id / BOM id / electronics block / tolerance / certification (or DFM
issue id) and drops or trims the ones that do not. If the LLM is unavailable a deterministic list derived from
the spec is used (generated_by = "code"). Man-day rate: $268 V-Trust (Sourced).
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, Literal

from contracts.artifacts import Certification, DefectClass, Label, QCArtifact, Severity, SpecArtifact
from pydantic import BaseModel, ConfigDict, Field

from api.agents import _planning as plan
from api.agents._common import AssumptionLog, estimate, llm_tag, lv, render_prompt
from api.agents.dfm_review import _NOT_BATTERY, has_cell
from api.llm import complete_json
from api.stages.registry import StageContext, stage_handler

log = logging.getLogger("agents.qc")

AQL = {"critical": 0.0, "major": 2.5, "minor": 4.0}
MAN_DAY_RATE_USD = 268.0
_ID_TOKEN = re.compile(r"\b[a-z]{1,2}\d{1,3}\b")
MAX_DEFECTS = 12


class _DefectDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    severity: Literal["critical", "major", "minor"]
    description: str
    spec_ref: str
    check_method: str = "Visual + functional check"


class _QCDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    defects: list[_DefectDraft] = Field(default_factory=list, max_length=16)


# --------------------------------------------------------------------------- spec-line resolution


def known_ids(spec: SpecArtifact, dfm_ids: Iterable[str] = ()) -> set[str]:
    ids = {p.id.lower() for p in spec.parts} | {b.id.lower() for b in spec.bom} | {b.id.lower() for b in spec.electronics_blocks}
    return ids | {i.lower() for i in dfm_ids}


def _tolerance_texts(spec: SpecArtifact) -> list[str]:
    return [t for t in [*spec.tolerances, *(p.tolerance for p in spec.parts if p.tolerance)] if t]


def _cert_variants(standard: str) -> set[str]:
    low = standard.lower()
    return {v.strip() for v in (low, low.split(" (")[0], low.split(" — ")[0], low.split(" - ")[0]) if len(v.strip()) >= 4}


def _segment_resolves(seg: str, ids: set[str], tolerances: list[str], cert_standards: list[str]) -> bool:
    low = re.sub(r"^(certification|tolerance|part|bom|electronics block|packaging|dfm)\s*:?\s+", "", seg.strip().lower())
    if not low:
        return False
    if any(t in ids for t in _ID_TOKEN.findall(seg.lower())):
        return True
    for tol in tolerances:
        t = tol.lower()
        if len(low) >= 6 and (low in t or t in low):
            return True
    for std in cert_standards:
        for v in _cert_variants(std):
            if len(low) >= 4 and (v in low or low in v):
                return True
    return False


def resolve_spec_ref(ref: str, spec: SpecArtifact, cert_standards: list[str], dfm_ids: Iterable[str] = ()) -> str | None:
    """Keep only the ' / '-separated segments of `ref` that point to an existing spec line; None if none does."""
    ids, tols = known_ids(spec, dfm_ids), _tolerance_texts(spec)
    kept = [s.strip() for s in re.split(r"\s+/\s+|;", ref) if s.strip() and _segment_resolves(s, ids, tols, cert_standards)]
    return " / ".join(kept) if kept else None


def valid_ref_strings(spec: SpecArtifact, cert_standards: list[str]) -> list[str]:
    refs = [f"Part {p.id} ({p.name})" for p in spec.parts]
    refs += [f"BOM {b.id} ({b.part})" for b in spec.bom]
    refs += [f"Electronics block {b.id} ({b.name})" for b in spec.electronics_blocks]
    refs += [f"Tolerance: {t}" for t in _tolerance_texts(spec)]
    refs += [f"Certification: {s.split(' (')[0]}" for s in cert_standards]
    return refs


# --------------------------------------------------------------------------- deterministic defects

_CHARGER = re.compile(r"\b(charger|charging|tp4056|usb-?c)\b", re.I)
_CELL = re.compile(r"\b(18650|21700|li-?ion|li-?po|lipo|lithium|battery|cell|cr20\d\d)\b", re.I)


def _cert_ref(standards: list[str], *needles: str) -> str | None:
    for n in needles:  # needles are in priority order
        for s in standards:
            if n.lower() in s.lower():
                return f"Certification: {s.split(' (')[0]}"
    return None


def default_defects(spec: SpecArtifact, cert_standards: list[str]) -> list[tuple[str, str, str, str]]:
    """(severity, description, spec_ref, check_method) derived from the spec. Every ref is built from existing lines."""
    out: list[tuple[str, str, str, str]] = []
    cells = [b for b in spec.bom if _CELL.search(_NOT_BATTERY.sub(" ", f"{b.part} {b.description or ''}"))
             and not re.search(r"holder|connector|charger", b.part, re.I)]
    charger = next((b for b in spec.bom if _CHARGER.search(b.part) and getattr(b.category, "value", b.category) == "electronic"), None)
    battery_cert = _cert_ref(cert_standards, "62133", "60086", "UN38.3")
    if cells or has_cell(spec.bom):
        cell = cells[0] if cells else None
        ref = " / ".join(x for x in (f"BOM {cell.id}" if cell else None, battery_cert) if x)
        if ref:
            out.append(("critical", "Cell swelling, exposed cell, damaged wiring or missing/defeated protection circuit",
                        ref, "Visual + open-circuit voltage and over-discharge test on 5 units"))  # fmt: skip
    if charger and cells:
        out.append(("critical", "Charging voltage above the cell limit or port/cell overheating during charge",
                    f"BOM {charger.id}", "Charge test with USB meter and IR thermometer, 30 min"))  # fmt: skip
    mains = _cert_ref(cert_standards, "LVD", "62368", "UL")
    if mains and not cells:
        out.append(("critical", "Insulation/hi-pot failure or exposed live parts", mains, "Hi-pot test on 100% of samples, visual for exposed conductors"))
    if not any(s == "critical" for s, *_ in out) and spec.parts:
        p = spec.parts[0]
        out.append(("critical", f"Cracked or sharp-edged {p.name.lower()} that can injure the user", f"Part {p.id}", "Visual + finger-feel check on every sample"))

    tols = list(spec.tolerances) or [p.tolerance for p in spec.parts if p.tolerance]
    for t in tols[:3]:
        out.append(("major", f"Dimension out of tolerance: {t}", f"Tolerance: {t}", "Go/no-go gauge or caliper on the sample"))
    elec = [b for b in spec.bom if getattr(b.category, "value", b.category) == "electronic"]
    if elec:
        refs = " / ".join(f"BOM {b.id}" for b in elec[:2])
        out.append(("major", "Dead unit, LED flicker, unresponsive button or missing radio function", refs, "Power-on functional test in every mode"))
    for p in spec.parts:
        if re.search(r"anodi|paint|plated|coat|texture|powder", f"{p.finish}", re.I) and len([o for o in out if "colour" in o[1]]) < 2:
            out.append(("major", f"Finish colour or gloss of {p.name.lower()} differs from the golden sample (ΔE > 1.5)",
                        f"Part {p.id}", "Colorimeter or visual comparison against the approved golden sample"))  # fmt: skip
    radio = _cert_ref(cert_standards, "FCC Part 15C", "RED", "RSS-247", "Bluetooth")
    if radio:
        out.append(("major", "Firmware or radio configuration differs from the certified version", radio, "Check firmware version string and TX test mode on 5 units"))

    cosmetic = [p for p in spec.parts if getattr(p.process_hint, "value", p.process_hint) in ("injection_molding", "die_casting", "cnc")][:2]
    for p in cosmetic:
        out.append(("minor", f"Sink marks, flow lines, flash or scratches on {p.name.lower()}", f"Part {p.id}", "Visual at 50 cm under D65 light"))
    pack = next((b for b in spec.bom if getattr(b.category, "value", b.category) == "packaging"), None)
    if pack:
        out.append(("minor", "Box print misregistration, crushed corners or missing accessories", f"BOM {pack.id}", "Visual + contents checklist"))
    label_ref = _cert_ref(cert_standards, "FCC", "CE", "UKCA", "CPSIA", "FDA")
    if label_ref:
        out.append(("minor", "Missing or wrong regulatory marking/label (FCC ID, CE/UKCA, warnings)", label_ref, "Compare label against the artwork approved at golden sample"))
    return out


def _to_defects(rows: list[tuple[str, str, str, str]], n: int) -> list[DefectClass]:
    counters = {"critical": 0, "major": 0, "minor": 0}
    prefix = {"critical": "c", "major": "j", "minor": "n"}
    defects = []
    for sev, desc, ref, method in rows[:MAX_DEFECTS]:
        counters[sev] += 1
        aql = AQL[sev]
        ar = plan.accept_reject(aql, n)
        how = f"{method.rstrip('.')} — AQL {aql:g}: accept ≤{ar[0]} / reject ≥{ar[1]} at n={n}" if ar else method
        defects.append(DefectClass(id=f"{prefix[sev]}{counters[sev]}", severity=Severity(sev), description=desc, spec_ref=ref, check_method=how, aql=aql))
    return defects


def _cert_standards(ctx: StageContext, spec: SpecArtifact) -> list[str]:
    dfm, brief = ctx.artifact(4), ctx.artifact(1)
    certs: list[Certification] = list(getattr(dfm, "certifications", []) or [])
    if not certs and brief is not None:
        from api.agents.certification import certification_map

        certs = certification_map(brief, spec)
    return [c.standard for c in certs]


@stage_handler(10)
def run_qc(ctx: StageContext) -> QCArtifact:
    spec, brief, costs, neg = ctx.artifact(3), ctx.artifact(1), ctx.artifact(5), ctx.artifact(8)
    if spec is None:
        raise ValueError("stage 10 needs the stage 3 spec")
    log_ = AssumptionLog(10)
    ft = getattr(neg, "final_terms", None)
    lot = int(ft.quantity) if ft is not None else int(getattr(costs, "reference_quantity", 0) or 0)
    if not lot:
        vols = getattr(brief, "target_volumes", None) or []
        lot = int(vols[len(vols) // 2]) if vols else plan.DEFAULT_LOT
    letter, n = plan.sample_size(lot)
    stds = _cert_standards(ctx, spec)
    dfm_ids = [i.id for i in getattr(ctx.artifact(4), "issues", [])]

    rows: list[tuple[str, str, str, str]] = []
    generated_by = "code"
    try:
        prompt = render_prompt(
            "qc",
            product=spec.product_name,
            lot=str(lot),
            refs=valid_ref_strings(spec, stds),
            parts=[{"id": p.id, "name": p.name, "material": p.material, "finish": p.finish, "tolerance": p.tolerance} for p in spec.parts],
            tolerances=spec.tolerances,
            bom=[{"id": b.id, "part": b.part} for b in spec.bom][:30],
        )
        draft = complete_json("fast", prompt, _QCDraft, max_tokens=2500)
        for d in draft.defects:
            ref = resolve_spec_ref(d.spec_ref, spec, stds, dfm_ids)
            if ref and d.description.strip():
                rows.append((d.severity, d.description.strip(), ref, d.check_method.strip() or "Visual + functional check"))
        if rows:
            generated_by = llm_tag("fast")
    except Exception as e:  # noqa: BLE001 — code-derived list is a valid plan
        log.info("QC LLM unavailable (%s) → code-derived defect list", type(e).__name__)
    seen = {(s, r) for s, _, r, _ in rows}
    base = default_defects(spec, stds)
    if not any(s == "critical" for s, *_ in rows) or len(rows) < 5:
        for row in base:
            if (row[0], row[2]) not in seen and (len(rows) < 5 or (row[0] == "critical" and not any(s == "critical" for s, *_ in rows))):
                rows.append(row)
                seen.add((row[0], row[2]))
    order = {"critical": 0, "major": 1, "minor": 2}
    rows.sort(key=lambda r: order[r[0]])
    if generated_by == "code":
        rows = base or rows
        rows.sort(key=lambda r: order[r[0]])
    defects = _to_defects(rows, n)
    if not defects:
        raise ValueError("no defect class could be tied to a spec line")

    days = plan.inspection_man_days(n)
    log_.add(f"Pre-shipment inspection priced at ${MAN_DAY_RATE_USD:g} per man-day.", Label.sourced, "V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26")
    log_.add("AQL 0 / 2.5 / 4.0 for critical / major / minor is the usual consumer-goods setting; agree it with the buyer and factory.")
    log_.add(f"One inspector checks about {plan.PSI_UNITS_PER_MAN_DAY} units per day including functional tests.")
    if generated_by == "code":
        log_.add("Defect classes are derived by rule from the spec (LLM unavailable); every one points to an existing spec line.")
    return QCArtifact(
        project_id=ctx.project.id,
        generated_by=generated_by,
        assumptions=log_.items,
        lot_size=lot,
        sample_size=lv(n, "units", Label.estimate,
                       f"Per ISO 2859-1 table (edition not verified): Table I code letter {letter} for lot {plan.lot_range_text(lot)}, level General II, Table II-A"),  # fmt: skip
        defects=defects,
        inspection_man_days=estimate(days, "man-days", f"{n} samples at {plan.PSI_UNITS_PER_MAN_DAY} units per man-day incl. functional tests"),
        man_day_rate=lv(MAN_DAY_RATE_USD, "USD", Label.sourced, "V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26"),
        inspection_cost=lv(days * MAN_DAY_RATE_USD, "USD", Label.estimate, f"V-Trust rate (Sourced) × estimated man-days: {days} man-days (estimate) × ${MAN_DAY_RATE_USD:g}/man-day (V-Trust, https://www.v-trust.com/en/our-network, checked 2026-09-26)"),
    )
