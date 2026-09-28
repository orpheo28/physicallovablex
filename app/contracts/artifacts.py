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
    tags: list[str] = Field(default_factory=list, description="W21: e.g. ['Example'] for the showcase gallery projects")


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
    format: Literal["step", "stl", "glb", "pdf", "png", "svg", "py"] = Field(description=(
        "py (W21): the build123d program of the model, served by GET /projects/<pid>/cad/code/<n>"))
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


class PartAlternative(Model):
    """W21b: a cheaper / better-stocked catalogue part proposed for a risky BOM line (structured, no text parsing)."""

    part: str = Field(description="Manufacturer part number + package")
    lcsc_pn: str
    price: LabeledValue = Field(description="Unit price at the order quantity (Sourced: LCSC snapshot)")
    stock: LabeledValue | None = None
    label: Label = Label.sourced


class ComponentRiskSummary(Model):
    """W21b: structured risk of one part: level, reasons and the proposed alternative (None when the snapshot has none)."""

    level: RiskLevel
    reasons: list[str] = Field(default_factory=list)
    alternative: PartAlternative | None = None


class ComponentRiskItem(Model):
    bom_item_id: str
    part: str
    level: RiskLevel
    reasons: list[str]
    alternatives: list[str] = Field(default_factory=list)
    stock: LabeledValue | None = None
    lead_time_weeks: LabeledValue | None = None
    alternative: PartAlternative | None = Field(default=None, description=(
        "W21b: cheapest in-stock same-kind part when this one is expensive or low-stock (None: no alternative in the snapshot)"))


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
    tiers: list[CostTier] = Field(min_length=1, description=(
        "500 / 2,000 / 10,000 by default; a site install (unit_basis per_installation, W21c) has ONE tier: the pilot "
        "quantity of installations, with per-installation figures"))
    unit_basis: Literal["per_unit", "per_installation"] = Field(default="per_unit", description=(
        "W21c: per_installation = rooftop solar etc.: unit_cost = installer cost of one installation, target_retail_price = "
        "turnkey installed price, cash for a pilot of reference_quantity installations"))
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
    categories: list[str] = Field(default_factory=list, description=(
        "W21: product categories the factory specialises in (engineering category keys, e.g. lighting, wearable, drone); "
        "empty = generalist. A specialist scores lower on process fit for other categories"))


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
    kind: Literal["factory", "installer", "integrator"] = Field(default="factory", description=(
        "W21b: partner kind for the portal filter — factory (makes parts / assembles), installer (site install, e.g. rooftop "
        "PV), integrator (integrates bought-in modules, e.g. drones / robots)"))


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
    category: str | None = Field(default=None, description="W21: product category (engineering key) for specialist scoring")


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


class ProductPhoto(Model):
    """W27: one AI product photo. With a reference the model only restyles light, surface, lens and framing around OUR
    CAD image (viewer capture or Blender render of the CAD); without one it is a text-only concept image."""

    shot: Literal["hero_studio", "packshot_white", "lifestyle", "in_hand_scale", "detail_macro"]
    url: str = Field(description="/files/<pid>/photo_v<n>_<shot>.png")
    label: str = Field(description=(
        "Honesty caption shown under the image: 'Photo-styled from the CAD (AI image, geometry from our CAD)' or "
        "'AI concept image (no CAD reference)'; lifestyle adds ' · Staged scene — illustrative'"))
    reference: Literal["viewer", "cad_render", "none"] = Field(description=(
        "viewer = PNG captured from the 3D viewer by the client; cad_render = Blender render of the CAD; none = text only"))
    aspect_ratio: str = Field(description="4:5 or 1:1")
    staged: bool = Field(default=False, description="Lifestyle / in-hand scene: illustrative staging, not a real photo shoot")
    model: str | None = Field(default=None, description="Image model slug (OpenRouter)")
    version: int | None = Field(default=None, description="Studio version the photo was made from")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BrandArtifact(ArtifactBase):
    stage: Literal[13] = 13
    name_options: list[NameOption] = Field(min_length=1)
    chosen_name: str | None = None
    packaging: PackagingSpec
    landing_copy: LandingCopy
    shopify_listing: ListingDraft
    amazon_listing: ListingDraft
    listing_photos: list[ProductPhoto] = Field(default_factory=list, description=(
        "W27: e-commerce listing photo kit (packshot_white, lifestyle, in_hand_scale, detail_macro) of the current version"))


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


