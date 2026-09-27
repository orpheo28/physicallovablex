import type { Label, LabeledValue } from "@/types/contracts";

export const LABEL_TEXT: Record<Label, string> = {
  measured: "Measured",
  sourced: "Sourced",
  estimate: "Estimate",
  fictional: "Fictional — demo data",
};

export const LABEL_HELP: Record<Label, string> = {
  measured: "Computed on your CAD model, for example draft angles and undercuts.",
  sourced: "A real price or official rate, with its date.",
  estimate: "An assumption we show you, and you can change.",
  fictional: "Simulated for this demo: the factories, their quotes, freight rates.",
};

/** Trust-label pill: muted tint + ink of the same hue. */
export const LABEL_CLASS: Record<Label, string> = {
  measured: "bg-measured-soft text-measured-ink",
  sourced: "bg-sourced-soft text-sourced-ink",
  estimate: "bg-estimate-soft text-estimate-ink",
  fictional: "bg-fictional-soft text-fictional-ink",
};

/** Trust label printed as text next to its dot (legend, section headers). */
export const LABEL_INK: Record<Label, string> = {
  measured: "text-measured-ink",
  sourced: "text-sourced-ink",
  estimate: "text-estimate-ink",
  fictional: "text-fictional-ink",
};

/** The coloured trust-label dot. */
export const LABEL_DOT: Record<Label, string> = {
  measured: "bg-measured",
  sourced: "bg-sourced",
  estimate: "bg-estimate",
  fictional: "bg-fictional",
};

export type Layer = "Lovable" | "Core" | "Alibaba" | "Infra" | "Brand";

/** Layers are structure, not signal: neutral tinted tags (the accent is kept for the primary action and the current state). */
export const LAYER_CLASS: Record<Layer, string> = {
  Lovable: "bg-paper-2 text-ink-2",
  Core: "bg-paper-2 text-ink",
  Alibaba: "bg-paper-2 text-ink-2",
  Infra: "bg-paper-2 text-ink-2",
  Brand: "bg-paper-2 text-ink-2",
};

export type StageMeta = {
  n: number;
  name: string;
  /** Plain-language name, shown first everywhere. */
  title: string;
  /** The trade term, shown second (small). */
  jargon: string;
  layer: Layer;
  line: string;
  /** Stage header: what this step does / what you decide here. */
  does: string;
  decide: string;
  phase: number;
};

export const STAGES: StageMeta[] = [
  { n: 1, name: "brief", title: "Brief", jargon: "Product brief", layer: "Lovable", phase: 1, line: "an idea, or a prototype and its BOM.",
    does: "Turns your sentence into a product brief: what it is, who buys it, at what price and in what volumes.",
    decide: "Answer up to five quick questions, or skip them and keep the defaults." },
  { n: 2, name: "design", title: "Design options", jargon: "Industrial design", layer: "Lovable", phase: 1, line: "three directions to choose from.",
    does: "Proposes three design directions, each with a shape, material, finish and size.",
    decide: "Pick the direction to engineer. The 3D model is built from it." },
  { n: 3, name: "cad_spec", title: "3D model & spec", jargon: "CAD + spec", layer: "Lovable", phase: 1, line: "a 3D model and an editable spec, STEP included.",
    does: "Generates the 3D model (STEP, STL, GLB), the parts list, the BOM and an editable spec.",
    decide: "Check dimensions, materials and tolerances. Edit anything that is off." },
  { n: 4, name: "dfm", title: "Manufacturability check", jargon: "DFM", layer: "Core", phase: 2, line: "manufacturing checks, measured on your CAD.",
    does: "Checks the CAD for what makes molding or assembly fail, flags risky components and lists certifications per market.",
    decide: "Accept the proposed fixes, or go back and change the design." },
  { n: 5, name: "costs", title: "Costs & investment", jargon: "Investment", layer: "Lovable", phase: 2, line: "unit cost at 500, 2,000 and 10,000 units, plus cash needed.",
    does: "Prices every BOM line (real LCSC prices where possible), then unit cost at three volumes, tooling and total cash needed.",
    decide: "Set the volumes and the first-order size you plan for." },
  { n: 6, name: "production_plan", title: "Production plan", jargon: "Process plan", layer: "Lovable", phase: 2, line: "how each part is made, and where.",
    does: "Chooses how each part is made (molding, CNC, PCBA…), in which region, and how long it takes.",
    decide: "Confirm the processes before factories are matched." },
  { n: 7, name: "matching", title: "Factory shortlist", jargon: "Factory matching", layer: "Alibaba", phase: 3, line: "a ranked shortlist from the factory network.",
    does: "Queries the simulated factory network and ranks the factories that fit your processes, volumes and certifications.",
    decide: "Review the top three before they are asked for quotes." },
  { n: 8, name: "negotiation", title: "Quotes & negotiation", jargon: "RFQ + negotiation", layer: "Infra", phase: 3, line: "agents request and compare quotes; you approve.",
    does: "Agents send the Factory Pack to the shortlist, collect quotes and counter on price, MOQ, lead time and terms.",
    decide: "Approve one quote, or pick another factory." },
  { n: 9, name: "tooling", title: "Tooling & samples", jargon: "T0 / T1 / golden sample", layer: "Infra", phase: 4, line: "milestones from first mold to golden sample.",
    does: "Plans the milestones from first mold (T0) to golden sample and mass production, with the payment schedule.",
    decide: "Check the dates fit your launch." },
  { n: 10, name: "qc", title: "Quality control", jargon: "QC · AQL", layer: "Infra", phase: 4, line: "an inspection plan built from your spec.",
    does: "Builds the inspection plan from your spec: AQL sample size, defect classes and inspection cost.",
    decide: "Confirm which defects are critical." },
  { n: 11, name: "logistics", title: "Shipping & duties", jargon: "Logistics · landed cost", layer: "Infra", phase: 4, line: "landed cost with duties by product code.",
    does: "Computes the landed cost per unit: freight options, duties by product code (HTS) and fees.",
    decide: "Pick the freight mode and the duty scenario." },
  { n: 12, name: "financing", title: "Cash plan", jargon: "Financing", layer: "Infra", phase: 4, line: "your cash curve, and the options to fund it.",
    does: "Turns the milestones into a cash curve and lists the ways to fund it.",
    decide: "Choose how to finance the first order." },
  { n: 13, name: "brand", title: "Brand & listing", jargon: "Brand + distribution", layer: "Brand", phase: 4, line: "name, packaging, landing copy, listing draft.",
    does: "Proposes names, packaging, landing-page copy and Shopify / Amazon listing drafts.",
    decide: "Pick the name, then download the Launch Dossier." },
];

