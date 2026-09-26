"use client";

import Link from "next/link";
import type { Factory } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { hasTrackRecord, humanize } from "@/lib/meta";
import { Empty, ErrorBox, LabelBadge, Loading, Table, Td, Th } from "@/components/ui";
import { OfferCapacity } from "@/components/OfferCapacity";

function Load({ pct }: { pct: number }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <span className="h-[3px] w-16 overflow-hidden rounded-full bg-paper-2">
        <span className={`block h-full ${pct >= 80 ? "bg-accent" : "bg-ink"}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </span>
      <span className="w-9 text-right font-mono">{Math.round(pct)}%</span>
    </span>
  );
}

export default function FactoriesPage() {
  const { data, error, loading, reload } = useApi<Factory[]>("/factories");
  return (
    <div className="mx-auto max-w-[1320px] px-6 pt-10 lg:px-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-[34px] font-semibold uppercase leading-[36px]">Factory portal</h1>
          <p className="mt-2 max-w-[72ch] text-md text-ink-2">
            The factory side of the network: each factory registers its capacity through the production MCP and receives RFQs built from
            Factory Packs. Pick a factory to see its profile and the RFQs it received.
          </p>
        </div>
        {data && (
          <p className="text-sm text-ink-2">
            <span className="font-mono text-ink">{data.length}</span> factories
          </p>
        )}
      </div>

      <div className="mt-8 rounded-md border border-line bg-surface px-6 py-4">
        {error && <ErrorBox message={`Could not load factories: ${error}`} onRetry={reload} />}
        {loading && !data && <Loading text="Loading factories…" rows={6} />}
        {data && data.length === 0 && <Empty title="No factories in the network yet." />}
        {data && data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Factory</Th>
                <Th>Processes</Th>
                <Th right>MOQ</Th>
                <Th right>Lead time</Th>
                <Th right>Monthly capacity</Th>
                <Th right>Load</Th>
                <Th right>On time</Th>
                <Th right>Data</Th>
              </tr>
            </thead>
            <tbody>
              {data.map((f) => (
                <tr key={f.id} className="group">
                  <Td>
                    <Link href={`/factories/${f.id}`} className="font-medium transition-colors group-hover:text-accent-ink">
                      {f.name}
                    </Link>
                    <div className="text-sm text-ink-2">
                      {f.region} · {f.archetype}
                    </div>
                  </Td>
                  <Td className="max-w-[260px] text-sm text-ink-2">{f.capacity.processes.map(humanize).join(", ")}</Td>
                  <Td right className="font-mono">{f.capacity.moq.toLocaleString("en-US")}</Td>
                  <Td right className="whitespace-nowrap font-mono">{f.capacity.lead_time_days} d</Td>
                  <Td right className="font-mono">{f.capacity.monthly_capacity.toLocaleString("en-US")}</Td>
                  <Td right>
                    <Load pct={f.capacity.current_load_pct} />
                  </Td>
                  <Td right className="font-mono">
                    {hasTrackRecord(f.past_performance) ? `${f.past_performance.on_time_rate_pct}%` : <span className="font-sans text-sm text-ink-3">No track record yet</span>}
                  </Td>
                  <Td right>
                    <LabelBadge label="fictional" small />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <div className="mt-10">
        <OfferCapacity onCreated={reload} />
      </div>
    </div>
  );
}