DRAWINGS_NOTE = "Generated from CAD — verify before release"


class DrawingSheet(Model):
    """C3 (additive): one 2D technical drawing sheet of a version — GET /projects/{id}/drawings?version=n (CAD_DRAWINGS=1).
    Orthographic views (first angle) + isometric, dimensions measured on the STEP, ISO 2768-m title block."""

    sheet: str = Field(description="Sheet id within the version: 'A1' assembly, 'P01'… parts, 'M01'… moulded shells (DFM model)")
    kind: Literal["assembly", "part", "moulded"]
    part_id: str | None = Field(default=None, description="GLB part_id (PartMeta.part_id) drawn on a part sheet; None on the assembly")
    title: str
    svg_url: str = Field(description="/files/<pid>/drawings/v<n>_<sheet>.svg")
    pdf_url: str = Field(description="/files/<pid>/drawings/v<n>_<sheet>.pdf (vector, one page)")
    set_pdf_url: str = Field(description="/files/<pid>/drawings/v<n>_set.pdf — every sheet of the version, one PDF")
    version: int
    size: Literal["A3", "A4"]
    scale: str = Field(description="Scale of the orthographic views, ISO 5455 standard, e.g. '1:2'")
    bbox_mm: list[float] = Field(min_length=3, max_length=3, description="Overall [x, y, z] measured on the STEP (Z up)")
    bom_item_id: str | None = None
    qty: int = 1
    label: Literal["measured"] = "measured"
    note: Literal["Generated from CAD — verify before release"] = DRAWINGS_NOTE


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
    # 10. Engineering & prototype path (W20, additive): checks, standards, power budget, prototype path, firmware note
    engineering: EngineeringArtifact | None = None
    # 3b. Drawings (C3, additive; CAD_DRAWINGS=1): the version's 2D sheets (SVG + PDF), measured on the STEP
    drawings: list[DrawingSheet] = Field(default_factory=list)


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
    """Progress of the background autorun (stages 1-7, or 1-13 + Factory Pack in autofill mode). Poll GET /projects/{id} every ~2 s."""

    state: AutorunState = AutorunState.idle
    through: Literal[7, 13] = Field(default=7, description="Last stage the run goes to: 7 (default) or 13 (autofill: also auto-approves the recommended quote at stage 8 and builds the Factory Pack)")
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


# ---------------------------------------------------------------------------
# Engineering layer (W20) — GET /projects/{id}/engineering, computed from the current project state
# ---------------------------------------------------------------------------


