"""PhysicalLovableX contracts — the single source of truth for every artifact.

Owner: W0 (frozen for Wave 1). Changes go through the Monitor as a CONTRACT CHANGE REQUEST.

Honesty rules (PRD §15):
- Every number shown to a user in a *stage artifact* is a `LabeledValue` (value, unit, label, source_or_assumption).
- Records of the simulated network (Factory, CapacityProfile, RFQ, Quote, NegotiationTurn) carry a
  record-level `label` that is always `fictional`; every number inside them inherits it. The UI must show
  the "Fictional — demo data" badge on the whole record.
- Plain numbers elsewhere (quantities, ids, versions, parameters fed to CAD) are inputs, not claims.

Stage map (PRD §8): 1 brief · 2 design · 3 cad_spec · 4 dfm · 5 costs · 6 production_plan · 7 matching ·
8 negotiation · 9 tooling · 10 qc · 11 logistics · 12 financing · 13 brand. The Factory Pack (PRD §8.1)
is assembled after stage 6 and consumed by stages 7-8 and the Launch Dossier export.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True, json_schema_serialization_defaults_required=True)


# ---------------------------------------------------------------------------
# Honesty primitives
# ---------------------------------------------------------------------------


class Label(str, Enum):
    """The four honesty labels. UI text: Measured / Sourced / Estimate / Fictional — demo data."""

    measured = "measured"  # computed on the CAD (build123d / OCCT)
    sourced = "sourced"  # real price or official rate, with date + source
    estimate = "estimate"  # assumption shown
    fictional = "fictional"  # simulated network: factories, quotes, freight


class LabeledValue(Model):
    value: float
    unit: str = Field(description="e.g. USD, EUR, mm, g, days, weeks, pct, units, man-days")
    label: Label
    source_or_assumption: str = Field(
        description="Sourced: '<source>, <YYYY-MM-DD>'. Estimate: the assumption. Measured: the check. Fictional: 'demo data'."
    )


class Assumption(Model):
    id: str
    text: str
    label: Label
    source: str | None = None
    stage: int | None = Field(default=None, description="Stage that introduced the assumption")


class Dimensions(Model):
    length: LabeledValue
    width: LabeledValue
    height: LabeledValue


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectMode(str, Enum):
    idea = "idea"
    prototype = "prototype"


class StageStatus(str, Enum):
    not_started = "not_started"
    draft = "draft"
    validated = "validated"


class ProjectStatus(str, Enum):
    active = "active"
    archived = "archived"


STAGE_NAMES: dict[int, str] = {
    1: "brief",
    2: "design",
    3: "cad_spec",
    4: "dfm",
    5: "costs",
    6: "production_plan",
    7: "matching",
    8: "negotiation",
    9: "tooling",
    10: "qc",
    11: "logistics",
    12: "financing",
    13: "brand",
}

STAGE_TITLES: dict[int, str] = {
    1: "Brief",
    2: "Industrial design",
    3: "CAD + spec",
    4: "DFM",
    5: "Investment",
    6: "Production plan",
    7: "Factory matching",
    8: "RFQ + negotiation",
    9: "Tooling + samples",
    10: "QC",
    11: "Logistics",
    12: "Financing",
    13: "Brand + distribution",
}


class Project(Model):
    id: str
    name: str
    mode: ProjectMode
    prompt: str
    pasted_bom: str | None = None
    example: str | None = Field(
        default=None, description="Fixture set used for fallbacks, e.g. 'desk_lamp', 'tracker_card'"
    )
    status: ProjectStatus = ProjectStatus.active
    created_at: datetime = Field(default_factory=utcnow)
    stage_status: dict[str, StageStatus] = Field(
        default_factory=dict, description="Keys are stage numbers as strings ('1'..'13')"
    )


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    critical = "critical"
    major = "major"
    minor = "minor"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class BOMCategory(str, Enum):
    electronic = "electronic"
    mechanical = "mechanical"
    packaging = "packaging"


class ComponentRisk(Model):
    level: RiskLevel
    reasons: list[str] = Field(default_factory=list, description="e.g. EOL, single source, long lead time, low stock")


class BOMItem(Model):
    id: str
    part: str
    category: BOMCategory
    qty: float = Field(description="Quantity per finished unit")
    description: str | None = None
    manufacturer_pn: str | None = None
    lcsc_pn: str | None = Field(default=None, description="e.g. 'C725790' when matched to the LCSC snapshot")
    unit_cost_est: LabeledValue | None = None
    risk: ComponentRisk | None = None
    alternative: str | None = None


class CadFile(Model):
    format: Literal["step", "stl", "glb", "pdf", "png", "svg"]
    url: str = Field(description="Served by the API, e.g. /files/<project_id>/enclosure.step")
    description: str | None = None
    size_bytes: int | None = None


class Certification(Model):
    market: str = Field(description="US, EU, UK, ...")
    standard: str = Field(description="e.g. FCC Part 15B, CE (LVD/EMC/RED), UKCA, UN38.3")
    applies_because: str
    required: bool = True
    cost_est: LabeledValue
    lead_time_weeks: LabeledValue


class ProcessType(str, Enum):
    injection_molding = "injection_molding"
    cnc = "cnc"
    sheet_metal = "sheet_metal"
    die_casting = "die_casting"
    extrusion = "extrusion"
    pcba = "pcba"
    assembly = "assembly"
    other = "other"


class ArtifactBase(Model):
    project_id: str
    status: StageStatus = StageStatus.draft
    fallback: bool = Field(default=False, description="True when served from a fixture after an error")
    fallback_reason: str | None = None
    generated_by: str = Field(default="fixture", description="'fixture' | 'code' | 'llm:<model slug>'")
    generated_at: datetime = Field(default_factory=utcnow)
    assumptions: list[Assumption] = Field(default_factory=list)


CACHED_NOTE = "Cached example — AI was unavailable, figures come from a pre-computed example"

PROCESS_LABELS: dict[str, str] = {  # human wording of ProcessType for PDFs, reasons and UI
    "injection_molding": "Injection molding", "cnc": "CNC machining", "sheet_metal": "Sheet metal",
    "die_casting": "Die casting", "extrusion": "Extrusion", "pcba": "PCBA", "assembly": "Assembly", "other": "Other",
}


def process_label(p: object) -> str:
    v = str(getattr(p, "value", p))
    return PROCESS_LABELS.get(v, v.replace("_", " ").capitalize())


# ---------------------------------------------------------------------------
# Stage 1 — Brief
# ---------------------------------------------------------------------------


class ClarifyingQuestion(Model):
    id: str
    topic: Literal["markets", "volume", "target_price", "battery", "wireless", "other"]
    question: str
    options: list[str] = Field(default_factory=list)
    answer: str | None = None
    skipped: bool = False


class BriefArtifact(ArtifactBase):
    stage: Literal[1] = 1
    mode: ProjectMode
    prompt: str
    product_name: str
    one_liner: str
    category: str
    target_markets: list[str]
    target_retail_price: LabeledValue
    target_volumes: list[int] = Field(description="Volume tiers, default [500, 2000, 10000]")
    key_features: list[str]
    constraints: list[str] = Field(default_factory=list)
    has_battery: bool
    wireless: list[str] = Field(default_factory=list, description="e.g. BLE, Wi-Fi, NFC; empty if none")
    pasted_bom: list[BOMItem] = Field(default_factory=list, description="Prototype mode only")
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list, max_length=5)


# ---------------------------------------------------------------------------
# Stage 2 — Industrial design
# ---------------------------------------------------------------------------


class DesignDirection(Model):
    id: str
    name: str
    description: str
    shape: str
    material: str
    finish: str
    dimensions: Dimensions
    cad_parameters: dict[str, float] = Field(
        default_factory=dict, description="Parametric inputs for the build123d generator (mm)"
    )
    render_url: str | None = None
    glb_url: str | None = None


class DesignArtifact(ArtifactBase):
    stage: Literal[2] = 2
    directions: list[DesignDirection] = Field(min_length=3, max_length=3)
    chosen_direction_id: str | None = None


# ---------------------------------------------------------------------------
# Stage 3 — CAD + spec
# ---------------------------------------------------------------------------


class SpecPart(Model):
    id: str
    name: str
    material: str
    finish: str
    process_hint: ProcessType | None = None
    tolerance: str | None = Field(default=None, description="e.g. '±0.1 mm on mating faces'")
    dimensions: Dimensions | None = None
    wall_thickness: LabeledValue | None = None
    quantity: int = 1


class ElectronicsBlock(Model):
    id: str
    name: str
    function: str


class ElectronicsEdge(Model):
    source: str
    target: str
    signal: str


class SpecArtifact(ArtifactBase):
    stage: Literal[3] = 3
    product_name: str
    direction_id: str
    overall_dimensions: Dimensions
    weight: LabeledValue
    parts: list[SpecPart]
    electronics_blocks: list[ElectronicsBlock] = Field(default_factory=list)
    electronics_edges: list[ElectronicsEdge] = Field(default_factory=list)
    bom: list[BOMItem]
    tolerances: list[str] = Field(default_factory=list)
    cad_files: list[CadFile] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 4 — DFM
# ---------------------------------------------------------------------------


class DFMMethod(str, Enum):
    measured = "measured"  # geometry check on the CAD
    ai_reviewed = "ai_reviewed"  # LLM review with checklist prompt


class DFMIssue(Model):
    id: str
    severity: Severity
    category: Literal["draft", "undercut", "projection", "wall_thickness", "tolerance", "assembly", "material", "other"]
    method: DFMMethod
    part_id: str | None = None
    description: str
    fix: str
    rule_citation: str = Field(description="The rule the finding is based on, with its source")
    measurement: LabeledValue | None = Field(default=None, description="Required when method == measured")
    resolved: bool = False
    resolution: str | None = None


class ComponentRiskItem(Model):
    bom_item_id: str
    part: str
    level: RiskLevel
    reasons: list[str]
    alternatives: list[str] = Field(default_factory=list)
    stock: LabeledValue | None = None
    lead_time_weeks: LabeledValue | None = None


class DFMArtifact(ArtifactBase):
    stage: Literal[4] = 4
    issues: list[DFMIssue]
    component_risks: list[ComponentRiskItem] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 5 — Investment (costs)
# ---------------------------------------------------------------------------


class CostLine(Model):
    bom_item_id: str
    part: str
    qty_per_unit: float
    unit_price: LabeledValue = Field(description="Sourced: 'LCSC price, <date>'; else Estimate + assumption")
    lcsc_pn: str | None = None
    stock: LabeledValue | None = None
    extended: LabeledValue = Field(description="qty_per_unit × unit_price")


class CostTier(Model):
    quantity: int
    bom_cost: LabeledValue
    assembly_cost: LabeledValue
    packaging_cost: LabeledValue
    unit_cost: LabeledValue = Field(description="Ex-works unit cost (FOB basis) at this tier")
    tooling_amortisation: LabeledValue
    margin_pct: LabeledValue = Field(description="Margin at target retail price, landed-cost estimate basis")


class ToolingItem(Model):
    name: str
    process: ProcessType
    cost: LabeledValue


class CostsArtifact(ArtifactBase):
    stage: Literal[5] = 5
    currency: str = "USD"
    bom_lines: list[CostLine]
    volume_factor: LabeledValue = Field(description="Editable unit-cost decay per tier step")
    tiers: list[CostTier] = Field(min_length=3, description="500 / 2,000 / 10,000 by default")
    tooling: list[ToolingItem]
    tooling_total: LabeledValue
    certification_total: LabeledValue
    reference_quantity: int = Field(description="Tier used for the cash-needed figure (first order)")
    total_cash_needed: LabeledValue = Field(
        description="Tooling + certification + first order (reference_quantity × landed estimate) + samples/QC"
    )
    cash_breakdown: list[LandedCostComponent] = Field(description="Components summing to total_cash_needed")
    target_retail_price: LabeledValue
    breakeven_units: LabeledValue


# ---------------------------------------------------------------------------
# Stage 6 — Production plan
# ---------------------------------------------------------------------------


class ProcessStep(Model):
    part_id: str
    part_name: str
    process: ProcessType
    reason: str
    region: str = Field(description="e.g. 'Shenzhen, Guangdong'")
    lead_time_days: LabeledValue


class ProductionPlanArtifact(ArtifactBase):
    stage: Literal[6] = 6
    steps: list[ProcessStep]
    assembly_notes: list[str] = Field(default_factory=list)
    total_lead_time_days: LabeledValue


# ---------------------------------------------------------------------------
# Simulated network (MCP) — record-level label, always fictional
# ---------------------------------------------------------------------------


class CapacityProfile(Model):
    """Mirrors MCP `register_capacity` input (PRD §10)."""

    processes: list[ProcessType]
    materials: list[str]
    moq: int
    certifications: list[str] = Field(description="Factory certifications, e.g. ISO 9001, BSCI")
    lead_time_days: int
    monthly_capacity: int = Field(description="Units per month")
    current_load_pct: float
    label: Literal["fictional"] = "fictional"


class PastPerformance(Model):
    orders_completed: int
    on_time_rate_pct: float | None = Field(description="None = no data yet (self-registered factory, no order on the network)")
    defect_rate_pct: float | None = Field(description="None = no data yet")
    no_data: bool = Field(default=False, description="True for a factory with no completed order on the network: show 'no data yet'")
    label: Literal["fictional"] = "fictional"


class Factory(Model):
    id: str
    name: str = Field(description="Fictional name — never a real factory")
    region: str
    archetype: str = Field(description="e.g. 'cheap/slow', 'fast/expensive', 'balanced' (E_usines.md)")
    personality: str | None = Field(default=None, description="Behaviour of its negotiation agent")
    capacity: CapacityProfile
    audit_notes: list[str] = Field(default_factory=list)
    past_performance: PastPerformance
    label: Literal["fictional"] = "fictional"
    fictional: Literal[True] = True


class RFQStatus(str, Enum):
    sent = "sent"
    quoted = "quoted"
    declined = "declined"
    accepted = "accepted"


class RFQ(Model):
    id: str
    project_id: str
    factory_id: str
    factory_pack_id: str
    quantities: list[int]
    status: RFQStatus = RFQStatus.sent
    created_at: datetime = Field(default_factory=utcnow)
    label: Literal["fictional"] = "fictional"


class QuoteTier(Model):
    quantity: int
    unit_price_usd: float


class QuoteStatus(str, Enum):
    submitted = "submitted"
    countered = "countered"
    superseded = "superseded"
    accepted = "accepted"
    rejected = "rejected"


class Quote(Model):
    """Mirrors MCP `submit_quote` (PRD §10). Each counter creates a new version."""

    id: str
    rfq_id: str
    factory_id: str
    version: int = 1
    tiers: list[QuoteTier]
    tooling_usd: float
    moq: int
    lead_time_days: int
    payment_terms: str = Field(description="e.g. '30% deposit / 70% before shipment'")
    exceptions: list[str] = Field(default_factory=list)
    status: QuoteStatus = QuoteStatus.submitted
    created_at: datetime = Field(default_factory=utcnow)
    label: Literal["fictional"] = "fictional"


class Speaker(str, Enum):
    platform_agent = "platform_agent"
    factory_agent = "factory_agent"
    user = "user"


class NegotiationTurn(Model):
    id: str
    rfq_id: str
    factory_id: str
    turn: int
    speaker: Speaker
    message: str
    message_cn: str | None = Field(default=None, description="Machine-translated, to be reviewed by a native speaker")
    quote_id: str | None = None
    proposed_changes: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    label: Literal["fictional"] = "fictional"


class RFQWithQuotes(Model):
    """Factory-portal view of one RFQ."""

    rfq: RFQ
    product_name: str
    quotes: list[Quote] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 7 — Factory matching
# ---------------------------------------------------------------------------


class SearchCapacityQuery(Model):
    """Mirrors MCP `search_capacity` input."""

    process: ProcessType
    material: str
    quantity: int
    certifications_required: list[str] = Field(default_factory=list)
    deadline: date | None = None


class ScoreComponent(Model):
    criterion: Literal["process_fit", "moq", "certifications", "load", "lead_time"]
    score: float = Field(ge=0, le=1)
    weight: float
    note: str


class FactoryMatch(Model):
    rank: int
    factory_id: str
    factory_name: str
    score: LabeledValue = Field(description="0-100, label fictional (scored on demo data)")
    score_breakdown: list[ScoreComponent]
    reasons: list[str]


class MatchingArtifact(ArtifactBase):
    stage: Literal[7] = 7
    factory_pack_id: str
    queries: list[SearchCapacityQuery]
    shortlist: list[FactoryMatch] = Field(min_length=3)


# ---------------------------------------------------------------------------
# Stage 8 — RFQ + negotiation
# ---------------------------------------------------------------------------


class Recommendation(Model):
    factory_id: str
    quote_id: str
    rationale: str


class FinalTerms(Model):
    factory_id: str
    quote_id: str
    quantity: int
    unit_price: LabeledValue
    tooling: LabeledValue
    moq: int
    lead_time_days: LabeledValue
    payment_terms: str


class NegotiationArtifact(ArtifactBase):
    stage: Literal[8] = 8
    rfqs: list[RFQ]
    quotes: list[Quote]
    transcript: list[NegotiationTurn]
    recommendation: Recommendation
    user_approved: bool = False
    final_terms: FinalTerms | None = Field(default=None, description="Set once the user approves")


# ---------------------------------------------------------------------------
# Stage 9 — Tooling + samples
# ---------------------------------------------------------------------------


class MilestoneKind(str, Enum):
    deposit = "deposit"
    tooling_t0 = "tooling_t0"
    tooling_t1 = "tooling_t1"
    golden_sample = "golden_sample"
    certification = "certification"
    mass_production = "mass_production"
    pre_shipment_inspection = "pre_shipment_inspection"
    shipment = "shipment"
    delivered = "delivered"
    other = "other"


class Milestone(Model):
    id: str
    name: str
    kind: MilestoneKind
    start_date: date
    end_date: date
    duration_days: LabeledValue
    depends_on: list[str] = Field(default_factory=list)
    payment: LabeledValue | None = Field(default=None, description="Cash out at this milestone, if any")
    notes: str | None = None


class PaymentScheduleItem(Model):
    milestone_id: str
    description: str
    pct_of_order: float | None = None
    amount: LabeledValue
    due_date: date


class ToolingArtifact(ArtifactBase):
    stage: Literal[9] = 9
    milestones: list[Milestone]
    payment_schedule: list[PaymentScheduleItem]


# ---------------------------------------------------------------------------
# Stage 10 — QC
# ---------------------------------------------------------------------------


class DefectClass(Model):
    id: str
    severity: Severity
    description: str
    spec_ref: str = Field(description="Spec line (part id / tolerance / certification) the defect maps to")
    check_method: str
    aql: float = Field(description="Acceptable quality limit for this class, e.g. 0, 2.5, 4.0")


class QCArtifact(ArtifactBase):
    stage: Literal[10] = 10
    standard: str = Field(default="ISO 2859-1 (ANSI/ASQ Z1.4)")
    inspection_level: str = "General II"
    lot_size: int
    sample_size: LabeledValue
    defects: list[DefectClass]
    inspection_man_days: LabeledValue
    man_day_rate: LabeledValue
    inspection_cost: LabeledValue


# ---------------------------------------------------------------------------
# Stage 11 — Logistics + landed cost
# ---------------------------------------------------------------------------


class FreightOption(Model):
    mode: Literal["sea_lcl", "sea_fcl", "air", "express"]
    transit_days: LabeledValue
    cost_per_unit: LabeledValue


class HTSLine(Model):
    code: str = Field(description="e.g. '9405.21.xx'")
    description: str
    general_rate: LabeledValue
    section_301_rate: LabeledValue
    source_url: str


class LandedCostComponent(Model):
    name: str
    amount: LabeledValue


class LogisticsArtifact(ArtifactBase):
    stage: Literal[11] = 11
    incoterm: Literal["EXW", "FOB", "CIF", "DDP"] = "FOB"
    destination: str
    quantity: int
    freight_options: list[FreightOption]
    chosen_mode: Literal["sea_lcl", "sea_fcl", "air", "express"]
    hts: HTSLine
    section_122_applied: bool = False
    landed_cost_breakdown: list[LandedCostComponent] = Field(description="Per-unit components (PRD §11)")
    landed_cost_per_unit: LabeledValue
    reconciles_with_stage5: bool
    reconciliation_note: str


# ---------------------------------------------------------------------------
# Stage 12 — Financing
# ---------------------------------------------------------------------------


class CashPoint(Model):
    date: date
    milestone_id: str
    description: str
    cash_out: LabeledValue
    cumulative: LabeledValue


class FinancingOption(Model):
    kind: Literal["preorders", "crowdfunding", "inventory_financing", "revenue_based", "equity", "other"]
    name: str
    description: str
    cost: LabeledValue | None = None
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)


class FinancingArtifact(ArtifactBase):
    stage: Literal[12] = 12
    cash_curve: list[CashPoint]
    total_cash: LabeledValue
    matches_stage5_total: bool
    options: list[FinancingOption]
    stage5_total: LabeledValue | None = Field(default=None, description="Stage 5 budget reference (total cash needed)")
    reconciliation_note: str | None = Field(
        default=None, description="Why the curve differs from stage 5 (e.g. the approved quote replaced the estimate); None if equal")


# ---------------------------------------------------------------------------
# Stage 13 — Brand + distribution
# ---------------------------------------------------------------------------


class NameOption(Model):
    name: str
    rationale: str


class PackagingSpec(Model):
    box_type: str
    dimensions: Dimensions
    materials: list[str]
    printing: str
    contents: list[str]
    unit_cost: LabeledValue


class LandingCopy(Model):
    headline: str
    subheadline: str
    bullets: list[str]
    cta: str


class ListingDraft(Model):
    channel: Literal["shopify", "amazon"]
    title: str
    description: str
    bullets: list[str]
    price: LabeledValue
    keywords: list[str] = Field(default_factory=list)


class BrandArtifact(ArtifactBase):
    stage: Literal[13] = 13
    name_options: list[NameOption] = Field(min_length=1)
    chosen_name: str | None = None
    packaging: PackagingSpec
    landing_copy: LandingCopy
    shopify_listing: ListingDraft
    amazon_listing: ListingDraft


# ---------------------------------------------------------------------------
# Factory Pack (PRD §8.1) — the primitive
# ---------------------------------------------------------------------------


class FactoryQuestion(Model):
    id: str
    en: str
    cn: str | None = None
    cn_review_note: str = "Machine-translated — to be reviewed by a native speaker"


class StructuredSpec(Model):
    overall_dimensions: Dimensions
    weight: LabeledValue
    parts: list[SpecPart]
    tolerances: list[str]


class FactoryPack(Model):
    id: str
    project_id: str
    version: int = 1
    created_at: datetime = Field(default_factory=utcnow)
    fallback: bool = False
    cached_note: str | None = Field(default=None, description=(
        "Set when any of stages 1-7 served a cached example: shown on the Factory Pack and the Launch Dossier cover"))
    fallback_stages: list[int] = Field(default_factory=list, description="Stages 1-7 that served a cached example")
    # 1. Product summary and target markets
    product_name: str
    product_summary: str
    product_summary_cn: str | None = None
    target_markets: list[str]
    # 2. Structured spec
    spec: StructuredSpec
    # 3. CAD (STEP) and drawings
    cad_files: list[CadFile]
    # 4. BOM with component risk and alternatives
    bom: list[BOMItem]
    # 5. DFM alerts and resolutions
    dfm_alerts: list[DFMIssue]
    # 6. Certification checklist by market
    certifications: list[Certification]
    # 7. Target quantities and cost estimate
    target_quantities: list[int]
    cost_estimate: list[CostTier]
    # 8. Questions for the factory (EN + CN)
    questions: list[FactoryQuestion]
    # 9. Assumption register
    assumption_register: list[Assumption]


# ---------------------------------------------------------------------------
# Unions, API envelopes
# ---------------------------------------------------------------------------

StageArtifact = Annotated[
    Union[
        BriefArtifact,
        DesignArtifact,
        SpecArtifact,
        DFMArtifact,
        CostsArtifact,
        ProductionPlanArtifact,
        MatchingArtifact,
        NegotiationArtifact,
        ToolingArtifact,
        QCArtifact,
        LogisticsArtifact,
        FinancingArtifact,
        BrandArtifact,
    ],
    Field(discriminator="stage"),
]

ARTIFACT_MODELS: dict[int, type[ArtifactBase]] = {
    1: BriefArtifact,
    2: DesignArtifact,
    3: SpecArtifact,
    4: DFMArtifact,
    5: CostsArtifact,
    6: ProductionPlanArtifact,
    7: MatchingArtifact,
    8: NegotiationArtifact,
    9: ToolingArtifact,
    10: QCArtifact,
    11: LogisticsArtifact,
    12: FinancingArtifact,
    13: BrandArtifact,
}


class CreateProjectRequest(Model):
    mode: ProjectMode
    prompt: str
    name: str | None = None
    pasted_bom: str | None = None
    example: str | None = Field(default=None, description="Force a cached example: 'desk_lamp' | 'tracker_card'")


class RunStageRequest(Model):
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Stage-specific user inputs, e.g. {'answers': {...}} for 1, {'direction_id': 'd1'} for 3, {'approve': true} for 8",
    )


class UpdateStageRequest(Model):
    artifact: StageArtifact
    validate_stage: bool = Field(default=False, description="Also mark the stage validated")


class StageResult(Model):
    project_id: str
    stage: int
    name: str
    title: str
    status: StageStatus
    fallback: bool
    artifact: StageArtifact


class StageSummary(Model):
    stage: int
    name: str
    title: str
    status: StageStatus
    fallback: bool = False
    updated_at: datetime | None = None


class AutorunState(str, Enum):
    idle = "idle"
    running = "running"
    done = "done"
    failed = "failed"


class AutorunStatus(Model):
    """Progress of the background autorun (stages 1-7). Poll GET /projects/{id} every ~2 s."""

    state: AutorunState = AutorunState.idle
    current_stage: int | None = Field(default=None, description="Stage being run while state == running")
    completed_stages: list[int] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class ProjectDetail(Model):
    project: Project
    stages: list[StageSummary]
    autorun: AutorunStatus | None = Field(default=None, description="None if autorun was never started")
    has_fallback: bool = Field(default=False, description="True if any stage 1-7 serves a cached example (fallback: true)")
    fallback_stages: list[int] = Field(default_factory=list, description="Stages (1-13) currently serving a cached example")


class AutorunResult(Model):
    project_id: str
    results: list[StageResult] = Field(default_factory=list, description="Empty for the async 202 response")
    autorun: AutorunStatus | None = None


class RegisterFactoryRequest(Model):
    """POST /factories — mirrors MCP `register_capacity` (PRD §10). The factory is Fictional — demo data."""

    name: str = Field(description="' (fictional)' is appended if missing")
    region: str
    processes: list[ProcessType] = Field(min_length=1)
    materials: list[str] = Field(default_factory=list)
    moq: int = Field(ge=1)
    certifications: list[str] = Field(default_factory=list)
    lead_time_days: int = Field(ge=1, le=365)
    monthly_capacity: int = Field(ge=1)
    current_load_pct: float = Field(ge=0, le=100)
    archetype: str = "balanced"
    personality: str | None = None


class ResetResult(Model):
    projects: list[Project]


class HealthResponse(Model):
    status: Literal["ok"] = "ok"
    version: str
    llm_configured: bool
    models: dict[str, str | None]
    registered_stages: list[int] = Field(description="Stages with a live handler; others serve fixtures")


class ErrorResponse(Model):
    detail: str


CostsArtifact.model_rebuild()
