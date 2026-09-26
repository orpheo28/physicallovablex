"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { Factory, RFQWithQuotes } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { fmtDate, hasTrackRecord, humanize } from "@/lib/meta";
import { Card, Empty, ErrorBox, KV, LabelBadge, Loading, Pill, StatStrip, Table, Td, Th } from "@/components/ui";

export default function FactoryPage() {
  const { id } = useParams<{ id: string }>();
  const f = useApi<Factory>(`/factories/${id}`);
  const rfqs = useApi<RFQWithQuotes[]>(`/factories/${id}/rfqs`);
  const fac = f.data;

  return (
    <div className="mx-auto max-w-[1320px] px-6 pt-8 lg:px-10">
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm text-ink-3">
        <Link href="/factories" className="transition-colors hover:text-ink">
          Factory portal
        </Link>
        <span aria-hidden>/</span>
        <span className="text-ink-2">{fac?.name ?? id}</span>
      </nav>
      {f.error && !fac && (
        <div className="mt-6">
          <ErrorBox message={f.status === 404 ? `Factory “${id}” not found.` : `Could not load the factory: ${f.error}`} onRetry={f.reload} />
        </div>
      )}
      {f.loading && !fac && <Loading text="Loading factory…" rows={5} />}
      {fac && (
        <div className="mt-4 flex flex-col gap-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="font-display text-[34px] font-semibold uppercase leading-[36px]">{fac.name}</h1>
              <p className="mt-1.5 flex flex-wrap items-center gap-2 text-base text-ink-2">
                {fac.region} <Pill>{fac.archetype}</Pill>
              </p>
              {fac.personality && <p className="mt-2 max-w-[72ch] text-base text-ink-2">Negotiation agent: {fac.personality}</p>}
            </div>
            <LabelBadge label="fictional" tip="Simulated factory — demo data" />
          </div>

          <StatStrip
            items={[
              ...(hasTrackRecord(fac.past_performance)
                ? [
                    { label: "Orders completed", value: <span className="font-mono text-xl">{fac.past_performance.orders_completed}</span> },
                    { label: "On-time rate", value: <span className="font-mono text-xl">{fac.past_performance.on_time_rate_pct}%</span> },
                    { label: "Defect rate", value: <span className="font-mono text-xl">{fac.past_performance.defect_rate_pct}%</span> },
                  ]
                : [{ label: "Track record", value: <span className="text-md text-ink-2">No track record yet</span>, sub: "No completed orders on record" }]),
              {
                label: "Current load",
                value: (
                  <span className="flex items-center gap-3">
                    <span className="font-mono text-xl">{Math.round(fac.capacity.current_load_pct)}%</span>
                    <span className="h-[3px] w-24 overflow-hidden rounded-full bg-paper-2">
                      <span className="block h-full bg-ink" style={{ width: `${Math.min(100, fac.capacity.current_load_pct)}%` }} />
                    </span>
                  </span>
                ),
              },
            ]}
          />

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <Card title={<>Capacity profile <span className="font-mono text-sm font-normal text-ink-3">register_capacity</span></>} fictional>
              <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
                <KV k="Processes">{fac.capacity.processes.map(humanize).join(", ")}</KV>
                <KV k="Materials">{fac.capacity.materials.join(", ")}</KV>
                <KV k="MOQ">
                  <span className="font-mono">{fac.capacity.moq.toLocaleString("en-US")}</span> units
                </KV>
                <KV k="Lead time">
                  <span className="font-mono">{fac.capacity.lead_time_days}</span> days
                </KV>
                <KV k="Monthly capacity">
                  <span className="font-mono">{fac.capacity.monthly_capacity.toLocaleString("en-US")}</span> units
                </KV>
                <KV k="Certifications">{fac.capacity.certifications.join(", ") || "—"}</KV>
              </div>
            </Card>
            <Card title="Audit notes" fictional>
              {fac.audit_notes.length ? (
                <ul className="flex flex-col">
                  {fac.audit_notes.map((n) => (
                    <li key={n} className="border-b border-line py-2 text-base last:border-b-0">
                      {n}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-base text-ink-3">No audit notes.</p>
              )}
            </Card>
          </div>

          <h2 className="mt-4 text-lg font-semibold tracking-[-0.015em]">
            RFQs received {rfqs.data && <span className="font-mono text-base font-normal text-ink-3">{rfqs.data.length}</span>}
          </h2>
          {rfqs.error && <ErrorBox message={`Could not load RFQs: ${rfqs.error}`} onRetry={rfqs.reload} />}
          {rfqs.loading && !rfqs.data && <Loading text="Loading RFQs…" />}
          {rfqs.data && rfqs.data.length === 0 && (
            <Empty title="No RFQs received yet." body="RFQs arrive here when a project's negotiation stage sends its Factory Pack to this factory." />
          )}
          {rfqs.data?.map((r) => (
            <Card
              key={r.rfq.id}
              fictional
              title={
                <span>
                  {r.product_name} <span className="ml-1 font-mono text-sm font-normal text-ink-3">{r.rfq.id}</span>
                </span>
              }
              right={
                <Pill tone={r.rfq.status === "accepted" ? "green" : r.rfq.status === "declined" ? "red" : "zinc"} dot>
                  {r.rfq.status}
                </Pill>
              }
            >
              <p className="mb-4 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-2">
                <span>
                  Project{" "}
                  <Link href={`/projects/${r.rfq.project_id}`} className="font-mono text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink">
                    {r.rfq.project_id}
                  </Link>
                </span>
                <span>
                  Factory Pack <span className="font-mono text-ink">{r.rfq.factory_pack_id}</span>
                </span>
                <span>
                  Quantities <span className="font-mono text-ink">{r.rfq.quantities.map((q) => q.toLocaleString("en-US")).join(" / ")}</span>
                </span>
                <span className="font-mono">{fmtDate(r.rfq.created_at)}</span>
              </p>
              <Table>
                <thead>
                  <tr>
                    <Th>Quote</Th>
                    <Th>Status</Th>
                    <Th>Unit price by tier</Th>
                    <Th right>Tooling</Th>
                    <Th right>MOQ</Th>
                    <Th right>Lead</Th>
                    <Th>Payment</Th>
                  </tr>
                </thead>
                <tbody>
                  {[...r.quotes]
                    .sort((a, b) => a.version - b.version)
                    .map((q) => (
                      <tr key={q.id}>
                        <Td className="font-mono">v{q.version}</Td>
                        <Td className="capitalize text-ink-2">{q.status}</Td>
                        <Td className="font-mono text-sm">{q.tiers.map((t) => `${t.quantity.toLocaleString("en-US")}: $${t.unit_price_usd.toFixed(2)}`).join("  ·  ")}</Td>
                        <Td right className="font-mono">${q.tooling_usd.toLocaleString("en-US")}</Td>
                        <Td right className="font-mono">{q.moq.toLocaleString("en-US")}</Td>
                        <Td right className="font-mono">{q.lead_time_days} d</Td>
                        <Td className="text-sm text-ink-2">{q.payment_terms}</Td>
                      </tr>
                    ))}
                </tbody>
              </Table>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