class CheckVerdict(str, Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"
    info = "info"  # no threshold: a figure to know (e.g. annual yield)


class StandardRef(Model):
    code: str = Field(description="e.g. 'IEC 60335-2-2', 'EN 12221-1', 'IEC 60529'")
    title: str
    applies_because: str
    url: str | None = None
    citation_label: Label = Field(description="sourced = the URL was checked to load (date in citation_note); estimate = standard to be confirmed")
    citation_note: str


class DesignRisk(Model):
    id: str
    risk: str
    mitigation: str
    severity: Severity = Severity.major


class RequiredTest(Model):
    id: str
    name: str = Field(description="e.g. 'Drop test 1.5 m', 'IPX7 immersion', 'Salt spray 96 h', 'Tip-over'")
    kind: Literal["drop", "ingress", "salt_spray", "tip_over", "thermal", "electrical", "radio", "mechanical", "battery", "chemical", "other"]
    method: str
    standard: str | None = None


class EngineeringCheck(Model):
    id: str
    name: str
    domain: Literal["stability", "hydrodynamics", "power", "ingress", "airflow", "fluid", "solar", "thermal", "mass", "geometry",
                    "flight", "regulatory", "assembly"]
    value: LabeledValue
    threshold: str | None = Field(default=None, description="Human wording of the pass/warn/fail rule, e.g. '≥ 15° (design target)'")
    verdict: CheckVerdict
    formula: str = Field(description="Formula and assumptions, with the inputs' labels")
    inputs: list[LabeledValue] = Field(default_factory=list, description="Inputs of the formula (each labeled)")
    notes: list[str] = Field(default_factory=list, description="e.g. the sealing checklist of an IP check")


# ---------------------------------------------------------------------------
# Assembly (C2, additive) — GET /projects/{id}/assembly?version=n; EngineeringArtifact.assembly; behind CAD_ASSEMBLY=1
# ---------------------------------------------------------------------------


class FastenerUse(Model):
    """One fastener kind used at a joint (screw + its insert are two rows)."""

    kind: Literal["screw", "insert", "spring_bar", "pin", "nut", "washer"]
    standard: str = Field(description="e.g. 'ISO 14583 (hexalobular pan head)', 'Heat-set brass insert'")
    designation: str = Field(description="e.g. 'M2.5×8', 'M2.5×4.0'")
    size: str = Field(description="Thread / nominal size, e.g. 'M2.5'")
    length_mm: float
    qty: int
    source: str = Field(description="'api.cad.stdparts' (C1 catalogue) or 'built-in table' (C2 fallback)")


class AssemblyJoint(Model):
    id: str
    parent: str = Field(description="part_id of the parent (the part that carries the joint)")
    child: str = Field(description="part_id placed by the joint")
    kind: Literal["rigid", "revolute", "linear"] = Field(description="build123d RigidJoint / RevoluteJoint / LinearJoint")
    method: Literal["screwed", "snap_fit", "inlay", "press_fit", "bonded", "clip", "hinge", "bearing", "slide", "latch"]
    dof: int = Field(description="Degrees of freedom of the child relative to the parent (0 rigid, 1 revolute / linear)")
    origin_mm: list[float] = Field(min_length=3, max_length=3, description="Joint origin, mm, GLB axes (+Y up)")
    axis: list[float] | None = Field(default=None, min_length=3, max_length=3, description="Unit joint axis, GLB axes")
    range: list[float] | None = Field(default=None, min_length=2, max_length=2, description="Motion range: deg (revolute) or mm (linear)")
    fasteners: list[FastenerUse] = Field(default_factory=list)
    rule: str = Field(description="Why this mate: the family / role rule that inferred it")


class AssemblyNode(Model):
    part_id: str = Field(description="= PartMeta.part_id of the version GLB")
    name: str
    role: str
    parent: str | None = Field(default=None, description="Parent part_id (None = assembly root)")
    joint_id: str | None = None
    rigid_body: int = Field(description="Parts with the same number move together (connected by rigid joints)")
    volume: LabeledValue = Field(description="Measured solid volume, mm³")
    explode_vector: list[float] = Field(min_length=3, max_length=3, description="Unit vector, GLB axes; derived from the joint")
    explode_distance_mm: float = Field(description="Cumulative along the tree (a child moves with its parent)")


class AssemblyInterference(Model):
    a: str
    b: str
    volume: LabeledValue = Field(description="Boolean intersection volume, mm³ (Measured; tolerance 0.01 mm³)")
    kind: Literal["interference", "joint_seat", "static_overlap"] = Field(description=(
        "interference = parts that move relative to each other (different rigid bodies, not joint partners) or the two shells "
        "of a parting line overlap → fail; joint_seat = overlap between the two parts of one joint (seat / insertion depth of "
        "concept geometry); static_overlap = parts of one rigid body interpenetrate (concept geometry, pocket at detail design)"))
    note: str = ""


class AssemblyClearance(Model):
    part_id: str = Field(description="Moving part (or the smaller part of an adjacent pair)")
    against: str
    min_clearance: LabeledValue = Field(description="Minimum distance, mm (Measured with BRepExtrema; over the motion range when moving)")
    motion: str = Field(description="e.g. 'revolute 0-360° (12 steps)', 'linear 0-0.8 mm', 'static'")
    verdict: CheckVerdict
    rule: str


class ProjectAssembly(Model):
    """GET /projects/{id}/assembly?version=n — parts connected by build123d joints, with measured assembly checks."""

    project_id: str
    version: int
    label: str = "Measured on the version STEP (build123d / OCCT); mates inferred from the family / part roles"
    source: str = Field(description="STEP the solids were read from, e.g. /files/<pid>/model_v2.step")
    root: str = Field(description="part_id of the assembly root")
    nodes: list[AssemblyNode]
    joints: list[AssemblyJoint]
    interferences: list[AssemblyInterference] = Field(default_factory=list, description="Every overlapping pair > 0.01 mm³, classified")
    clearances: list[AssemblyClearance] = Field(default_factory=list)
    fasteners: list[BOMItem] = Field(default_factory=list, description=(
        "Fastener BOM lines aggregated by designation (ids 'fx<n>'; Estimate price unless LCSC-matched → Sourced)"))
    checks: list[EngineeringCheck] = Field(default_factory=list, description="domain 'assembly'")
    summary: str = Field(description="One line, e.g. '28 parts · 27 joints (3 moving) · 0 interferences · 16 fasteners'")
    engine: str = Field(description="Assembly engine version (cache key)")


class PowerNode(Model):
    id: str
    name: str
    kind: Literal["source", "charger", "storage", "regulator", "load"]
    parent: str | None = Field(default=None, description="Upstream node id (None for a source)")
    voltage: LabeledValue


class NetConnection(Model):
    source: str
    target: str
    bus: Literal["power", "i2c", "spi", "uart", "gpio", "pwm", "adc", "rf", "usb", "analog", "can"]
    signals: str = Field(description="Net names, e.g. 'SDA, SCL, INT1'")


class PowerBudgetLine(Model):
    block: str
    part: str
    active_current: LabeledValue = Field(description="mA while active")
    sleep_current: LabeledValue = Field(description="µA while idle")
    duty_cycle: LabeledValue = Field(description="pct of time active")
    average_current: LabeledValue = Field(description="mA, duty-weighted")


class ElectronicsArchitecture(Model):
    mcu_family: Literal["nrf52", "esp32", "stm32", "avr", "generic"]
    mcu_part: str
    radio: list[str] = Field(default_factory=list)
    power_tree: list[PowerNode]
    connections: list[NetConnection]
    power_budget: list[PowerBudgetLine]
    average_current: LabeledValue
    battery_voltage: LabeledValue | None = None
    battery_capacity: LabeledValue | None = None
    battery_life: LabeledValue | None = None
    pcb_note: str = "PCB layout: next step (human or text-to-PCB)"


class FirmwareProject(Model):
    framework: Literal["zephyr", "arduino"]
    mcu_family: str
    connectivity: str = Field(description="e.g. 'BLE GATT service', 'Wi-Fi + MQTT'")
    url: str = Field(description="/files/<project_id>/firmware.zip")
    files: list[str]
    generated_by: str = Field(description="'template' | 'llm:<model slug>'")
    note: str = "Generated code — not compiled or tested"
    pending_llm: bool = Field(default=False, description="An LLM version is being generated in the background; re-GET to pick it up")


class PrototypeCostLine(Model):
    item: str
    amount: LabeledValue


class DevKitLine(Model):
    part: str
    role: str
    qty: int = 1
    lcsc_pn: str | None = None
    unit_price: LabeledValue


class PrototypePath(Model):
    enclosure_method: str
    enclosure_volume: LabeledValue
    units: int = Field(description="Prototype quantity (input)")
    cost_lines: list[PrototypeCostLine]
    devkit_bom: list[DevKitLine] = Field(default_factory=list)
    assembly_steps: list[str]
    timeline_weeks: LabeledValue
    total_cost: LabeledValue


class SolarDesign(Model):
    location: str
    latitude: float
    longitude: float
    location_assumed: bool = Field(description="True when the location was not in the prompt (default demo site)")
    roof_area: LabeledValue
    module_power: LabeledValue
    module_count: LabeledValue
    peak_power: LabeledValue
    specific_yield: LabeledValue = Field(description="kWh/kWp/year from PVGIS (Sourced)")
    annual_energy: LabeledValue
    monthly_energy: list[LabeledValue] = Field(default_factory=list, description="12 values, kWh")
    install_cost: LabeledValue
    annual_savings: LabeledValue
    payback: LabeledValue
    pvgis_url: str


class InstallerMatch(Model):
    factory_id: str
    name: str = Field(description="Fictional installer name — ends with '(fictional)'")
    region: str
    certifications: list[str]
    lead_time_days: int
    label: Literal["fictional"] = "fictional"


class BuildStrategy(Model):
    """W21: how this product realistically gets built — design everything, assemble bought-in modules, or customise an
    ODM reference platform. Figures are Estimates with their assumptions."""

    strategy: Literal["full_design", "module_assembly", "odm_customization"]
    title: str = Field(description="e.g. 'Full design', 'Module assembly', 'ODM customisation'")
    explanation: str
    customisable: list[str] = Field(description="What the founder designs / chooses")
    not_customisable: list[str] = Field(default_factory=list, description="What comes from the modules / the ODM platform")
    moq: LabeledValue = Field(description="Typical minimum order quantity (units), Estimate")
    entry_cost: LabeledValue = Field(description="Typical entry cost (NRE, tooling, certification) before the first order, Estimate")
    lead_time: LabeledValue = Field(description="Typical time from frozen design to first production units (weeks), Estimate")
    path: list[str] = Field(default_factory=list, description="Realistic steps (for ODM: find a close reference platform…)")
    certifications_note: str = ""
    assumptions: list[str] = Field(default_factory=list)


class EngineeringArtifact(ArtifactBase):
    stage: Literal["engineering"] = "engineering"
    category: str = Field(description="Engineering category key, e.g. wearable, furniture_baby, home_robot, vacuum, irrigation, solar_roof, surfboard, lighting, tracker, generic")
    category_title: str
    partner_word: Literal["factories", "installers"] = "factories"
    site_install: bool = False
    product_name: str
    inputs_digest: str = Field(description="Hash of the project state this was computed from")
    standards: list[StandardRef]
    risks: list[DesignRisk]
    tests: list[RequiredTest]
    checks: list[EngineeringCheck]
    electronics: ElectronicsArchitecture | None = None
    firmware: FirmwareProject | None = None
    prototype: PrototypePath
    solar: SolarDesign | None = None
    installers: list[InstallerMatch] = Field(default_factory=list, description="Site-install mode: fictional certified installers")
    build_strategy: BuildStrategy | None = Field(default=None, description="W21: full design / module assembly / ODM customisation")
    unit_basis: Literal["per_unit", "per_installation"] = Field(default="per_unit", description=(
        "W21b: what one 'unit' is for this product — per_installation for site installs (rooftop solar): costs are per site"))
    installation_cost: LabeledValue | None = Field(default=None, description=(
        "W21b: turnkey cost of one installation (per_installation only; = solar.install_cost)"))
    assembly: ProjectAssembly | None = Field(default=None, description=(
        "C2 (CAD_ASSEMBLY=1): assembly tree, joints, measured interference / clearance / fastener checks (also in `checks`, "
        "domain 'assembly'); travels into the Factory Pack with `FactoryPack.engineering`"))


# ---------------------------------------------------------------------------
# Studio (W17) — refine the product by prompting; every prompt = a new Version
# ---------------------------------------------------------------------------


class VersionStatus(str, Enum):
    running = "running"
    done = "done"
    failed = "failed"


class VersionChange(Model):
    area: Literal["color", "material", "shape", "dimensions", "feature", "component", "price", "markets", "requirement",
                  "certification", "cost", "performance"]
    label: str = Field(description="Human wording, e.g. 'Colour', 'Pod height', 'Optical heart-rate sensor'")
    before: str | None = None
    after: str | None = None
    label_kind: Label = Field(description="Honesty label of the new value: measured (CAD), sourced (LCSC), estimate, fictional")
    risk: ComponentRiskSummary | None = Field(default=None, description=(
        "W21b: on a 'Component added' change — structured supply risk + proposed cheaper in-stock alternative"))


class VersionUnitCost(Model):
    quantity: int
    value: float = Field(description="Ex-works unit cost, USD")
    label: Label = Label.estimate
    source_or_assumption: str | None = None


class VersionFactory(Model):
    name: str = Field(description="Fictional factory name")
    score: float = Field(description="0-100 match score on demo data")
    label: Literal["fictional"] = "fictional"


class VersionPreview(Model):
    glb_url: str | None = Field(default=None, description="Full-product GLB of this version (/files/<pid>/v<n>.glb)")
    render_url: str | None = Field(default=None, description="AI concept render (illustrative, not the CAD); patched in later")
    unit_basis: Literal["per_unit", "per_installation"] = Field(default="per_unit", description="W21e: see CostsArtifact.unit_basis")
    installed_price: LabeledValue | None = Field(default=None, description=(
        "W21e, per_installation only: THE customer price of one installation for this version (turnkey, battery included "
        "when the BOM has one) — the single source for the Studio strip, Overview and gallery card"))
    installer_cost: LabeledValue | None = Field(default=None, description=(
        "W21e, per_installation only: what one installation costs the installer (equipment + labour + site admin)"))
    dimensions: Dimensions | None = Field(default=None, description="Measured on the built STEP (moulded parts)")
    color_hex: str | None = None
    color_name: str | None = None
    material: str | None = None
    finish: str | None = None
    shape_family: str | None = Field(default=None, description=(
        "rounded_box | puck | slab | wearable_band | ring, or a W21 product family (board, furniture, stick_vacuum, home_robot, "
        "irrigation, solar_array, drone, hair_dryer, camera, smartphone)"))
    unit_costs: list[VersionUnitCost] = Field(default_factory=list)
    top_factories: list[VersionFactory] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list, description="'<market> <standard>' of the required certifications")
    bom_count: int = 0
    code_url: str | None = Field(default=None, description=(
        "W21: the build123d program of this version's model (/projects/<pid>/cad/code/<k>): AI-written, or the parametric "
        "family seed when AI CAD is off / failed (see cad_label)"))
    step_url: str | None = Field(default=None, description="W21: STEP of the model shown in glb_url (AI model when present)")
    cad_label: str | None = Field(default=None, description=(
        "W21: 'AI-generated CAD (concept level) — geometry measured on the result' or 'Parametric family CAD (concept level) — …'"))
    cad_source: str | None = Field(default=None, description="W21: llm:<model> | seed:<family> | previous_version | family:<name>")
    photos: list[ProductPhoto] = Field(default_factory=list, description=(
        "W27: AI product photos of this version (one per shot, newest wins). hero_studio, when present, is also render_url"))
    photo_stale: bool = Field(default=False, description=(
        "W29b: the look changed (part edit) and no hero_studio photo of the new look exists yet (no stored viewer / CAD "
        "reference, or the photo job has not finished): any photo shown is of an older look — say so. Cleared when a "
        "hero_studio photo of this version is attached"))


