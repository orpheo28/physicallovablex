"use client";

import type {
  BOMItem,
  CadFile,
  Certification,
  CostTier,
  DFMIssue,
  Dimensions,
  LabeledValue,
  SpecPart,
} from "@/types/contracts";
import { fileUrl } from "@/lib/api";
import { useFileExists } from "@/lib/useApi";
import { fmtValue, humanize } from "@/lib/meta";
import { KV, LabelBadge, LV, Pill, Severity, Spinner, Table, Td, Th } from "./ui";

export function DimsView({ d }: { d: Dimensions | null | undefined }) {
  if (!d) return <span className="text-ink-4">—</span>;
  const unit = d.length.unit === d.width.unit && d.width.unit === d.height.unit ? d.length.unit : null;
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
      {unit ? (
        <span className="whitespace-nowrap font-mono tabular-nums" title={d.length.source_or_assumption}>
          {fmtValue({ value: d.length.value, unit: "" })}
          <span className="px-1 text-ink-4">×</span>
          {fmtValue({ value: d.width.value, unit: "" })}
          <span className="px-1 text-ink-4">×</span>
          {fmtValue({ value: d.height.value, unit: "" })} <span className="text-ink-2">{unit}</span>
        </span>
      ) : (
        <>
          <LV v={d.length} noBadge /> <span className="text-ink-4">×</span> <LV v={d.width} noBadge /> <span className="text-ink-4">×</span>{" "}
          <LV v={d.height} noBadge />
        </>
      )}
      <LabelBadge label={d.length.label} tip={d.length.source_or_assumption} small />
    </span>
  );
}

export function FileLink({ file }: { file: CadFile }) {
  const url = fileUrl(file.url);
  const { checking, ok } = useFileExists(url);
  const name = file.url.split("/").pop();
  return (
    <div className="grid grid-cols-[44px_1fr] items-baseline gap-3 border-b border-line py-2 text-base last:border-b-0">
      <span className="font-mono text-2xs font-medium uppercase tracking-wider text-ink-3">{file.format}</span>
      <span className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-0.5">
        {checking ? (
          <span className="flex items-center gap-1.5 text-ink-3">
            <Spinner /> {name}
          </span>
        ) : ok && url ? (
          <a href={url} download={name} className="inline-flex items-center gap-1.5 font-medium text-ink underline decoration-line-2 underline-offset-4 transition-colors hover:decoration-ink">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
              <path d="M8 2v8.5M4.5 7 8 10.5 11.5 7M3 13.5h10" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {name}
          </a>
        ) : (
          <span className="text-ink-3">
            {name} · pending, not generated yet
          </span>
        )}
        {file.description && <span className="text-sm text-ink-2">{file.description}</span>}
      </span>
    </div>
  );
}

