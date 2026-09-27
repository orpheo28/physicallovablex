"use client";

import Link from "next/link";
import { useState } from "react";
import type { Factory } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { hasTrackRecord, humanize } from "@/lib/meta";
import { Empty, ErrorBox, LabelBadge, Loading, Segmented, Table, Td, Th } from "@/components/ui";
import { OfferCapacity } from "@/components/OfferCapacity";
import { ScrollArea } from "@/components/ScrollArea";
import { ConnectAgent } from "@/components/ConnectAgent";

function Load({ pct }: { pct: number }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <span className="h-[3px] w-16 overflow-hidden rounded-full bg-paper-2">
        <span className={`block h-full rounded-full ${pct >= 80 ? "bg-estimate" : "bg-ink-3"}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </span>
      <span className="w-9 text-right font-mono">{Math.round(pct)}%</span>
    </span>
  );
}

type Kind = "all" | "factory" | "installer" | "integrator";
const KIND_TEXT: Record<Exclude<Kind, "all">, string> = { factory: "Factories", installer: "Installers", integrator: "Integrators" };

export default function FactoriesPage() {
  const { data: all, error, loading, reload } = useApi<Factory[]>("/factories");
  // Factory.kind (W21b): factory · installer (site install, e.g. rooftop PV) · integrator (bought-in modules: drones, robots).
  const [kind, setKind] = useState<Kind>("all");
  const kinds = (["factory", "installer", "integrator"] as const).filter((k) => all?.some((f) => (f.kind ?? "factory") === k));
  const data = all?.filter((f) => kind === "all" || (f.kind ?? "factory") === kind);
  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)]">
      <div className="flex flex-wrap items-end justify-between gap-4 px-10 pb-4 pt-6">
        <div>
          <h1 className="title text-[28px] leading-[34px]">Factory portal</h1>
          <p className="mt-2 max-w-[860px] text-md text-ink-2 text-pretty">
            The factory side of the network: each factory registers its capacity through the production MCP and receives RFQs built from
            Factory Packs. Pick a factory to see its profile and the RFQs it received.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {kinds.length > 1 && (
            <Segmented
              label="Partner type"
              value={kind}
              onChange={setKind}
              options={[{ value: "all" as Kind, label: "All" }, ...kinds.map((k) => ({ value: k as Kind, label: KIND_TEXT[k] }))]}
            />
          )}
          {data && (
            <p className="text-sm text-ink-2">
              <span className="font-mono text-ink">{data.length}</span> {kind === "all" ? (kinds.length > 1 ? "partners" : "factories") : KIND_TEXT[kind].toLowerCase()}
            </p>
          )}
        </div>
      </div>

      <ScrollArea className="h-full px-10 pb-10 pt-2" label="Factories">
      <ConnectAgent />
      <div className="rounded-lg bg-surface px-6 py-4">
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
      </ScrollArea>
    </div>
  );
}