class Version(Model):
    n: int
    message: str = Field(description="The founder's prompt ('Studio start' for version 1)")
    status: VersionStatus = VersionStatus.running
    created_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    summary: str = ""
    changes: list[VersionChange] = Field(default_factory=list)
    preview: VersionPreview | None = None
    error: str | None = Field(default=None, description="Plain-language reason when status == failed")
    is_current: bool = Field(default=False, description="Stage artifacts reflect this version")
    render_pending: bool = Field(default=False, description="An AI concept render for this version is still running")
    background_pending: bool = Field(default=False, description="AI DFM review / production plan still refreshing in the background")
    cad_pending: bool = Field(default=False, description=(
        "W21: the AI CAD model (text-to-CAD) of this version is still being generated; preview.glb_url / code_url are "
        "patched in when done"))
    cad_note: str | None = Field(default=None, description="W21: plain-language note on the AI CAD (e.g. fell back to the family)")
    cad_attempts: int = Field(default=0, description="W21c: LLM attempts the AI CAD program of this version took (0 = no AI CAD run)")
    cad_repairs: int = Field(default=0, description="W21c: self-repair rounds (attempts − 1 when it ended ok) — 'self-repaired N×'")
    look_changed: bool = Field(default=True, description=(
        "W21e: colour, material, finish, shape or dimensions changed vs the previous version. False → the previous version's "
        "photos are carried over (copied, same labels) and no new photo is generated"))