export function PartsTable({ parts }: { parts: SpecPart[] }) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Part</Th>
          <Th>Material / finish</Th>
          <Th>Process</Th>
          <Th>Dimensions (L × W × H)</Th>
          <Th>Wall</Th>
          <Th>Tolerance</Th>
          <Th right>Qty</Th>
        </tr>
      </thead>
      <tbody>
        {parts.map((p) => (
          <tr key={p.id}>
            <Td>
              <span className="font-medium">{p.name}</span> <span className="font-mono text-2xs text-ink-3">{p.id}</span>
            </Td>
            <Td>
              {p.material}
              <div className="text-sm text-ink-2">{p.finish}</div>
            </Td>
            <Td>{p.process_hint ? humanize(p.process_hint) : "—"}</Td>
            <Td>
              <DimsView d={p.dimensions} />
            </Td>
            <Td>
              <LV v={p.wall_thickness} />
            </Td>
            <Td className="text-sm text-ink-2">{p.tolerance ?? "—"}</Td>
            <Td right className="font-mono">{p.quantity}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function BOMTable({ items }: { items: BOMItem[] }) {
  if (!items.length) return <p className="text-base text-ink-3">No BOM lines.</p>;
  return (
    <Table>
      <thead>
        <tr>
          <Th>Part</Th>
          <Th>Category</Th>
          <Th right>Qty</Th>
          <Th>MPN / LCSC</Th>
          <Th>Unit cost</Th>
          <Th>Risk</Th>
          <Th>Alternative</Th>
        </tr>
      </thead>
      <tbody>
        {items.map((b) => (
          <tr key={b.id}>
            <Td>
              <span className="font-medium">{b.part}</span>
              {b.description && <div className="text-sm text-ink-2">{b.description}</div>}
            </Td>
            <Td>{b.category}</Td>
            <Td right className="font-mono">{b.qty}</Td>
            <Td className="font-mono text-sm">
              {b.manufacturer_pn ?? "—"}
              {b.lcsc_pn && <div className="text-ink-3">{b.lcsc_pn}</div>}
            </Td>
            <Td>
              <LV v={b.unit_cost_est} />
            </Td>
            <Td>
              {b.risk ? (
                <span title={b.risk.reasons.join("; ")}>
                  <Severity level={b.risk.level} />
                  {b.risk.reasons.length > 0 && <div className="text-sm text-ink-2">{b.risk.reasons.join(", ")}</div>}
                </span>
              ) : (
                "—"
              )}
            </Td>
            <Td className="text-sm text-ink-2">{b.alternative ?? "—"}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function MethodBadge({ method }: { method: string }) {
  return method === "measured" ? (
    <LabelBadge label="measured" tip="Geometry check computed on the CAD" small />
  ) : (
    <span
      className="inline-flex h-[18px] items-center gap-1.5 whitespace-nowrap rounded-full border border-line-2 px-1.5 text-[10.5px] font-medium text-ink-2"
      title="LLM review with a checklist prompt"
    >
      <span className="h-1.5 w-1.5 rounded-full border border-ink-3" aria-hidden />
      AI-reviewed
    </span>
  );
}

export function IssuesTable({ issues }: { issues: DFMIssue[] }) {
  if (!issues.length) return <p className="text-base text-ink-3">No DFM issues.</p>;
  return (
    <Table>
      <thead>
        <tr>
          <Th>Severity</Th>
          <Th>Method</Th>
          <Th>Issue</Th>
          <Th>Measurement</Th>
          <Th>Fix</Th>
          <Th>Rule</Th>
        </tr>
      </thead>
      <tbody>
        {issues.map((i) => (
          <tr key={i.id}>
            <Td>
              <Severity level={i.severity} />
            </Td>
            <Td>
              <MethodBadge method={i.method} />
            </Td>
            <Td>
              <span className="text-sm font-medium text-ink-2">
                {humanize(i.category)}
                {i.part_id ? <span className="font-mono text-2xs text-ink-3"> {i.part_id}</span> : ""}
              </span>
              <div>{i.description}</div>
              {i.resolved && <div className="mt-1 text-sm text-measured-ink">Resolved{i.resolution ? `: ${i.resolution}` : ""}</div>}
            </Td>
            <Td>
              <LV v={i.measurement} />
            </Td>
            <Td className="max-w-[280px] text-ink-2">{i.fix}</Td>
            <Td className="max-w-[220px] text-sm text-ink-3">{i.rule_citation}</Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function CertificationsByMarket({ certs }: { certs: Certification[] }) {
  if (!certs.length) return <p className="text-base text-ink-3">No certifications listed.</p>;
  const markets = Array.from(new Set(certs.map((c) => c.market)));
  return (
    <div className="grid gap-x-8 gap-y-6 md:grid-cols-2 xl:grid-cols-3">
      {markets.map((m) => (
        <div key={m}>
          <div className="flex items-baseline justify-between border-b border-line-2 pb-2">
            <span className="text-base font-medium">{m}</span>
            <span className="font-mono text-2xs text-ink-3">{certs.filter((c) => c.market === m).length}</span>
          </div>
          <ul className="divide-y divide-line">
            {certs
              .filter((c) => c.market === m)
              .map((c, i) => (
                <li key={i} className="py-3 text-base">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{c.standard}</span>
                    {!c.required && <Pill>optional</Pill>}
                  </div>
                  <div className="mt-0.5 text-sm text-ink-2">{c.applies_because}</div>
                  <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-2">
                    <span className="inline-flex items-center gap-2">
                      Cost <LV v={c.cost_est} />
                    </span>
                    <span className="inline-flex items-center gap-2">
                      Lead time <LV v={c.lead_time_weeks} />
                    </span>
                  </div>
                </li>
              ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

const TIER_ROWS: { key: keyof CostTier; label: string; strong?: boolean }[] = [
  { key: "bom_cost", label: "BOM cost" },
  { key: "assembly_cost", label: "Assembly" },
  { key: "packaging_cost", label: "Packaging" },
  { key: "unit_cost", label: "Unit cost (ex-works)", strong: true },
  { key: "tooling_amortisation", label: "Tooling amortisation" },
  { key: "margin_pct", label: "Margin at target price", strong: true },
];

export function TiersTable({ tiers }: { tiers: CostTier[] }) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Per unit</Th>
          {tiers.map((t) => (
            <Th key={t.quantity} right>
              {t.quantity.toLocaleString("en-US")} units
            </Th>
          ))}
        </tr>
      </thead>
      <tbody>
        {TIER_ROWS.map((r) => (
          <tr key={r.key} className={r.strong ? "[&>td]:border-t [&>td]:border-t-line-2" : ""}>
            <Td className={r.strong ? "font-medium" : "text-ink-2"}>{r.label}</Td>
            {tiers.map((t) => (
              <Td key={t.quantity} right>
                <LV v={t[r.key] as LabeledValue} />
              </Td>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

/** Palette for part-of-whole bars: ink, accent, then warm neutrals and two muted hues. */
export const SERIES = ["#111111", "#FF4F00", "#8A8883", "#3F5E7C", "#C9C5BC", "#B7793F", "#5C5B57", "#7C8F6A", "#E3DFD6", "#9A6B8F"];

/** Horizontal stacked bar for components that sum to a total (cash breakdown, landed cost). */
export function StackedBar({ parts, total }: { parts: { name: string; amount: LabeledValue }[]; total?: LabeledValue }) {
  const sum = parts.reduce((s, p) => s + Math.max(0, p.amount.value), 0) || 1;
  return (
    <div className="flex flex-col gap-5">
      <div className="flex h-3 w-full gap-[2px] overflow-hidden rounded-sm">
        {parts.map((p, i) => (
          <div
            key={p.name + i}
            title={`${p.name}: ${fmtValue(p.amount)} — ${p.amount.source_or_assumption}`}
            style={{ width: `${(Math.max(0, p.amount.value) / sum) * 100}%`, background: SERIES[i % SERIES.length] }}
            className="h-full first:rounded-l-sm last:rounded-r-sm"
          />
        ))}
      </div>
      <ul className="grid gap-x-10 sm:grid-cols-2">
        {parts.map((p, i) => (
          <li key={p.name + i} className="flex items-center gap-3 border-b border-line py-2 text-base">
            <span className="inline-block h-2 w-2 shrink-0 rounded-[1px]" style={{ background: SERIES[i % SERIES.length] }} />
            <span className="flex-1 text-ink-2">{p.name}</span>
            <LV v={p.amount} />
            <span className="w-10 text-right font-mono text-sm text-ink-3" title={`Share of total — derived from the ${p.amount.label} amount`}>
              {((Math.max(0, p.amount.value) / sum) * 100).toFixed(0)}%
            </span>
          </li>
        ))}
      </ul>
      {total && (
        <div className="flex items-center justify-end gap-3 text-base font-medium">
          <span className="text-ink-2">Total</span> <LV v={total} />
        </div>
      )}
    </div>
  );
}

export { KV };

/** Break-even units; when the cost engine says it cannot be reached, say so — never "0 units". */
export function BreakEven({ v, big }: { v: LabeledValue | null | undefined; big?: boolean }) {
  if (v && v.source_or_assumption.trim().toUpperCase().startsWith("NOT REACHABLE")) {
    return (
      <span className="inline-flex flex-col gap-1" title={v.source_or_assumption}>
        <span className={`inline-flex items-center gap-2 font-medium text-danger ${big ? "text-lg" : "text-base"}`}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
            <path d="M8 1.8 15 14H1L8 1.8Z" strokeLinejoin="round" />
            <path d="M8 6.5v3.3M8 11.8v.2" strokeLinecap="round" />
          </svg>
          Not reachable at this retail price
        </span>
        <span className="text-sm text-ink-2">{v.source_or_assumption.replace(/^NOT REACHABLE:\s*/i, "")}</span>
      </span>
    );
  }
  return <LV v={v} big={big} />;
}
