/* AUTO-GENERATED from contracts/schemas/_bundle.json — do not edit. Regenerate: uv run python -m contracts.export_schemas && npm run gen:types */

/**
 * The four honesty labels. UI text: Measured / Sourced / Estimate / Fictional — demo data.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Label".
 */
export type Label = "measured" | "sourced" | "estimate" | "fictional";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProjectMode".
 */
export type ProjectMode = "idea" | "prototype";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProjectStatus".
 */
export type ProjectStatus = "active" | "archived";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "StageStatus".
 */
export type StageStatus = "not_started" | "draft" | "validated";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "BOMCategory".
 */
export type BOMCategory = "electronic" | "mechanical" | "packaging";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "RiskLevel".
 */
export type RiskLevel = "low" | "medium" | "high";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProcessType".
 */
export type ProcessType =
  "injection_molding" | "cnc" | "sheet_metal" | "die_casting" | "extrusion" | "pcba" | "assembly" | "other";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Severity".
 */
export type Severity = "critical" | "major" | "minor";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DFMMethod".
 */
export type DFMMethod = "measured" | "ai_reviewed";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "RFQStatus".
 */
export type RFQStatus = "sent" | "quoted" | "declined" | "accepted";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "QuoteStatus".
 */
export type QuoteStatus = "submitted" | "countered" | "superseded" | "accepted" | "rejected";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Speaker".
 */
export type Speaker = "platform_agent" | "factory_agent" | "user";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "MilestoneKind".
 */
export type MilestoneKind =
  | "deposit"
  | "tooling_t0"
  | "tooling_t1"
  | "golden_sample"
  | "certification"
  | "mass_production"
  | "pre_shipment_inspection"
  | "shipment"
  | "delivered"
  | "other";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "CheckVerdict".
 */
export type CheckVerdict = "pass" | "warn" | "fail" | "info";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AutorunState".
 */
export type AutorunState = "idle" | "running" | "done" | "failed";
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "VersionStatus".
 */
export type VersionStatus = "running" | "done" | "failed";