class ExampleSummary(Model):
    """W21: one showcase project of the gallery (GET /examples). Opening it costs nothing: every stage is cached."""

    id: str = Field(description="Project id, e.g. demo_whoop_kitesurf")
    slug: str
    name: str
    prompt: str
    category: str = Field(description="Engineering category key")
    strategy: Literal["full_design", "module_assembly", "odm_customization"] | None = None
    hero_image_url: str | None = Field(default=None, description="Concept render (illustrative) or None")
    glb_url: str | None = Field(default=None, description="3D model of the current version")
    one_line_result: str
    unit_basis: Literal["per_unit", "per_installation"] = "per_unit"
    unit_cost: LabeledValue | None = Field(default=None, description=(
        "W21b: headline cost — ex-works unit cost at the reference quantity (per_unit) or turnkey cost per installation"))
    versions: int = 0
    stages_done: int = 0
    tags: list[str] = Field(default_factory=list)
    seeded: bool = Field(default=False, description="The project exists in the database (after POST /demo/reset)")
    hero_image_label: str | None = Field(default=None, description="W27: honesty caption of hero_image_url")
    photos: list[ProductPhoto] = Field(default_factory=list, description="W27: hero_studio + lifestyle photos of the current version")


class RefineRequest(Model):
    message: str = Field(min_length=1, max_length=1000)


