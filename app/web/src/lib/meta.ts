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

/** The coloured dot inside a trust-label pill. */
export const LABEL_DOT: Record<Label, string> = {
  measured: "bg-measured",
  sourced: "bg-sourced",
  estimate: "bg-estimate",
  fictional: "bg-fictional",
};

export type Layer = "Lovable" | "Core" | "Alibaba" | "Infra" | "Brand";

/** Layers are structure, not signal: neutral tags, the Core carries the accent. */
export const LAYER_CLASS: Record<Layer, string> = {
  Lovable: "border-line-2 text-ink-2",
  Core: "border-accent/40 text-accent-ink",
  Alibaba: "border-line-2 text-ink-2",
  Infra: "border-line-2 text-ink-2",
  Brand: "border-line-2 text-ink-2",
};

export const STAGES: { n: number; name: string; title: string; layer: Layer; line: string }[] = [
  { n: 1, name: "brief", title: "Brief", layer: "Lovable", line: "an idea, or a prototype and its BOM." },
  { n: 2, name: "design", title: "Industrial design", layer: "Lovable", line: "three directions to choose from." },
  { n: 3, name: "cad_spec", title: "CAD + spec", layer: "Lovable", line: "a 3D model and an editable spec, STEP included." },
  { n: 4, name: "dfm", title: "DFM", layer: "Core", line: "manufacturing checks, measured on your CAD." },
  { n: 5, name: "costs", title: "Investment", layer: "Lovable", line: "unit cost at 500, 2,000 and 10,000 units, plus cash needed." },
  { n: 6, name: "production_plan", title: "Production plan", layer: "Lovable", line: "how each part is made, and where." },
  { n: 7, name: "matching", title: "Factory matching", layer: "Alibaba", line: "a ranked shortlist from the factory network." },
  { n: 8, name: "negotiation", title: "RFQ + negotiation", layer: "Infra", line: "agents request and compare quotes; you approve." },
  { n: 9, name: "tooling", title: "Tooling + samples", layer: "Infra", line: "milestones from first mold to golden sample." },
  { n: 10, name: "qc", title: "Quality control", layer: "Infra", line: "an inspection plan built from your spec." },
  { n: 11, name: "logistics", title: "Logistics", layer: "Infra", line: "landed cost with duties by product code." },
  { n: 12, name: "financing", title: "Financing", layer: "Infra", line: "your cash curve, and the options to fund it." },
  { n: 13, name: "brand", title: "Brand + distribution", layer: "Brand", line: "name, packaging, landing copy, listing draft." },
];

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