export interface ContractsBundle {
  LabeledValue: LabeledValue;
  Assumption: Assumption;
  Project: Project;
  BriefArtifact: BriefArtifact;
  DesignArtifact: DesignArtifact;
  SpecArtifact: SpecArtifact;
  DFMArtifact: DFMArtifact;
  CostsArtifact: CostsArtifact;
  ProductionPlanArtifact: ProductionPlanArtifact;
  MatchingArtifact: MatchingArtifact;
  NegotiationArtifact: NegotiationArtifact;
  ToolingArtifact: ToolingArtifact;
  QCArtifact: QCArtifact;
  LogisticsArtifact: LogisticsArtifact;
  FinancingArtifact: FinancingArtifact;
  BrandArtifact: BrandArtifact;
  FactoryPack: FactoryPack;
  Factory: Factory;
  CapacityProfile: CapacityProfile;
  RegisterFactoryRequest: RegisterFactoryRequest;
  AutorunStatus: AutorunStatus;
  RFQ: RFQ;
  Quote: Quote;
  NegotiationTurn: NegotiationTurn;
  Milestone: Milestone;
  RFQWithQuotes: RFQWithQuotes;
  CreateProjectRequest: CreateProjectRequest;
  RunStageRequest: RunStageRequest;
  UpdateStageRequest: UpdateStageRequest;
  StageResult: StageResult;
  StageSummary: StageSummary;
  ProjectDetail: ProjectDetail;
  AutorunResult: AutorunResult;
  ResetResult: ResetResult;
  HealthResponse: HealthResponse;
  ErrorResponse: ErrorResponse;
  EngineeringArtifact: EngineeringArtifact;
  Version: Version;
  VersionChange: VersionChange;
  VersionPreview: VersionPreview;
  RefineRequest: RefineRequest;
  ExampleSummary: ExampleSummary;
  BuildStrategy: BuildStrategy;
  ComponentRiskSummary: ComponentRiskSummary;
  PartAlternative: PartAlternative;
  StudioAccepted: StudioAccepted;
  ProductPhoto: ProductPhoto;
  PhotoJob: PhotoJob;
  ProjectPhotos: ProjectPhotos;
  PhotoAccepted: PhotoAccepted;
  PartEditable: PartEditable;
  PartMeta: PartMeta;
  ProjectParts: ProjectParts;
  PartEditRequest: PartEditRequest;
  AnatomyLayer: AnatomyLayer;
  AnatomyCamera: AnatomyCamera;
  AnatomyStep: AnatomyStep;
  ProjectAnatomy: ProjectAnatomy;
  DrawingSheet: DrawingSheet;
  ProjectAssembly: ProjectAssembly;
  Label: Label;
  StageStatus: StageStatus;
  ProcessType: ProcessType;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "LabeledValue".
 */
export interface LabeledValue {
  value: number;
  /**
   * e.g. USD, EUR, mm, g, days, weeks, pct, units, man-days
   */
  unit: string;
  label: Label;
  /**
   * Sourced: '<source>, <YYYY-MM-DD>'. Estimate: the assumption. Measured: the check. Fictional: 'demo data'.
   */
  source_or_assumption: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Assumption".
 */
export interface Assumption {
  id: string;
  text: string;
  label: Label;
  source: string | null;
  /**
   * Stage that introduced the assumption
   */
  stage: number | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Project".
 */
export interface Project {
  id: string;
  name: string;
  mode: ProjectMode;
  prompt: string;
  pasted_bom: string | null;
  /**
   * Fixture set used for fallbacks, e.g. 'desk_lamp', 'tracker_card'
   */
  example: string | null;
  status: ProjectStatus;
  created_at: string;
  /**
   * Keys are stage numbers as strings ('1'..'13')
   */
  stage_status: {
    [k: string]: StageStatus;
  };
  /**
   * W21: e.g. ['Example'] for the showcase gallery projects
   */
  tags: string[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "BriefArtifact".
 */
export interface BriefArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 1;
  mode: ProjectMode;
  prompt: string;
  product_name: string;
  one_liner: string;
  category: string;
  target_markets: string[];
  target_retail_price: LabeledValue;
  /**
   * Volume tiers, default [500, 2000, 10000]
   */
  target_volumes: number[];
  key_features: string[];
  constraints: string[];
  has_battery: boolean;
  /**
   * e.g. BLE, Wi-Fi, NFC; empty if none
   */
  wireless: string[];
  /**
   * Prototype mode only
   */
  pasted_bom: BOMItem[];
  /**
   * @maxItems 5
   */
  clarifying_questions:
    | []
    | [ClarifyingQuestion]
    | [ClarifyingQuestion, ClarifyingQuestion]
    | [ClarifyingQuestion, ClarifyingQuestion, ClarifyingQuestion]
    | [ClarifyingQuestion, ClarifyingQuestion, ClarifyingQuestion, ClarifyingQuestion]
    | [ClarifyingQuestion, ClarifyingQuestion, ClarifyingQuestion, ClarifyingQuestion, ClarifyingQuestion];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "BOMItem".
 */
export interface BOMItem {
  id: string;
  part: string;
  category: BOMCategory;
  /**
   * Quantity per finished unit
   */
  qty: number;
  description: string | null;
  manufacturer_pn: string | null;
  /**
   * e.g. 'C725790' when matched to the LCSC snapshot
   */
  lcsc_pn: string | null;
  unit_cost_est: LabeledValue | null;
  risk: ComponentRisk | null;
  alternative: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ComponentRisk".
 */
export interface ComponentRisk {
  level: RiskLevel;
  /**
   * e.g. EOL, single source, long lead time, low stock
   */
  reasons: string[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ClarifyingQuestion".
 */
export interface ClarifyingQuestion {
  id: string;
  topic: "markets" | "volume" | "target_price" | "battery" | "wireless" | "other";
  question: string;
  options: string[];
  answer: string | null;
  skipped: boolean;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DesignArtifact".
 */
export interface DesignArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 2;
  /**
   * @minItems 3
   * @maxItems 3
   */
  directions: [DesignDirection, DesignDirection, DesignDirection];
  chosen_direction_id: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DesignDirection".
 */
export interface DesignDirection {
  id: string;
  name: string;
  description: string;
  shape: string;
  material: string;
  finish: string;
  dimensions: Dimensions;
  /**
   * Parametric inputs for the build123d generator (mm)
   */
  cad_parameters: {
    [k: string]: number;
  };
  render_url: string | null;
  glb_url: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Dimensions".
 */
export interface Dimensions {
  length: LabeledValue;
  width: LabeledValue;
  height: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "SpecArtifact".
 */
export interface SpecArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 3;
  product_name: string;
  direction_id: string;
  overall_dimensions: Dimensions;
  weight: LabeledValue;
  parts: SpecPart[];
  electronics_blocks: ElectronicsBlock[];
  electronics_edges: ElectronicsEdge[];
  bom: BOMItem[];
  tolerances: string[];
  cad_files: CadFile[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "SpecPart".
 */
export interface SpecPart {
  id: string;
  name: string;
  material: string;
  finish: string;
  process_hint: ProcessType | null;
  /**
   * e.g. '±0.1 mm on mating faces'
   */
  tolerance: string | null;
  dimensions: Dimensions | null;
  wall_thickness: LabeledValue | null;
  quantity: number;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ElectronicsBlock".
 */
export interface ElectronicsBlock {
  id: string;
  name: string;
  function: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ElectronicsEdge".
 */
export interface ElectronicsEdge {
  source: string;
  target: string;
  signal: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "CadFile".
 */
export interface CadFile {
  /**
   * py (W21): the build123d program of the model, served by GET /projects/<pid>/cad/code/<n>
   */
  format: "step" | "stl" | "glb" | "pdf" | "png" | "svg" | "py";
  /**
   * Served by the API, e.g. /files/<project_id>/enclosure.step
   */
  url: string;
  description: string | null;
  size_bytes: number | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DFMArtifact".
 */
export interface DFMArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 4;
  issues: DFMIssue[];
  component_risks: ComponentRiskItem[];
  certifications: Certification[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DFMIssue".
 */
export interface DFMIssue {
  id: string;
  severity: Severity;
  category: "draft" | "undercut" | "projection" | "wall_thickness" | "tolerance" | "assembly" | "material" | "other";
  method: DFMMethod;
  part_id: string | null;
  description: string;
  fix: string;
  /**
   * The rule the finding is based on, with its source
   */
  rule_citation: string;
  /**
   * Required when method == measured
   */
  measurement: LabeledValue | null;
  resolved: boolean;
  resolution: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ComponentRiskItem".
 */
export interface ComponentRiskItem {
  bom_item_id: string;
  part: string;
  level: RiskLevel;
  reasons: string[];
  alternatives: string[];
  stock: LabeledValue | null;
  lead_time_weeks: LabeledValue | null;
  /**
   * W21b: cheapest in-stock same-kind part when this one is expensive or low-stock (None: no alternative in the snapshot)
   */
  alternative: PartAlternative | null;
}
/**
 * W21b: a cheaper / better-stocked catalogue part proposed for a risky BOM line (structured, no text parsing).
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PartAlternative".
 */
export interface PartAlternative {
  /**
   * Manufacturer part number + package
   */
  part: string;
  lcsc_pn: string;
  price: LabeledValue;
  stock: LabeledValue | null;
  label: Label;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Certification".
 */
export interface Certification {
  /**
   * US, EU, UK, ...
   */
  market: string;
  /**
   * e.g. FCC Part 15B, CE (LVD/EMC/RED), UKCA, UN38.3
   */
  standard: string;
  applies_because: string;
  required: boolean;
  cost_est: LabeledValue;
  lead_time_weeks: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "CostsArtifact".
 */
export interface CostsArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 5;
  currency: string;
  bom_lines: CostLine[];
  volume_factor: LabeledValue;
  /**
   * 500 / 2,000 / 10,000 by default; a site install (unit_basis per_installation, W21c) has ONE tier: the pilot quantity of installations, with per-installation figures
   *
   * @minItems 1
   */
  tiers: [CostTier, ...CostTier[]];
  /**
   * W21c: per_installation = rooftop solar etc.: unit_cost = installer cost of one installation, target_retail_price = turnkey installed price, cash for a pilot of reference_quantity installations
   */
  unit_basis: "per_unit" | "per_installation";
  tooling: ToolingItem[];
  tooling_total: LabeledValue;
  certification_total: LabeledValue;
  /**
   * Tier used for the cash-needed figure (first order)
   */
  reference_quantity: number;
  total_cash_needed: LabeledValue;
  /**
   * Components summing to total_cash_needed
   */
  cash_breakdown: LandedCostComponent[];
  target_retail_price: LabeledValue;
  breakeven_units: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "CostLine".
 */
export interface CostLine {
  bom_item_id: string;
  part: string;
  qty_per_unit: number;
  unit_price: LabeledValue;
  lcsc_pn: string | null;
  stock: LabeledValue | null;
  extended: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "CostTier".
 */
export interface CostTier {
  quantity: number;
  bom_cost: LabeledValue;
  assembly_cost: LabeledValue;
  packaging_cost: LabeledValue;
  unit_cost: LabeledValue;
  tooling_amortisation: LabeledValue;
  margin_pct: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ToolingItem".
 */
export interface ToolingItem {
  name: string;
  process: ProcessType;
  cost: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "LandedCostComponent".
 */
export interface LandedCostComponent {
  name: string;
  amount: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProductionPlanArtifact".
 */
export interface ProductionPlanArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 6;
  steps: ProcessStep[];
  assembly_notes: string[];
  total_lead_time_days: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProcessStep".
 */
export interface ProcessStep {
  part_id: string;
  part_name: string;
  process: ProcessType;
  reason: string;
  /**
   * e.g. 'Shenzhen, Guangdong'
   */
  region: string;
  lead_time_days: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "MatchingArtifact".
 */
export interface MatchingArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 7;
  factory_pack_id: string;
  queries: SearchCapacityQuery[];
  /**
   * @minItems 3
   */
  shortlist: [FactoryMatch, FactoryMatch, FactoryMatch, ...FactoryMatch[]];
}
/**
 * Mirrors MCP `search_capacity` input.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "SearchCapacityQuery".
 */
export interface SearchCapacityQuery {
  process: ProcessType;
  material: string;
  quantity: number;
  certifications_required: string[];
  deadline: string | null;
  /**
   * W21: product category (engineering key) for specialist scoring
   */
  category: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FactoryMatch".
 */
export interface FactoryMatch {
  rank: number;
  factory_id: string;
  factory_name: string;
  score: LabeledValue;
  score_breakdown: ScoreComponent[];
  reasons: string[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ScoreComponent".
 */
export interface ScoreComponent {
  criterion: "process_fit" | "moq" | "certifications" | "load" | "lead_time";
  score: number;
  weight: number;
  note: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "NegotiationArtifact".
 */
export interface NegotiationArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 8;
  rfqs: RFQ[];
  quotes: Quote[];
  transcript: NegotiationTurn[];
  recommendation: Recommendation;
  user_approved: boolean;
  /**
   * Set once the user approves
   */
  final_terms: FinalTerms | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "RFQ".
 */
export interface RFQ {
  id: string;
  project_id: string;
  factory_id: string;
  factory_pack_id: string;
  quantities: number[];
  status: RFQStatus;
  created_at: string;
  label: "fictional";
}
/**
 * Mirrors MCP `submit_quote` (PRD §10). Each counter creates a new version.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Quote".
 */
export interface Quote {
  id: string;
  rfq_id: string;
  factory_id: string;
  version: number;
  tiers: QuoteTier[];
  tooling_usd: number;
  moq: number;
  lead_time_days: number;
  /**
   * e.g. '30% deposit / 70% before shipment'
   */
  payment_terms: string;
  exceptions: string[];
  status: QuoteStatus;
  created_at: string;
  label: "fictional";
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "QuoteTier".
 */
export interface QuoteTier {
  quantity: number;
  unit_price_usd: number;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "NegotiationTurn".
 */
export interface NegotiationTurn {
  id: string;
  rfq_id: string;
  factory_id: string;
  turn: number;
  speaker: Speaker;
  message: string;
  /**
   * Machine-translated, to be reviewed by a native speaker
   */
  message_cn: string | null;
  quote_id: string | null;
  proposed_changes: {
    [k: string]: unknown;
  };
  rationale: string | null;
  created_at: string;
  label: "fictional";
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Recommendation".
 */
export interface Recommendation {
  factory_id: string;
  quote_id: string;
  rationale: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FinalTerms".
 */
export interface FinalTerms {
  factory_id: string;
  quote_id: string;
  quantity: number;
  unit_price: LabeledValue;
  tooling: LabeledValue;
  moq: number;
  lead_time_days: LabeledValue;
  payment_terms: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ToolingArtifact".
 */
export interface ToolingArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 9;
  milestones: Milestone[];
  payment_schedule: PaymentScheduleItem[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Milestone".
 */
export interface Milestone {
  id: string;
  name: string;
  kind: MilestoneKind;
  start_date: string;
  end_date: string;
  duration_days: LabeledValue;
  depends_on: string[];
  /**
   * Cash out at this milestone, if any
   */
  payment: LabeledValue | null;
  notes: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PaymentScheduleItem".
 */
export interface PaymentScheduleItem {
  milestone_id: string;
  description: string;
  pct_of_order: number | null;
  amount: LabeledValue;
  due_date: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "QCArtifact".
 */
export interface QCArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 10;
  standard: string;
  inspection_level: string;
  lot_size: number;
  sample_size: LabeledValue;
  defects: DefectClass[];
  inspection_man_days: LabeledValue;
  man_day_rate: LabeledValue;
  inspection_cost: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DefectClass".
 */
export interface DefectClass {
  id: string;
  severity: Severity;
  description: string;
  /**
   * Spec line (part id / tolerance / certification) the defect maps to
   */
  spec_ref: string;
  check_method: string;
  /**
   * Acceptable quality limit for this class, e.g. 0, 2.5, 4.0
   */
  aql: number;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "LogisticsArtifact".
 */
export interface LogisticsArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 11;
  incoterm: "EXW" | "FOB" | "CIF" | "DDP";
  destination: string;
  quantity: number;
  freight_options: FreightOption[];
  chosen_mode: "sea_lcl" | "sea_fcl" | "air" | "express";
  hts: HTSLine;
  section_122_applied: boolean;
  /**
   * Per-unit components (PRD §11)
   */
  landed_cost_breakdown: LandedCostComponent[];
  landed_cost_per_unit: LabeledValue;
  reconciles_with_stage5: boolean;
  reconciliation_note: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FreightOption".
 */
export interface FreightOption {
  mode: "sea_lcl" | "sea_fcl" | "air" | "express";
  transit_days: LabeledValue;
  cost_per_unit: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "HTSLine".
 */
export interface HTSLine {
  /**
   * e.g. '9405.21.xx'
   */
  code: string;
  description: string;
  general_rate: LabeledValue;
  section_301_rate: LabeledValue;
  source_url: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FinancingArtifact".
 */
export interface FinancingArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 12;
  cash_curve: CashPoint[];
  total_cash: LabeledValue;
  matches_stage5_total: boolean;
  options: FinancingOption[];
  /**
   * Stage 5 budget reference (total cash needed)
   */
  stage5_total: LabeledValue | null;
  /**
   * Why the curve differs from stage 5 (e.g. the approved quote replaced the estimate); None if equal
   */
  reconciliation_note: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "CashPoint".
 */
export interface CashPoint {
  date: string;
  milestone_id: string;
  description: string;
  cash_out: LabeledValue;
  cumulative: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FinancingOption".
 */
export interface FinancingOption {
  kind: "preorders" | "crowdfunding" | "inventory_financing" | "revenue_based" | "equity" | "other";
  name: string;
  description: string;
  cost: LabeledValue | null;
  pros: string[];
  cons: string[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "BrandArtifact".
 */
export interface BrandArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: 13;
  /**
   * @minItems 1
   */
  name_options: [NameOption, ...NameOption[]];
  chosen_name: string | null;
  packaging: PackagingSpec;
  landing_copy: LandingCopy;
  shopify_listing: ListingDraft;
  amazon_listing: ListingDraft;
  /**
   * W27: e-commerce listing photo kit (packshot_white, lifestyle, in_hand_scale, detail_macro) of the current version
   */
  listing_photos: ProductPhoto[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "NameOption".
 */
export interface NameOption {
  name: string;
  rationale: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PackagingSpec".
 */
export interface PackagingSpec {
  box_type: string;
  dimensions: Dimensions;
  materials: string[];
  printing: string;
  contents: string[];
  unit_cost: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "LandingCopy".
 */
export interface LandingCopy {
  headline: string;
  subheadline: string;
  bullets: string[];
  cta: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ListingDraft".
 */
export interface ListingDraft {
  channel: "shopify" | "amazon";
  title: string;
  description: string;
  bullets: string[];
  price: LabeledValue;
  keywords: string[];
}
/**
 * W27: one AI product photo. With a reference the model only restyles light, surface, lens and framing around OUR
 * CAD image (viewer capture or Blender render of the CAD); without one it is a text-only concept image.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProductPhoto".
 */
export interface ProductPhoto {
  shot: "hero_studio" | "packshot_white" | "lifestyle" | "in_hand_scale" | "detail_macro";
  /**
   * /files/<pid>/photo_v<n>_<shot>.png
   */
  url: string;
  /**
   * Honesty caption shown under the image: 'Photo-styled from the CAD (AI image, geometry from our CAD)' or 'AI concept image (no CAD reference)'; lifestyle adds ' · Staged scene — illustrative'
   */
  label: string;
  /**
   * viewer = PNG captured from the 3D viewer by the client; cad_render = Blender render of the CAD; none = text only
   */
  reference: "viewer" | "cad_render" | "none";
  /**
   * 4:5 or 1:1
   */
  aspect_ratio: string;
  /**
   * Lifestyle / in-hand scene: illustrative staging, not a real photo shoot
   */
  staged: boolean;
  /**
   * Image model slug (OpenRouter)
   */
  model: string | null;
  /**
   * Studio version the photo was made from
   */
  version: number | null;
  created_at: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FactoryPack".
 */
export interface FactoryPack {
  id: string;
  project_id: string;
  version: number;
  created_at: string;
  fallback: boolean;
  /**
   * Set when any of stages 1-7 served a cached example: shown on the Factory Pack and the Launch Dossier cover
   */
  cached_note: string | null;
  /**
   * Stages 1-7 that served a cached example
   */
  fallback_stages: number[];
  product_name: string;
  product_summary: string;
  product_summary_cn: string | null;
  target_markets: string[];
  spec: StructuredSpec;
  cad_files: CadFile[];
  bom: BOMItem[];
  dfm_alerts: DFMIssue[];
  certifications: Certification[];
  target_quantities: number[];
  cost_estimate: CostTier[];
  questions: FactoryQuestion[];
  assumption_register: Assumption[];
  engineering: EngineeringArtifact | null;
  drawings: DrawingSheet[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "StructuredSpec".
 */
export interface StructuredSpec {
  overall_dimensions: Dimensions;
  weight: LabeledValue;
  parts: SpecPart[];
  tolerances: string[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FactoryQuestion".
 */
export interface FactoryQuestion {
  id: string;
  en: string;
  cn: string | null;
  cn_review_note: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "EngineeringArtifact".
 */
export interface EngineeringArtifact {
  project_id: string;
  status: StageStatus;
  /**
   * True when served from a fixture after an error
   */
  fallback: boolean;
  fallback_reason: string | null;
  /**
   * 'fixture' | 'code' | 'llm:<model slug>'
   */
  generated_by: string;
  generated_at: string;
  assumptions: Assumption[];
  stage: "engineering";
  /**
   * Engineering category key, e.g. wearable, furniture_baby, home_robot, vacuum, irrigation, solar_roof, surfboard, lighting, tracker, generic
   */
  category: string;
  category_title: string;
  partner_word: "factories" | "installers";
  site_install: boolean;
  product_name: string;
  /**
   * Hash of the project state this was computed from
   */
  inputs_digest: string;
  standards: StandardRef[];
  risks: DesignRisk[];
  tests: RequiredTest[];
  checks: EngineeringCheck[];
  electronics: ElectronicsArchitecture | null;
  firmware: FirmwareProject | null;
  prototype: PrototypePath;
  solar: SolarDesign | null;
  /**
   * Site-install mode: fictional certified installers
   */
  installers: InstallerMatch[];
  /**
   * W21: full design / module assembly / ODM customisation
   */
  build_strategy: BuildStrategy | null;
  /**
   * W21b: what one 'unit' is for this product — per_installation for site installs (rooftop solar): costs are per site
   */
  unit_basis: "per_unit" | "per_installation";
  /**
   * W21b: turnkey cost of one installation (per_installation only; = solar.install_cost)
   */
  installation_cost: LabeledValue | null;
  /**
   * C2 (CAD_ASSEMBLY=1): assembly tree, joints, measured interference / clearance / fastener checks (also in `checks`, domain 'assembly'); travels into the Factory Pack with `FactoryPack.engineering`
   */
  assembly: ProjectAssembly | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "StandardRef".
 */
export interface StandardRef {
  /**
   * e.g. 'IEC 60335-2-2', 'EN 12221-1', 'IEC 60529'
   */
  code: string;
  title: string;
  applies_because: string;
  url: string | null;
  citation_label: Label;
  citation_note: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DesignRisk".
 */
export interface DesignRisk {
  id: string;
  risk: string;
  mitigation: string;
  severity: Severity;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "RequiredTest".
 */
export interface RequiredTest {
  id: string;
  /**
   * e.g. 'Drop test 1.5 m', 'IPX7 immersion', 'Salt spray 96 h', 'Tip-over'
   */
  name: string;
  kind:
    | "drop"
    | "ingress"
    | "salt_spray"
    | "tip_over"
    | "thermal"
    | "electrical"
    | "radio"
    | "mechanical"
    | "battery"
    | "chemical"
    | "other";
  method: string;
  standard: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "EngineeringCheck".
 */
export interface EngineeringCheck {
  id: string;
  name: string;
  domain:
    | "stability"
    | "hydrodynamics"
    | "power"
    | "ingress"
    | "airflow"
    | "fluid"
    | "solar"
    | "thermal"
    | "mass"
    | "geometry"
    | "flight"
    | "regulatory"
    | "assembly";
  value: LabeledValue;
  /**
   * Human wording of the pass/warn/fail rule, e.g. '≥ 15° (design target)'
   */
  threshold: string | null;
  verdict: CheckVerdict;
  /**
   * Formula and assumptions, with the inputs' labels
   */
  formula: string;
  /**
   * Inputs of the formula (each labeled)
   */
  inputs: LabeledValue[];
  /**
   * e.g. the sealing checklist of an IP check
   */
  notes: string[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ElectronicsArchitecture".
 */
export interface ElectronicsArchitecture {
  mcu_family: "nrf52" | "esp32" | "stm32" | "avr" | "generic";
  mcu_part: string;
  radio: string[];
  power_tree: PowerNode[];
  connections: NetConnection[];
  power_budget: PowerBudgetLine[];
  average_current: LabeledValue;
  battery_voltage: LabeledValue | null;
  battery_capacity: LabeledValue | null;
  battery_life: LabeledValue | null;
  pcb_note: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PowerNode".
 */
export interface PowerNode {
  id: string;
  name: string;
  kind: "source" | "charger" | "storage" | "regulator" | "load";
  /**
   * Upstream node id (None for a source)
   */
  parent: string | null;
  voltage: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "NetConnection".
 */
export interface NetConnection {
  source: string;
  target: string;
  bus: "power" | "i2c" | "spi" | "uart" | "gpio" | "pwm" | "adc" | "rf" | "usb" | "analog" | "can";
  /**
   * Net names, e.g. 'SDA, SCL, INT1'
   */
  signals: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PowerBudgetLine".
 */
export interface PowerBudgetLine {
  block: string;
  part: string;
  active_current: LabeledValue;
  sleep_current: LabeledValue;
  duty_cycle: LabeledValue;
  average_current: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FirmwareProject".
 */
export interface FirmwareProject {
  framework: "zephyr" | "arduino";
  mcu_family: string;
  /**
   * e.g. 'BLE GATT service', 'Wi-Fi + MQTT'
   */
  connectivity: string;
  /**
   * /files/<project_id>/firmware.zip
   */
  url: string;
  files: string[];
  /**
   * 'template' | 'llm:<model slug>'
   */
  generated_by: string;
  note: string;
  /**
   * An LLM version is being generated in the background; re-GET to pick it up
   */
  pending_llm: boolean;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PrototypePath".
 */
export interface PrototypePath {
  enclosure_method: string;
  enclosure_volume: LabeledValue;
  /**
   * Prototype quantity (input)
   */
  units: number;
  cost_lines: PrototypeCostLine[];
  devkit_bom: DevKitLine[];
  assembly_steps: string[];
  timeline_weeks: LabeledValue;
  total_cost: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PrototypeCostLine".
 */
export interface PrototypeCostLine {
  item: string;
  amount: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DevKitLine".
 */
export interface DevKitLine {
  part: string;
  role: string;
  qty: number;
  lcsc_pn: string | null;
  unit_price: LabeledValue;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "SolarDesign".
 */
export interface SolarDesign {
  location: string;
  latitude: number;
  longitude: number;
  /**
   * True when the location was not in the prompt (default demo site)
   */
  location_assumed: boolean;
  roof_area: LabeledValue;
  module_power: LabeledValue;
  module_count: LabeledValue;
  peak_power: LabeledValue;
  specific_yield: LabeledValue;
  annual_energy: LabeledValue;
  /**
   * 12 values, kWh
   */
  monthly_energy: LabeledValue[];
  install_cost: LabeledValue;
  annual_savings: LabeledValue;
  payback: LabeledValue;
  pvgis_url: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "InstallerMatch".
 */
export interface InstallerMatch {
  factory_id: string;
  /**
   * Fictional installer name — ends with '(fictional)'
   */
  name: string;
  region: string;
  certifications: string[];
  lead_time_days: number;
  label: "fictional";
}
/**
 * W21: how this product realistically gets built — design everything, assemble bought-in modules, or customise an
 * ODM reference platform. Figures are Estimates with their assumptions.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "BuildStrategy".
 */
export interface BuildStrategy {
  strategy: "full_design" | "module_assembly" | "odm_customization";
  /**
   * e.g. 'Full design', 'Module assembly', 'ODM customisation'
   */
  title: string;
  explanation: string;
  /**
   * What the founder designs / chooses
   */
  customisable: string[];
  /**
   * What comes from the modules / the ODM platform
   */
  not_customisable: string[];
  moq: LabeledValue;
  entry_cost: LabeledValue;
  lead_time: LabeledValue;
  /**
   * Realistic steps (for ODM: find a close reference platform…)
   */
  path: string[];
  certifications_note: string;
  assumptions: string[];
}
/**
 * GET /projects/{id}/assembly?version=n — parts connected by build123d joints, with measured assembly checks.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProjectAssembly".
 */
export interface ProjectAssembly {
  project_id: string;
  version: number;
  label: string;
  /**
   * STEP the solids were read from, e.g. /files/<pid>/model_v2.step
   */
  source: string;
  /**
   * part_id of the assembly root
   */
  root: string;
  nodes: AssemblyNode[];
  joints: AssemblyJoint[];
  /**
   * Every overlapping pair > 0.01 mm³, classified
   */
  interferences: AssemblyInterference[];
  clearances: AssemblyClearance[];
  /**
   * Fastener BOM lines aggregated by designation (ids 'fx<n>'; Estimate price unless LCSC-matched → Sourced)
   */
  fasteners: BOMItem[];
  /**
   * domain 'assembly'
   */
  checks: EngineeringCheck[];
  /**
   * One line, e.g. '28 parts · 27 joints (3 moving) · 0 interferences · 16 fasteners'
   */
  summary: string;
  /**
   * Assembly engine version (cache key)
   */
  engine: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AssemblyNode".
 */
export interface AssemblyNode {
  /**
   * = PartMeta.part_id of the version GLB
   */
  part_id: string;
  name: string;
  role: string;
  /**
   * Parent part_id (None = assembly root)
   */
  parent: string | null;
  joint_id: string | null;
  /**
   * Parts with the same number move together (connected by rigid joints)
   */
  rigid_body: number;
  volume: LabeledValue;
  /**
   * Unit vector, GLB axes; derived from the joint
   *
   * @minItems 3
   * @maxItems 3
   */
  explode_vector: [number, number, number];
  /**
   * Cumulative along the tree (a child moves with its parent)
   */
  explode_distance_mm: number;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AssemblyJoint".
 */
export interface AssemblyJoint {
  id: string;
  /**
   * part_id of the parent (the part that carries the joint)
   */
  parent: string;
  /**
   * part_id placed by the joint
   */
  child: string;
  /**
   * build123d RigidJoint / RevoluteJoint / LinearJoint
   */
  kind: "rigid" | "revolute" | "linear";
  method: "screwed" | "snap_fit" | "inlay" | "press_fit" | "bonded" | "clip" | "hinge" | "bearing" | "slide" | "latch";
  /**
   * Degrees of freedom of the child relative to the parent (0 rigid, 1 revolute / linear)
   */
  dof: number;
  /**
   * Joint origin, mm, GLB axes (+Y up)
   *
   * @minItems 3
   * @maxItems 3
   */
  origin_mm: [number, number, number];
  /**
   * Unit joint axis, GLB axes
   */
  axis: [number, number, number] | null;
  /**
   * Motion range: deg (revolute) or mm (linear)
   */
  range: [number, number] | null;
  fasteners: FastenerUse[];
  /**
   * Why this mate: the family / role rule that inferred it
   */
  rule: string;
}
/**
 * One fastener kind used at a joint (screw + its insert are two rows).
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "FastenerUse".
 */
export interface FastenerUse {
  kind: "screw" | "insert" | "spring_bar" | "pin" | "nut" | "washer";
  /**
   * e.g. 'ISO 14583 (hexalobular pan head)', 'Heat-set brass insert'
   */
  standard: string;
  /**
   * e.g. 'M2.5×8', 'M2.5×4.0'
   */
  designation: string;
  /**
   * Thread / nominal size, e.g. 'M2.5'
   */
  size: string;
  length_mm: number;
  qty: number;
  /**
   * 'api.cad.stdparts' (C1 catalogue) or 'built-in table' (C2 fallback)
   */
  source: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AssemblyInterference".
 */
export interface AssemblyInterference {
  a: string;
  b: string;
  volume: LabeledValue;
  /**
   * interference = parts that move relative to each other (different rigid bodies, not joint partners) or the two shells of a parting line overlap → fail; joint_seat = overlap between the two parts of one joint (seat / insertion depth of concept geometry); static_overlap = parts of one rigid body interpenetrate (concept geometry, pocket at detail design)
   */
  kind: "interference" | "joint_seat" | "static_overlap";
  note: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AssemblyClearance".
 */
export interface AssemblyClearance {
  /**
   * Moving part (or the smaller part of an adjacent pair)
   */
  part_id: string;
  against: string;
  min_clearance: LabeledValue;
  /**
   * e.g. 'revolute 0-360° (12 steps)', 'linear 0-0.8 mm', 'static'
   */
  motion: string;
  verdict: CheckVerdict;
  rule: string;
}
/**
 * C3 (additive): one 2D technical drawing sheet of a version — GET /projects/{id}/drawings?version=n (CAD_DRAWINGS=1).
 * Orthographic views (first angle) + isometric, dimensions measured on the STEP, ISO 2768-m title block.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "DrawingSheet".
 */
export interface DrawingSheet {
  /**
   * Sheet id within the version: 'A1' assembly, 'P01'… parts, 'M01'… moulded shells (DFM model)
   */
  sheet: string;
  kind: "assembly" | "part" | "moulded";
  /**
   * GLB part_id (PartMeta.part_id) drawn on a part sheet; None on the assembly
   */
  part_id: string | null;
  title: string;
  /**
   * /files/<pid>/drawings/v<n>_<sheet>.svg
   */
  svg_url: string;
  /**
   * /files/<pid>/drawings/v<n>_<sheet>.pdf (vector, one page)
   */
  pdf_url: string;
  /**
   * /files/<pid>/drawings/v<n>_set.pdf — every sheet of the version, one PDF
   */
  set_pdf_url: string;
  version: number;
  size: "A3" | "A4";
  /**
   * Scale of the orthographic views, ISO 5455 standard, e.g. '1:2'
   */
  scale: string;
  /**
   * Overall [x, y, z] measured on the STEP (Z up)
   *
   * @minItems 3
   * @maxItems 3
   */
  bbox_mm: [number, number, number];
  bom_item_id: string | null;
  qty: number;
  label: "measured";
  note: "Generated from CAD — verify before release";
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Factory".
 */
export interface Factory {
  id: string;
  /**
   * Fictional name — never a real factory
   */
  name: string;
  region: string;
  /**
   * e.g. 'cheap/slow', 'fast/expensive', 'balanced' (E_usines.md)
   */
  archetype: string;
  /**
   * Behaviour of its negotiation agent
   */
  personality: string | null;
  capacity: CapacityProfile;
  audit_notes: string[];
  past_performance: PastPerformance;
  label: "fictional";
  fictional: true;
  /**
   * W21b: partner kind for the portal filter — factory (makes parts / assembles), installer (site install, e.g. rooftop PV), integrator (integrates bought-in modules, e.g. drones / robots)
   */
  kind: "factory" | "installer" | "integrator";
}
/**
 * Mirrors MCP `register_capacity` input (PRD §10).
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "CapacityProfile".
 */
export interface CapacityProfile {
  processes: ProcessType[];
  materials: string[];
  moq: number;
  /**
   * Factory certifications, e.g. ISO 9001, BSCI
   */
  certifications: string[];
  lead_time_days: number;
  /**
   * Units per month
   */
  monthly_capacity: number;
  current_load_pct: number;
  label: "fictional";
  /**
   * W21: product categories the factory specialises in (engineering category keys, e.g. lighting, wearable, drone); empty = generalist. A specialist scores lower on process fit for other categories
   */
  categories: string[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PastPerformance".
 */
export interface PastPerformance {
  orders_completed: number;
  /**
   * None = no data yet (self-registered factory, no order on the network)
   */
  on_time_rate_pct: number | null;
  /**
   * None = no data yet
   */
  defect_rate_pct: number | null;
  /**
   * True for a factory with no completed order on the network: show 'no data yet'
   */
  no_data: boolean;
  label: "fictional";
}
/**
 * POST /factories — mirrors MCP `register_capacity` (PRD §10). The factory is Fictional — demo data.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "RegisterFactoryRequest".
 */
export interface RegisterFactoryRequest {
  /**
   * ' (fictional)' is appended if missing
   */
  name: string;
  region: string;
  /**
   * @minItems 1
   */
  processes: [ProcessType, ...ProcessType[]];
  materials: string[];
  moq: number;
  certifications: string[];
  lead_time_days: number;
  monthly_capacity: number;
  current_load_pct: number;
  archetype: string;
  personality: string | null;
}
/**
 * Progress of the background autorun (stages 1-7, or 1-13 + Factory Pack in autofill mode). Poll GET /projects/{id} every ~2 s.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AutorunStatus".
 */
export interface AutorunStatus {
  state: AutorunState;
  /**
   * Last stage the run goes to: 7 (default) or 13 (autofill: also auto-approves the recommended quote at stage 8 and builds the Factory Pack)
   */
  through: 7 | 13;
  /**
   * Stage being run while state == running
   */
  current_stage: number | null;
  completed_stages: number[];
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}
/**
 * Factory-portal view of one RFQ.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "RFQWithQuotes".
 */
export interface RFQWithQuotes {
  rfq: RFQ;
  product_name: string;
  quotes: Quote[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "CreateProjectRequest".
 */
export interface CreateProjectRequest {
  mode: ProjectMode;
  prompt: string;
  name: string | null;
  pasted_bom: string | null;
  /**
   * Force a cached example: 'desk_lamp' | 'tracker_card'
   */
  example: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "RunStageRequest".
 */
export interface RunStageRequest {
  /**
   * Stage-specific user inputs, e.g. {'answers': {...}} for 1, {'direction_id': 'd1'} for 3, {'approve': true} for 8
   */
  inputs: {
    [k: string]: unknown;
  };
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "UpdateStageRequest".
 */
export interface UpdateStageRequest {
  artifact:
    | BriefArtifact
    | DesignArtifact
    | SpecArtifact
    | DFMArtifact
    | CostsArtifact
    | ProductionPlanArtifact
    | MatchingArtifact
    | NegotiationArtifact
    | ToolingArtifact
    | QCArtifact
    | LogisticsArtifact
    | FinancingArtifact
    | BrandArtifact;
  /**
   * Also mark the stage validated
   */
  validate_stage: boolean;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "StageResult".
 */
export interface StageResult {
  project_id: string;
  stage: number;
  name: string;
  title: string;
  status: StageStatus;
  fallback: boolean;
  artifact:
    | BriefArtifact
    | DesignArtifact
    | SpecArtifact
    | DFMArtifact
    | CostsArtifact
    | ProductionPlanArtifact
    | MatchingArtifact
    | NegotiationArtifact
    | ToolingArtifact
    | QCArtifact
    | LogisticsArtifact
    | FinancingArtifact
    | BrandArtifact;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "StageSummary".
 */
export interface StageSummary {
  stage: number;
  name: string;
  title: string;
  status: StageStatus;
  fallback: boolean;
  updated_at: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProjectDetail".
 */
export interface ProjectDetail {
  project: Project;
  stages: StageSummary[];
  /**
   * None if autorun was never started
   */
  autorun: AutorunStatus | null;
  /**
   * True if any stage 1-7 serves a cached example (fallback: true)
   */
  has_fallback: boolean;
  /**
   * Stages (1-13) currently serving a cached example
   */
  fallback_stages: number[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AutorunResult".
 */
export interface AutorunResult {
  project_id: string;
  /**
   * Empty for the async 202 response
   */
  results: StageResult[];
  autorun: AutorunStatus | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ResetResult".
 */
export interface ResetResult {
  projects: Project[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "HealthResponse".
 */
export interface HealthResponse {
  status: "ok";
  version: string;
  llm_configured: boolean;
  models: {
    [k: string]: string | null;
  };
  /**
   * Stages with a live handler; others serve fixtures
   */
  registered_stages: number[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ErrorResponse".
 */
export interface ErrorResponse {
  detail: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "Version".
 */
export interface Version {
  n: number;
  /**
   * The founder's prompt ('Studio start' for version 1)
   */
  message: string;
  status: VersionStatus;
  created_at: string;
  finished_at: string | null;
  summary: string;
  changes: VersionChange[];
  preview: VersionPreview | null;
  /**
   * Plain-language reason when status == failed
   */
  error: string | null;
  /**
   * Stage artifacts reflect this version
   */
  is_current: boolean;
  /**
   * An AI concept render for this version is still running
   */
  render_pending: boolean;
  /**
   * AI DFM review / production plan still refreshing in the background
   */
  background_pending: boolean;
  /**
   * W21: the AI CAD model (text-to-CAD) of this version is still being generated; preview.glb_url / code_url are patched in when done
   */
  cad_pending: boolean;
  /**
   * W21: plain-language note on the AI CAD (e.g. fell back to the family)
   */
  cad_note: string | null;
  /**
   * W21c: LLM attempts the AI CAD program of this version took (0 = no AI CAD run)
   */
  cad_attempts: number;
  /**
   * W21c: self-repair rounds (attempts − 1 when it ended ok) — 'self-repaired N×'
   */
  cad_repairs: number;
  /**
   * W21e: colour, material, finish, shape or dimensions changed vs the previous version. False → the previous version's photos are carried over (copied, same labels) and no new photo is generated
   */
  look_changed: boolean;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "VersionChange".
 */
export interface VersionChange {
  area:
    | "color"
    | "material"
    | "shape"
    | "dimensions"
    | "feature"
    | "component"
    | "price"
    | "markets"
    | "requirement"
    | "certification"
    | "cost"
    | "performance";
  /**
   * Human wording, e.g. 'Colour', 'Pod height', 'Optical heart-rate sensor'
   */
  label: string;
  before: string | null;
  after: string | null;
  label_kind: Label;
  /**
   * W21b: on a 'Component added' change — structured supply risk + proposed cheaper in-stock alternative
   */
  risk: ComponentRiskSummary | null;
}
/**
 * W21b: structured risk of one part: level, reasons and the proposed alternative (None when the snapshot has none).
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ComponentRiskSummary".
 */
export interface ComponentRiskSummary {
  level: RiskLevel;
  reasons: string[];
  alternative: PartAlternative | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "VersionPreview".
 */
export interface VersionPreview {
  /**
   * Full-product GLB of this version (/files/<pid>/v<n>.glb)
   */
  glb_url: string | null;
  /**
   * AI concept render (illustrative, not the CAD); patched in later
   */
  render_url: string | null;
  /**
   * W21e: see CostsArtifact.unit_basis
   */
  unit_basis: "per_unit" | "per_installation";
  /**
   * W21e, per_installation only: THE customer price of one installation for this version (turnkey, battery included when the BOM has one) — the single source for the Studio strip, Overview and gallery card
   */
  installed_price: LabeledValue | null;
  /**
   * W21e, per_installation only: what one installation costs the installer (equipment + labour + site admin)
   */
  installer_cost: LabeledValue | null;
  /**
   * Measured on the built STEP (moulded parts)
   */
  dimensions: Dimensions | null;
  color_hex: string | null;
  color_name: string | null;
  material: string | null;
  finish: string | null;
  /**
   * rounded_box | puck | slab | wearable_band | ring, or a W21 product family (board, furniture, stick_vacuum, home_robot, irrigation, solar_array, drone, hair_dryer, camera, smartphone)
   */
  shape_family: string | null;
  unit_costs: VersionUnitCost[];
  top_factories: VersionFactory[];
  /**
   * '<market> <standard>' of the required certifications
   */
  certifications: string[];
  bom_count: number;
  /**
   * W21: the build123d program of this version's model (/projects/<pid>/cad/code/<k>): AI-written, or the parametric family seed when AI CAD is off / failed (see cad_label)
   */
  code_url: string | null;
  /**
   * W21: STEP of the model shown in glb_url (AI model when present)
   */
  step_url: string | null;
  /**
   * W21: 'AI-generated CAD (concept level) — geometry measured on the result' or 'Parametric family CAD (concept level) — …'
   */
  cad_label: string | null;
  /**
   * W21: llm:<model> | seed:<family> | previous_version | family:<name>
   */
  cad_source: string | null;
  /**
   * W27: AI product photos of this version (one per shot, newest wins). hero_studio, when present, is also render_url
   */
  photos: ProductPhoto[];
  /**
   * W29b: the look changed (part edit) and no hero_studio photo of the new look exists yet (no stored viewer / CAD reference, or the photo job has not finished): any photo shown is of an older look — say so. Cleared when a hero_studio photo of this version is attached
   */
  photo_stale: boolean;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "VersionUnitCost".
 */
export interface VersionUnitCost {
  quantity: number;
  /**
   * Ex-works unit cost, USD
   */
  value: number;
  label: Label;
  source_or_assumption: string | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "VersionFactory".
 */
export interface VersionFactory {
  /**
   * Fictional factory name
   */
  name: string;
  /**
   * 0-100 match score on demo data
   */
  score: number;
  label: "fictional";
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "RefineRequest".
 */
export interface RefineRequest {
  message: string;
}
/**
 * W21: one showcase project of the gallery (GET /examples). Opening it costs nothing: every stage is cached.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ExampleSummary".
 */
export interface ExampleSummary {
  /**
   * Project id, e.g. demo_whoop_kitesurf
   */
  id: string;
  slug: string;
  name: string;
  prompt: string;
  /**
   * Engineering category key
   */
  category: string;
  strategy: ("full_design" | "module_assembly" | "odm_customization") | null;
  /**
   * Concept render (illustrative) or None
   */
  hero_image_url: string | null;
  /**
   * 3D model of the current version
   */
  glb_url: string | null;
  one_line_result: string;
  unit_basis: "per_unit" | "per_installation";
  /**
   * W21b: headline cost — ex-works unit cost at the reference quantity (per_unit) or turnkey cost per installation
   */
  unit_cost: LabeledValue | null;
  versions: number;
  stages_done: number;
  tags: string[];
  /**
   * The project exists in the database (after POST /demo/reset)
   */
  seeded: boolean;
  /**
   * W27: honesty caption of hero_image_url
   */
  hero_image_label: string | null;
  /**
   * W27: hero_studio + lifestyle photos of the current version
   */
  photos: ProductPhoto[];
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "StudioAccepted".
 */
export interface StudioAccepted {
  version: number;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PhotoJob".
 */
export interface PhotoJob {
  state: "idle" | "running" | "done" | "failed";
  version: number | null;
  /**
   * Shots requested by this job
   */
  shots: string[];
  /**
   * Shots generated so far
   */
  done: string[];
  /**
   * Shots that failed (the previous photo, if any, is kept)
   */
  failed: string[];
  /**
   * Plain-language reason when a shot failed (e.g. image credits exhausted)
   */
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}
/**
 * GET /projects/{id}/photos — photos of the current version + the running / last photo job (poll every ~2 s).
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProjectPhotos".
 */
export interface ProjectPhotos {
  project_id: string;
  /**
   * Current Studio version (None: not a Studio project)
   */
  version: number | null;
  photos: ProductPhoto[];
  job: PhotoJob;
  /**
   * An image model + key are configured (else POSTs return 503)
   */
  configured: boolean;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PhotoAccepted".
 */
export interface PhotoAccepted {
  version: number;
  shots: string[];
}
/**
 * One editable parameter of a part (slider): POST /parts/{part_id}/edit {param, value} within [min, max].
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PartEditable".
 */
export interface PartEditable {
  /**
   * Family parameter (fp_*) or AI CAD program parameter name
   */
  param: string;
  /**
   * Human wording, e.g. 'Pod thickness'
   */
  label: string;
  min: number;
  max: number;
  step: number;
  /**
   * mm, pct …
   */
  unit: string;
  /**
   * Current value
   */
  value: number;
}
/**
 * W29: one part of a version's GLB. The GLB node named `part_id` carries this object as glTF `extras`.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PartMeta".
 */
export interface PartMeta {
  /**
   * Stable id within the version = GLB node name, e.g. 'shell_top', 'strap', 'u_ppg_1'
   */
  part_id: string;
  /**
   * Human name, e.g. 'Top shell', 'MAX30102 PPG sensor'
   */
  name: string;
  role:
    | "shell_top"
    | "shell_bottom"
    | "strap"
    | "button"
    | "window"
    | "lens"
    | "diffuser"
    | "frame"
    | "arm"
    | "prop"
    | "motor"
    | "pcb"
    | "component"
    | "battery"
    | "antenna"
    | "connector"
    | "cable"
    | "fastener"
    | "other";
  /**
   * Anatomy layer this part belongs to (see ProjectAnatomy.layers)
   */
  layer_id: string;
  /**
   * Human material, e.g. 'PC/ABS', 'LSR silicone', 'FR-4'
   */
  material: string;
  /**
   * e.g. 'soft-touch matte', 'anodised', 'gloss'
   */
  finish: string | null;
  /**
   * #RRGGBB
   */
  colour_hex: string;
  /**
   * [x, y, z] extent in mm (GLB axes: +Y up)
   *
   * @minItems 3
   * @maxItems 3
   */
  measured_bbox_mm: [number, number, number];
  /**
   * [x, y, z] bbox centre in mm (GLB axes)
   *
   * @minItems 3
   * @maxItems 3
   */
  centroid_mm: [number, number, number];
  /**
   * measured = geometry measured on our CAD; estimate = illustrative anatomy body (package table / sizing rule)
   */
  label: "measured" | "estimate";
  /**
   * BOM line this part stands for (stage 3 bom[].id)
   */
  bom_item_id: string | null;
  lcsc_pn: string | null;
  /**
   * Package string used for the body size, e.g. 'LGA-14', 'USB-C'
   */
  package: string | null;
  unit_price: LabeledValue | null;
  editable: PartEditable[];
  colour_editable: boolean;
  /**
   * Material keys accepted by POST /parts/{id}/edit
   */
  material_options: string[];
  /**
   * C2 (CAD_ASSEMBLY=1): parent in the assembly tree
   */
  parent_part_id: string | null;
  /**
   * C2: joint to the parent
   */
  joint: ("rigid" | "revolute" | "linear") | null;
  /**
   * C2: unit vector (GLB axes) derived from the joint; move the part node by explode_vector × explode_distance_mm
   */
  explode_vector: [number, number, number] | null;
  /**
   * C2: cumulative along the assembly tree
   */
  explode_distance_mm: number | null;
}
/**
 * GET /projects/{id}/parts?version=n
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProjectParts".
 */
export interface ProjectParts {
  version: number;
  /**
   * The version's full-product GLB (= preview.glb_url); one node per part
   */
  glb_url: string;
  parts: PartMeta[];
}
/**
 * POST /projects/{id}/parts/{part_id}/edit — deterministic refine (no LLM). At least one field.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "PartEditRequest".
 */
export interface PartEditRequest {
  colour_hex: string | null;
  /**
   * One of PartMeta.material_options
   */
  material: string | null;
  finish: string | null;
  /**
   * One of PartMeta.editable[].param (requires value)
   */
  param: string | null;
  value: number | null;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AnatomyLayer".
 */
export interface AnatomyLayer {
  id: string;
  name: string;
  /**
   * 0 = outermost / first to lift
   */
  order: number;
  /**
   * part_ids (nodes of the anatomy GLB)
   */
  parts: string[];
  /**
   * Unit vector, GLB axes (+Y up)
   *
   * @minItems 3
   * @maxItems 3
   */
  explode_vector: [number, number, number];
  explode_distance_mm: number;
  caption: string;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AnatomyCamera".
 */
export interface AnatomyCamera {
  /**
   * @minItems 3
   * @maxItems 3
   */
  position_mm: [number, number, number];
  /**
   * @minItems 3
   * @maxItems 3
   */
  target_mm: [number, number, number];
  fov_deg: number;
}
/**
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AnatomyStep".
 */
export interface AnatomyStep {
  id: string;
  title: string;
  /**
   * e.g. '01 · The band'
   */
  kicker: string;
  /**
   * One line with real BOM / engineering values and their labels
   */
  caption: string;
  camera: AnatomyCamera;
  layers_exploded: string[];
  focus_parts: string[];
}
/**
 * GET /projects/{id}/anatomy?version=n — illustrative internal layout generated from the BOM (deterministic).
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "ProjectAnatomy".
 */
export interface ProjectAnatomy {
  version: number;
  /**
   * Companion anatomy GLB /files/<pid>/anatomy_v<n>.glb (exterior parts + internals)
   */
  glb_url: string;
  label: "Illustrative internal layout — not a routed PCB";
  /**
   * construction = solid product (board, furniture): layers are construction layers, not a PCB
   */
  kind: "electronics" | "construction";
  /**
   * [x, y, z] of the whole product, GLB axes
   *
   * @minItems 3
   * @maxItems 3
   */
  bbox_mm: [number, number, number];
  layers: AnatomyLayer[];
  steps: AnatomyStep[];
  /**
   * Every node of the anatomy GLB
   */
  parts: PartMeta[];
}