class StudioAccepted(Model):
    version: int


CostsArtifact.model_rebuild()
FactoryPack.model_rebuild()


# ---------------------------------------------------------------------------
# W27 — product photography (reference-based AI photos + listing kit)
# ---------------------------------------------------------------------------


class PhotoJob(Model):
    state: Literal["idle", "running", "done", "failed"] = "idle"
    version: int | None = None
    shots: list[str] = Field(default_factory=list, description="Shots requested by this job")
    done: list[str] = Field(default_factory=list, description="Shots generated so far")
    failed: list[str] = Field(default_factory=list, description="Shots that failed (the previous photo, if any, is kept)")
    error: str | None = Field(default=None, description="Plain-language reason when a shot failed (e.g. image credits exhausted)")
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ProjectPhotos(Model):
    """GET /projects/{id}/photos — photos of the current version + the running / last photo job (poll every ~2 s)."""

    project_id: str
    version: int | None = Field(default=None, description="Current Studio version (None: not a Studio project)")
    photos: list[ProductPhoto] = Field(default_factory=list)
    job: PhotoJob = Field(default_factory=PhotoJob)
    configured: bool = Field(default=False, description="An image model + key are configured (else POSTs return 503)")


class PhotoAccepted(Model):
    version: int
    shots: list[str]


