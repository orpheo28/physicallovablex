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
 * via the `definition` "AutorunState".
 */
export type AutorunState = "idle" | "running" | "done" | "failed";

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
  format: "step" | "stl" | "glb" | "pdf" | "png" | "svg";
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
   * 500 / 2,000 / 10,000 by default
   *
   * @minItems 3
   */
  tiers: [CostTier, CostTier, CostTier, ...CostTier[]];
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
 * Progress of the background autorun (stages 1-7). Poll GET /projects/{id} every ~2 s.
 *
 * This interface was referenced by `ContractsBundle`'s JSON-Schema
 * via the `definition` "AutorunStatus".
 */
export interface AutorunStatus {
  state: AutorunState;
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
