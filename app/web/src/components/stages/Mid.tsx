"use client";

import Link from "next/link";
import { useState } from "react";
import type { CostsArtifact, DFMArtifact, FactoryMatch, MatchingArtifact, ProductionPlanArtifact } from "@/types/contracts";
import type { SpecArtifact } from "@/types/contracts";
import { humanize } from "@/lib/meta";
import { useApi } from "@/lib/useApi";
import { BreakEven, CertificationsByMarket, IssuesTable, StackedBar, TiersTable } from "../blocks";
import { Btn, Card, KV, LabelBadge, LV, Severity, Spinner, StatStrip, Table, Td, Th } from "../ui";
import type { StageViewProps } from "./types";

// ---------------------------------------------------------------- Stage 4
export function DFMView({ artifact: a }: StageViewProps<DFMArtifact>) {
  const measured = a.issues.filter((i) => i.method === "measured").length;
  const open = a.issues.filter((i) => !i.resolved).length;
  const high = a.issues.filter((i) => i.severity === "critical" || i.severity === "major" || (i.severity as string) === "high").length;
  return (
    <div className="flex flex-col gap-6">
      <StatStrip
        items={[
          { label: "DFM alerts", value: <span className="font-mono text-xl">{a.issues.length}</span>, sub: `${open} open` },
          {
            label: "Measured on the CAD",
            value: (
              <span className="flex items-center gap-2.5">
                <span className="font-mono text-xl">{measured}</span>
                <LabelBadge label="measured" small />
              </span>
            ),
            sub: `${a.issues.length - measured} AI-reviewed`,
          },
          { label: "Critical or major", value: <span className="font-mono text-xl">{high}</span> },
          { label: "Certifications", value: <span className="font-mono text-xl">{a.certifications.length}</span>, sub: `${new Set(a.certifications.map((c) => c.market)).size} markets` },
        ]}
      />
      <Card
        title={
          <>
            DFM alerts <span className="font-mono text-ink-3">{a.issues.length}</span>
          </>
        }
        right={
          <span>
            {measured} measured on the CAD, {a.issues.length - measured} AI-reviewed
          </span>
        }
      >
        <IssuesTable issues={a.issues} />
      </Card>
      <Card title={<>Component risks <span className="font-mono text-ink-3">{a.component_risks.length}</span></>}>
        {a.component_risks.length === 0 ? (
          <p className="text-base text-ink-3">No risky components flagged.</p>
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Part</Th>
                <Th>Risk</Th>
                <Th>Reasons</Th>
                <Th>Stock</Th>
                <Th>Lead time</Th>
                <Th>Alternatives</Th>
              </tr>
            </thead>
            <tbody>
              {a.component_risks.map((r) => (
                <tr key={r.bom_item_id + r.part}>
                  <Td className="font-medium">{r.part}</Td>
                  <Td>
                    <Severity level={r.level} />
                  </Td>
                  <Td className="text-ink-2">{r.reasons.join(", ")}</Td>
                  <Td>
                    <LV v={r.stock} />
                  </Td>
                  <Td>
                    <LV v={r.lead_time_weeks} />
                  </Td>
                  <Td className="text-sm text-ink-2">{r.alternatives.join(", ") || "—"}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
      <Card title="Certifications by market">
        <CertificationsByMarket certs={a.certifications} />
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- Stage 5
export function CostsView({ artifact: a, busy, run, project }: StageViewProps<CostsArtifact>) {
  // Cost lines rarely carry `stock`; the LCSC stock lives in the stage-3 BOM risk notes ("Stock 1.09M").
  const spec = useApi<{ artifact: SpecArtifact }>(`/projects/${project.id}/stages/3`);
  const stockText: Record<string, string> = {};
  for (const b of spec.data?.artifact?.bom ?? []) {
    const m = b.risk?.reasons.map((r) => /^stock\s+(.+)$/i.exec(r)).find(Boolean);
    if (m) stockText[b.id] = m[1];
  }
  const [vols, setVols] = useState(a.tiers.map((t) => String(t.quantity)).join(", "));
  const [factor, setFactor] = useState(String(a.volume_factor.value));
  const [ref, setRef] = useState(String(a.reference_quantity));
  const [err, setErr] = useState<string | null>(null);

  function recompute() {
    const volumes = vols
      .split(/[,\s]+/)
      .map((v) => parseInt(v.replace(/[^\d]/g, ""), 10))
      .filter((v) => v > 0);
    const vf = parseFloat(factor);
    const rq = parseInt(ref, 10);
    if (volumes.length < 3) return setErr("Enter at least 3 volumes.");
    if (!(vf > 0 && vf <= 1.5)) return setErr("Volume factor must be between 0 and 1.5.");
    setErr(null);
    const inputs: Record<string, unknown> = { volumes, volume_factor: vf };
    if (rq > 0) inputs.reference_quantity = rq;
    run(inputs);
  }

  return (
    <div className="flex flex-col gap-6">
      <StatStrip
        items={[
          { label: "Total cash needed", value: <LV v={a.total_cash_needed} big />, sub: `First order of ${a.reference_quantity.toLocaleString("en-US")} units`, accent: true },
          { label: "Break-even", value: <BreakEven v={a.breakeven_units} big /> },
          { label: "Target retail price", value: <LV v={a.target_retail_price} big /> },
          {
            label: "Tooling · certification",
            value: (
              <span className="flex flex-col gap-1 text-base">
                <span className="flex items-center justify-between gap-2">
                  <span className="text-ink-2">Tooling</span> <LV v={a.tooling_total} />
                </span>
                <span className="flex items-center justify-between gap-2">
                  <span className="text-ink-2">Certification</span> <LV v={a.certification_total} />
                </span>
              </span>
            ),
          },
        ]}
      />

      <Card title="Unit cost by volume tier">
        <TiersTable tiers={a.tiers} />
        <div className="mt-5 flex flex-wrap items-end gap-4 border-t border-line pt-5 text-base">
          <label className="flex flex-col gap-1.5">
            <span className="micro">Volumes</span>
            <input value={vols} onChange={(e) => setVols(e.target.value)} className="field !w-48 font-mono" />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="micro flex items-center gap-2">
              Volume factor <LabelBadge label={a.volume_factor.label} tip={a.volume_factor.source_or_assumption} small />
            </span>
            <input value={factor} onChange={(e) => setFactor(e.target.value)} className="field !w-24 font-mono" />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="micro">Reference quantity</span>
            <input value={ref} onChange={(e) => setRef(e.target.value)} className="field !w-28 font-mono" />
          </label>
          <Btn onClick={recompute} disabled={busy} className="!h-[36px]">
            {busy && <Spinner />} Recompute
          </Btn>
          {err && <span className="text-sm text-danger">{err}</span>}
        </div>
      </Card>

      <Card title="Cash needed — breakdown">
        <StackedBar parts={a.cash_breakdown} total={a.total_cash_needed} />
      </Card>

      <Card title={<>BOM lines <span className="font-mono text-ink-3">{a.bom_lines.length}</span></>}>
        <Table>
          <thead>
            <tr>
              <Th>Part</Th>
              <Th right>Qty / unit</Th>
              <Th>Unit price</Th>
              <Th>LCSC pn</Th>
              <Th>Stock</Th>
              <Th>Extended</Th>
            </tr>
          </thead>
          <tbody>
            {a.bom_lines.map((l) => (
              <tr key={l.bom_item_id}>
                <Td className="font-medium">{l.part}</Td>
                <Td right className="font-mono">{l.qty_per_unit}</Td>
                <Td>
                  <LV v={l.unit_price} />
                </Td>
                <Td className="font-mono text-sm text-ink-2">{l.lcsc_pn ?? "—"}</Td>
                <Td>
                  {l.stock ? (
                    <LV v={l.stock} />
                  ) : stockText[l.bom_item_id] ? (
                    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1" title="LCSC stock snapshot (from the BOM risk note)">
                      <span className="font-mono">{stockText[l.bom_item_id]}</span>
                      <LabelBadge label="sourced" tip="LCSC stock snapshot, see the BOM risk note in stage 3" small />
                    </span>
                  ) : (
                    <span className="text-ink-4">—</span>
                  )}
                </Td>
                <Td>
                  <LV v={l.extended} />
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card title="Tooling">
        <Table>
          <thead>
            <tr>
              <Th>Tool</Th>
              <Th>Process</Th>
              <Th>Cost</Th>
            </tr>
          </thead>
          <tbody>
            {a.tooling.map((t) => (
              <tr key={t.name}>
                <Td>{t.name}</Td>
                <Td>{humanize(t.process)}</Td>
                <Td>
                  <LV v={t.cost} />
                </Td>
              </tr>
            ))}
            <tr className="font-medium [&>td]:border-t [&>td]:border-t-line-2">
              <Td>Total</Td>
              <Td />
              <Td>
                <LV v={a.tooling_total} />
              </Td>
            </tr>
          </tbody>
        </Table>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- Stage 6
export function ProductionView({ artifact: a }: StageViewProps<ProductionPlanArtifact>) {
  return (
    <div className="flex flex-col gap-6">
      <Card title="Process per part" right={<span className="flex items-center gap-2">Total lead time <LV v={a.total_lead_time_days} /></span>}>
        <Table>
          <thead>
            <tr>
              <Th>Part</Th>
              <Th>Process</Th>
              <Th>Why</Th>
              <Th>Region</Th>
              <Th>Lead time</Th>
            </tr>
          </thead>
          <tbody>
            {a.steps.map((s, i) => (
              <tr key={s.part_id + i}>
                <Td className="font-medium">{s.part_name}</Td>
                <Td>
                  <span className="whitespace-nowrap font-medium">{humanize(s.process)}</span>
                </Td>
                <Td className="text-ink-2">{s.reason}</Td>
                <Td>{s.region}</Td>
                <Td>
                  <LV v={s.lead_time_days} />
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      {a.assembly_notes.length > 0 && (
        <Card title="Assembly notes">
          <ol className="flex flex-col">
            {a.assembly_notes.map((n, i) => (
              <li key={n} className="grid grid-cols-[32px_1fr] border-b border-line py-2 text-base last:border-b-0">
                <span className="font-mono text-sm text-ink-3">{i + 1}</span>
                {n}
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- Stage 7
export function MatchCard({ m, compact }: { m: FactoryMatch; compact?: boolean }) {
  return (
    <Card
      fictional
      title={
        <span className="flex items-center gap-2.5">
          <span className="font-mono text-sm text-ink-3">{String(m.rank).padStart(2, "0")}</span>
          <Link href={`/factories/${m.factory_id}`} className="transition-colors hover:text-accent-ink">
            {m.factory_name}
          </Link>
        </span>
      }
    >
      <div className="flex items-baseline justify-between gap-3" title={m.score.source_or_assumption}>
        <span className="micro">Match score</span>
        <span className="font-mono text-xl">
          {Math.round(m.score.value)}
          <span className="text-base text-ink-3">/100</span>
        </span>
      </div>
      {!compact && (
        <div className="mt-4 flex flex-col gap-3 border-t border-line pt-4">
          {m.score_breakdown.map((s) => (
            <div key={s.criterion} className="flex flex-col gap-1.5" title={s.note}>
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className="text-ink-2">{humanize(s.criterion)}</span>
                <span className="font-mono text-ink-3">
                  {s.score.toFixed(2)} × {s.weight}
                </span>
              </div>
              <span className="h-[3px] overflow-hidden rounded-full bg-paper-2">
                <span className="block h-full bg-ink" style={{ width: `${Math.round(s.score * 100)}%` }} />
              </span>
              <span className="text-sm text-ink-3">{s.note}</span>
            </div>
          ))}
        </div>
      )}
      <ul className="mt-4 flex flex-col gap-1 border-t border-line pt-4 text-base">
        {m.reasons.map((r) => (
          <li key={r} className="flex gap-2.5">
            <span className="mt-[11px] h-px w-2.5 shrink-0 bg-ink-3" aria-hidden />
            {r}
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function MatchingView({ artifact: a }: StageViewProps<MatchingArtifact>) {
  const list = [...a.shortlist].sort((x, y) => x.rank - y.rank);
  return (
    <div className="flex flex-col gap-6">
      <p className="flex flex-wrap items-center gap-2 text-base text-ink-2">
        Queried the production MCP with Factory Pack <span className="font-mono text-ink">{a.factory_pack_id}</span>. The factory network is
        <LabelBadge label="fictional" small />
      </p>
      <div className="grid gap-5 lg:grid-cols-3">
        {list.map((m) => (
          <MatchCard key={m.factory_id} m={m} />
        ))}
      </div>
      <Card title={<>Capacity queries sent <span className="font-mono text-sm font-normal text-ink-3">search_capacity</span></>}>
        <Table>
          <thead>
            <tr>
              <Th>Process</Th>
              <Th>Material</Th>
              <Th right>Quantity</Th>
              <Th>Certifications</Th>
              <Th>Deadline</Th>
            </tr>
          </thead>
          <tbody>
            {a.queries.map((q, i) => (
              <tr key={i}>
                <Td className="font-medium">{humanize(q.process)}</Td>
                <Td className="text-ink-2">{q.material}</Td>
                <Td right className="font-mono">{q.quantity.toLocaleString("en-US")}</Td>
                <Td className="text-ink-2">{q.certifications_required.join(", ") || "—"}</Td>
                <Td className="font-mono text-sm text-ink-2">{q.deadline ?? "—"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <KV k="Next">
        <span className="text-base text-ink-2">Stage 8 sends RFQs to the shortlist and negotiates.</span>
      </KV>
    </div>
  );
}