# ---------------------------------------------------------------------------
# W29 — 3D parts & anatomy (named GLB nodes, structured part edits, illustrative internal layout)
# ---------------------------------------------------------------------------

PartRole = Literal[
    "shell_top", "shell_bottom", "strap", "button", "window", "lens", "diffuser", "frame", "arm", "prop", "motor", "pcb",
    "component", "battery", "antenna", "connector", "cable", "fastener", "other",
]

ANATOMY_LABEL = "Illustrative internal layout — not a routed PCB"


class PartEditable(Model):
    """One editable parameter of a part (slider): POST /parts/{part_id}/edit {param, value} within [min, max]."""

    param: str = Field(description="Family parameter (fp_*) or AI CAD program parameter name")
    label: str = Field(description="Human wording, e.g. 'Pod thickness'")
    min: float
    max: float
    step: float
    unit: str = Field(description="mm, pct …")
    value: float = Field(description="Current value")


class PartMeta(Model):
    """W29: one part of a version's GLB. The GLB node named `part_id` carries this object as glTF `extras`."""

    part_id: str = Field(description="Stable id within the version = GLB node name, e.g. 'shell_top', 'strap', 'u_ppg_1'")
    name: str = Field(description="Human name, e.g. 'Top shell', 'MAX30102 PPG sensor'")
    role: PartRole
    layer_id: str = Field(description="Anatomy layer this part belongs to (see ProjectAnatomy.layers)")
    material: str = Field(description="Human material, e.g. 'PC/ABS', 'LSR silicone', 'FR-4'")
    finish: str | None = Field(default=None, description="e.g. 'soft-touch matte', 'anodised', 'gloss'")
    colour_hex: str = Field(description="#RRGGBB")
    measured_bbox_mm: list[float] = Field(min_length=3, max_length=3, description="[x, y, z] extent in mm (GLB axes: +Y up)")
    centroid_mm: list[float] = Field(min_length=3, max_length=3, description="[x, y, z] bbox centre in mm (GLB axes)")
    label: Literal["measured", "estimate"] = Field(description=(
        "measured = geometry measured on our CAD; estimate = illustrative anatomy body (package table / sizing rule)"))
    bom_item_id: str | None = Field(default=None, description="BOM line this part stands for (stage 3 bom[].id)")
    lcsc_pn: str | None = None
    package: str | None = Field(default=None, description="Package string used for the body size, e.g. 'LGA-14', 'USB-C'")
    unit_price: LabeledValue | None = None
    editable: list[PartEditable] = Field(default_factory=list)
    colour_editable: bool = False
    material_options: list[str] = Field(default_factory=list, description="Material keys accepted by POST /parts/{id}/edit")
    parent_part_id: str | None = Field(default=None, description="C2 (CAD_ASSEMBLY=1): parent in the assembly tree")
    joint: Literal["rigid", "revolute", "linear"] | None = Field(default=None, description="C2: joint to the parent")
    explode_vector: list[float] | None = Field(default=None, min_length=3, max_length=3, description=(
        "C2: unit vector (GLB axes) derived from the joint; move the part node by explode_vector × explode_distance_mm"))
    explode_distance_mm: float | None = Field(default=None, description="C2: cumulative along the assembly tree")