/** The 13 stages in 4 named phases (left rail, autofill stepper). */
export const PHASES: { n: number; title: string; stages: number[] }[] = [
  { n: 1, title: "Design", stages: [1, 2, 3] },
  { n: 2, title: "Make it manufacturable", stages: [4, 5, 6] },
  { n: 3, title: "Source", stages: [7, 8] },
  { n: 4, title: "Launch", stages: [9, 10, 11, 12, 13] },
];

/** Rail label: plain name first, the trade term in brackets only where it is the word people search for. */
export function railName(n: number): string {
  return n === 4 ? "Manufacturability check (DFM)" : STAGES[n - 1]?.title ?? `Stage ${n}`;
}

export function isLabeledValue(v: unknown): v is LabeledValue {
  if (!v || typeof v !== "object") return false;
  const o = v as Record<string, unknown>;
  return typeof o.value === "number" && typeof o.unit === "string" && typeof o.label === "string" && "source_or_assumption" in o;
}

const CURRENCY: Record<string, string> = { USD: "$", EUR: "€", GBP: "£", CNY: "¥", RMB: "¥" };

export function fmtNumber(n: number, digits?: number): string {
  if (!Number.isFinite(n)) return String(n);
  const d = digits ?? (Math.abs(n) >= 1000 ? 0 : Math.abs(n) >= 100 ? 1 : Math.abs(n) % 1 === 0 ? 0 : 2);
  return n.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: 0 });
}

/** "$13.75", "12.5 %", "340 mm", "2,000 units" */
export function fmtValue(v: { value: number; unit: string }): string {
  const u = v.unit ?? "";
  if (CURRENCY[u]) {
    const d = Math.abs(v.value) >= 1000 ? 0 : 2;
    return `${CURRENCY[u]}${v.value.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d })}`;
  }
  if (u === "pct" || u === "%") return `${fmtNumber(v.value, 1)}%`;
  if (!u) return fmtNumber(v.value);
  const unit = Math.abs(v.value) === 1 && /^(days|weeks|months|hours|units|pieces|man-days)$/.test(u) ? u.slice(0, -1) : u;
  return `${fmtNumber(v.value)} ${unit}`;
}

export function humanize(key: string): string {
  const s = key
    .replace(/_/g, " ")
    .replace(/\bpct\b/, "%")
    .replace(/\busd\b/i, "USD")
    .replace(/\b(pcba|cnc|moq|hts|led|usb)\b/gi, (m) => m.toUpperCase());
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function fmtDate(s: string | null | undefined): string {
  if (!s) return "—";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export type StageArtifact = import("@/types/contracts").StageResult["artifact"];

/** A factory with no completed orders has no track record: show "No track record yet", never 0 %. */
export function hasTrackRecord(pp: { orders_completed?: number | null; on_time_rate_pct?: number | null; defect_rate_pct?: number | null; no_data?: boolean } | null | undefined): boolean {
  return !!pp && !pp.no_data && (pp.orders_completed ?? 0) > 0 && pp.on_time_rate_pct != null && pp.defect_rate_pct != null;
}