class ProjectParts(Model):
    """GET /projects/{id}/parts?version=n"""

    version: int
    glb_url: str = Field(description="The version's full-product GLB (= preview.glb_url); one node per part")
    parts: list[PartMeta] = Field(default_factory=list)


class PartEditRequest(Model):
    """POST /projects/{id}/parts/{part_id}/edit — deterministic refine (no LLM). At least one field."""

    colour_hex: str | None = None
    material: str | None = Field(default=None, description="One of PartMeta.material_options")
    finish: str | None = None
    param: str | None = Field(default=None, description="One of PartMeta.editable[].param (requires value)")
    value: float | None = None


class AnatomyLayer(Model):
    id: str
    name: str
    order: int = Field(description="0 = outermost / first to lift")
    parts: list[str] = Field(default_factory=list, description="part_ids (nodes of the anatomy GLB)")
    explode_vector: list[float] = Field(min_length=3, max_length=3, description="Unit vector, GLB axes (+Y up)")
    explode_distance_mm: float
    caption: str


class AnatomyCamera(Model):
    position_mm: list[float] = Field(min_length=3, max_length=3)
    target_mm: list[float] = Field(min_length=3, max_length=3)
    fov_deg: float


class AnatomyStep(Model):
    id: str
    title: str
    kicker: str = Field(description="e.g. '01 · The band'")
    caption: str = Field(description="One line with real BOM / engineering values and their labels")
    camera: AnatomyCamera
    layers_exploded: list[str] = Field(default_factory=list)
    focus_parts: list[str] = Field(default_factory=list)


class ProjectAnatomy(Model):
    """GET /projects/{id}/anatomy?version=n — illustrative internal layout generated from the BOM (deterministic)."""

    version: int
    glb_url: str = Field(description="Companion anatomy GLB /files/<pid>/anatomy_v<n>.glb (exterior parts + internals)")
    label: Literal["Illustrative internal layout — not a routed PCB"] = ANATOMY_LABEL
    kind: Literal["electronics", "construction"] = Field(default="electronics", description=(
        "construction = solid product (board, furniture): layers are construction layers, not a PCB"))
    bbox_mm: list[float] = Field(min_length=3, max_length=3, description="[x, y, z] of the whole product, GLB axes")
    layers: list[AnatomyLayer] = Field(default_factory=list)
    steps: list[AnatomyStep] = Field(default_factory=list)
    parts: list[PartMeta] = Field(default_factory=list, description="Every node of the anatomy GLB")
