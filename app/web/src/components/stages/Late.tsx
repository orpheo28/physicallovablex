"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type {
  BrandArtifact,
  Factory,
  FinancingArtifact,
  ListingDraft,
  LogisticsArtifact,
  NegotiationArtifact,
  QCArtifact,
  Quote,
  ToolingArtifact,
} from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { fmtDate, humanize } from "@/lib/meta";
import { DimsView, StackedBar } from "../blocks";
import { Btn, Card, KV, LabelBadge, LV, Pill, Segmented, Severity, Spinner, StatStrip, Table, Td, Th } from "../ui";
import type { StageViewProps } from "./types";

const CashChart = dynamic(() => import("./CashChart"), {
  ssr: false,
  loading: () => <div className="flex h-[300px] items-center justify-center text-sm text-ink-3">Loading chart…</div>,
});

function useFactoryNames() {
  const { data } = useApi<Factory[]>("/factories");
  return (id: string) => data?.find((f) => f.id === id)?.name ?? id;
}

// ---------------------------------------------------------------- Stage 8
const usd = (n: number, d = 2) => `$${n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })}`;

function QuoteMatrix({ factories, quotes, name, recommended }: { factories: string[]; quotes: Quote[]; name: (id: string) => string; recommended?: string }) {
  const latest = factories
    .map((f) => [...quotes.filter((q) => q.factory_id === f)].sort((a, b) => b.version - a.version))
    .map((qs) => ({ latest: qs[0], earlier: qs.slice(1) }))
    .filter((x) => x.latest);
  const qtys = Array.from(new Set(latest.flatMap((x) => x.latest.tiers.map((t) => t.quantity)))).sort((a, b) => a - b);
  const isRec = (x: (typeof latest)[number]) => x.latest.id === recommended || x.earlier.some((q) => q.id === recommended);
  const row = (label: string, cell: (q: Quote) => React.ReactNode, mono = true) => (
    <tr key={label}>
      <Td className="text-ink-2">{label}</Td>
      {latest.map((x) => (
        <Td key={x.latest.id} right className={`${mono ? "font-mono" : "text-sm"} ${isRec(x) ? "bg-accent-soft shadow-[inset_1px_0_0_#FF4F00,inset_-1px_0_0_#FF4F00]" : ""}`}>
          {cell(x.latest)}
        </Td>
      ))}
    </tr>
  );
  return (
    <Table>
      <thead>
        <tr>
          <Th>Latest quote</Th>
          {latest.map((x) => (
            <Th key={x.latest.id} right className={`relative normal-case tracking-normal ${isRec(x) ? "bg-accent-soft shadow-[inset_1px_0_0_#FF4F00,inset_-1px_0_0_#FF4F00]" : ""}`}>
              {isRec(x) && <span className="absolute left-0 right-0 top-0 h-[3px] bg-accent" aria-hidden />}
              {isRec(x) && (
                <span className="mb-1.5 mt-2 flex justify-end">
                  <Pill tone="accent" dot>
                    Recommended
                  </Pill>
                </span>
              )}
              <span className={`block whitespace-normal text-base font-medium normal-case tracking-normal text-ink ${isRec(x) ? "" : "pt-2"}`}>{name(x.latest.factory_id)}</span>
              <span className="mt-0.5 flex items-center justify-end gap-2 text-sm font-normal normal-case tracking-normal text-ink-3">
                v{x.latest.version} · {x.latest.status}
              </span>
            </Th>
          ))}
        </tr>
      </thead>
      <tbody>
        {qtys.map((qty) => row(`${qty.toLocaleString("en-US")} units`, (q) => {
          const t = q.tiers.find((t) => t.quantity === qty);
          return t ? usd(t.unit_price_usd) : "—";
        }))}
        {row("Tooling", (q) => usd(q.tooling_usd, 0))}
        {row("MOQ", (q) => q.moq.toLocaleString("en-US"))}
        {row("Lead time", (q) => `${q.lead_time_days} d`)}
        {row("Payment", (q) => q.payment_terms, false)}
        {row("Exceptions", (q) => (q.exceptions.length ? <span className="text-estimate-ink">{q.exceptions.join("; ")}</span> : "—"), false)}
        <tr>
          <Td className="text-ink-2">Earlier versions</Td>
          {latest.map((x) => (
            <Td key={x.latest.id} right className={`text-sm text-ink-3 ${isRec(x) ? "bg-accent-soft shadow-[inset_1px_0_0_#FF4F00,inset_-1px_0_0_#FF4F00]" : ""}`}>
              {x.earlier.length === 0
                ? "—"
                : x.earlier.map((q) => (
                    <div key={q.id}>
                      v{q.version} {q.status}: {q.tiers.map((t) => usd(t.unit_price_usd)).join(" / ")}
                    </div>
                  ))}
            </Td>
          ))}
        </tr>
      </tbody>
    </Table>
  );
}

export function NegotiationView({ artifact: a, busy, run }: StageViewProps<NegotiationArtifact>) {
  const name = useFactoryNames();
  const [lang, setLang] = useState<"en" | "cn">("en");
  const [filter, setFilter] = useState<string>("all");
  const factories = Array.from(new Set([...a.rfqs.map((r) => r.factory_id), ...a.quotes.map((q) => q.factory_id)]));
  const turns = [...a.transcript].sort((x, y) => x.turn - y.turn).filter((t) => filter === "all" || t.factory_id === filter);
  const rec = a.recommendation;
  const hasCn = a.transcript.some((t) => t.message_cn);

  return (
    <div className="flex flex-col gap-6">
      <Card
        title="Recommendation"
        right={a.user_approved ? <Pill tone="green" dot>Approved by you</Pill> : <Pill tone="amber" dot>Awaiting your approval</Pill>}
      >
        <p className="text-lg font-medium tracking-[-0.01em]">
          {name(rec.factory_id)} <span className="ml-1 font-mono text-sm font-normal text-ink-3">{rec.quote_id}</span>
        </p>
        <p className="mt-1.5 max-w-[72ch] text-base text-ink-2">{rec.rationale}</p>
        {a.final_terms ? (
          <div className="mt-5 grid gap-x-6 gap-y-4 border-t border-line pt-5 sm:grid-cols-3 lg:grid-cols-6">
            <KV k="Quantity">
              <span className="font-mono">{a.final_terms.quantity.toLocaleString("en-US")}</span>
            </KV>
            <KV k="Unit price">
              <LV v={a.final_terms.unit_price} />
            </KV>
            <KV k="Tooling">
              <LV v={a.final_terms.tooling} />
            </KV>
            <KV k="MOQ">
              <span className="font-mono">{a.final_terms.moq.toLocaleString("en-US")}</span>
            </KV>
            <KV k="Lead time">
              <LV v={a.final_terms.lead_time_days} />
            </KV>
            <KV k="Payment">{a.final_terms.payment_terms}</KV>
          </div>
        ) : null}
        {!a.user_approved && (
          <div className="mt-5">
            <Btn variant="primary" disabled={busy} onClick={() => run({ approve: true, quote_id: rec.quote_id })}>
              {busy && <Spinner />} Approve recommended quote
            </Btn>
          </div>
        )}
      </Card>

      <Card fictional title="Quotes side by side">
        <QuoteMatrix factories={factories} quotes={a.quotes} name={name} recommended={rec.quote_id} />
      </Card>

      <Card
        fictional
        flush
        title={
          <>
            Negotiation transcript <span className="font-mono text-ink-3">{a.transcript.length}</span>
          </>
        }
        right={
          <>
            <select
              aria-label="Filter by factory"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="field !h-7 !w-52 !py-0 !text-sm"
            >
              <option value="all">All factories</option>
              {factories.map((f) => (
                <option key={f} value={f}>
                  {name(f)}
                </option>
              ))}
            </select>
            <Segmented
              label="Transcript language"
              value={lang}
              onChange={setLang}
              options={[
                { value: "en", label: "EN" },
                { value: "cn", label: "中文", disabled: !hasCn },
              ]}
            />
          </>
        }
      >
        {lang === "cn" && (
          <p className="border-b border-line bg-estimate-soft px-5 py-2 text-sm text-estimate-ink">Chinese is machine-translated — to be reviewed by a native speaker.</p>
        )}
        <ol>
          {turns.map((t) => {
            const factory = t.speaker === "factory_agent";
            const user = t.speaker === "user";
            const text = lang === "cn" && t.message_cn ? t.message_cn : t.message;
            const who = factory ? `${name(t.factory_id)} agent` : user ? "You" : "Platform agent";
            return (
              <li key={t.id} className="grid grid-cols-[44px_176px_minmax(0,1fr)] gap-x-4 border-b border-line px-5 py-4 last:border-b-0">
                <span className="pt-0.5 font-mono text-sm text-ink-3">{String(t.turn).padStart(2, "0")}</span>
                <div className="flex flex-col gap-1 pt-0.5">
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <span
                      className={`h-2 w-2 shrink-0 ${factory ? "rounded-full bg-fictional" : user ? "rounded-full bg-accent" : "rounded-[1px] bg-ink"}`}
                      aria-hidden
                    />
                    {who}
                  </span>
                  {!factory && !user && <span className="pl-4 text-sm text-ink-3">to {name(t.factory_id)}</span>}
                  {t.quote_id && <span className="pl-4 font-mono text-2xs text-ink-3">{t.quote_id}</span>}
                </div>
                <div className="min-w-0">
                  <p className="max-w-[72ch] whitespace-pre-wrap text-base">{text}</p>
                  {Object.keys(t.proposed_changes ?? {}).length > 0 && (
                    <p className="mt-2 flex flex-wrap gap-1.5">
                      {Object.entries(t.proposed_changes).map(([k, v]) => (
                        <span key={k} className="rounded-sm bg-paper-2 px-1.5 py-0.5 font-mono text-2xs text-ink-2">
                          {k} = {typeof v === "object" ? JSON.stringify(v) : String(v)}
                        </span>
                      ))}
                    </p>
                  )}
                  {t.rationale && <p className="mt-2 text-sm text-ink-3">Why: {t.rationale}</p>}
                </div>
              </li>
            );
          })}
        </ol>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- Stage 9
export function ToolingView({ artifact: a }: StageViewProps<ToolingArtifact>) {
  const ts = (d: string) => new Date(d).getTime();
  const valid = a.milestones.filter((m) => !Number.isNaN(ts(m.start_date)) && !Number.isNaN(ts(m.end_date)));
  const min = Math.min(...valid.map((m) => ts(m.start_date)));
  const max = Math.max(...valid.map((m) => ts(m.end_date)));
  const span = Math.max(max - min, 1);
  return (
    <div className="flex flex-col gap-6">
      <Card title="Milestones" right={valid.length ? <span className="font-mono text-sm">{fmtDate(new Date(min).toISOString())} – {fmtDate(new Date(max).toISOString())}</span> : undefined}>
        <div className="flex flex-col">
          {a.milestones.map((m) => {
            const left = ((ts(m.start_date) - min) / span) * 100;
            const width = Math.max(((ts(m.end_date) - ts(m.start_date)) / span) * 100, 0.8);
            return (
              <div key={m.id} className="grid grid-cols-[minmax(160px,220px)_1fr_minmax(150px,auto)] items-center gap-4 border-b border-line py-2.5 text-base last:border-b-0">
                <div>
                  <div className="font-medium">{m.name}</div>
                  <div className="font-mono text-2xs text-ink-3">
                    {fmtDate(m.start_date)} – {fmtDate(m.end_date)}
                  </div>
                </div>
                <div className="relative h-2 rounded-full bg-paper-2">
                  <div
                    className={`absolute top-0 h-2 rounded-full ${m.kind === "mass_production" ? "bg-accent" : m.kind.startsWith("tooling") ? "bg-ink" : "bg-ink-3"}`}
                    style={{ left: `${Number.isFinite(left) ? left : 0}%`, width: `${Number.isFinite(width) ? width : 1}%` }}
                    title={m.notes ?? m.name}
                  />
                </div>
                <div className="flex flex-col items-end gap-1 text-sm">
                  <LV v={m.duration_days} />
                  {m.payment && (
                    <span>
                      Pay <LV v={m.payment} />
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Card>
      <Card title="Payment schedule">
        <Table>
          <thead>
            <tr>
              <Th>Due</Th>
              <Th>Milestone</Th>
              <Th>Description</Th>
              <Th right>% of order</Th>
              <Th right>Amount</Th>
            </tr>
          </thead>
          <tbody>
            {a.payment_schedule.map((p, i) => (
              <tr key={i}>
                <Td className="whitespace-nowrap font-mono text-sm">{fmtDate(p.due_date)}</Td>
                <Td className="font-mono text-sm text-ink-3">{p.milestone_id}</Td>
                <Td>{p.description}</Td>
                <Td right className="font-mono">{p.pct_of_order != null ? `${p.pct_of_order}%` : "—"}</Td>
                <Td right>
                  <LV v={p.amount} />
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- Stage 10
export function QCView({ artifact: a }: StageViewProps<QCArtifact>) {
  return (
    <div className="flex flex-col gap-6">
      <Card title="Inspection plan">
        <div className="grid gap-x-8 gap-y-5 sm:grid-cols-3 lg:grid-cols-4">
          <KV k="Standard">{a.standard}</KV>
          <KV k="Inspection level">{a.inspection_level}</KV>
          <KV k="Lot size"><span className="font-mono">{a.lot_size.toLocaleString("en-US")}</span> units</KV>
          <KV k="Sample size">
            <LV v={a.sample_size} />
          </KV>
          <KV k="Man-days">
            <LV v={a.inspection_man_days} />
          </KV>
          <KV k="Man-day rate">
            <LV v={a.man_day_rate} />
          </KV>
          <KV k="Inspection cost">
            <LV v={a.inspection_cost} />
          </KV>
        </div>
      </Card>
      <Card title={<>Defect classes <span className="font-mono text-ink-3">{a.defects.length}</span></>}>
        <Table>
          <thead>
            <tr>
              <Th>Severity</Th>
              <Th>Defect</Th>
              <Th>Spec line</Th>
              <Th>Check method</Th>
              <Th right>AQL</Th>
            </tr>
          </thead>
          <tbody>
            {a.defects.map((d) => (
              <tr key={d.id}>
                <Td>
                  <Severity level={d.severity} />
                </Td>
                <Td>{d.description}</Td>
                <Td className="font-mono text-sm text-ink-3">{d.spec_ref}</Td>
                <Td className="text-ink-2">{d.check_method}</Td>
                <Td right className="font-mono">
                  {d.aql}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- Stage 11
const MODE_TEXT: Record<string, string> = { sea_lcl: "Sea LCL", sea_fcl: "Sea FCL", air: "Air", express: "Express" };

export function LogisticsView({ artifact: a, busy, run }: StageViewProps<LogisticsArtifact>) {
  return (
    <div className="flex flex-col gap-6">
      <StatStrip
        items={[
          {
            label: "Landed cost per unit",
            value: <LV v={a.landed_cost_per_unit} big />,
            sub: `${a.incoterm}, ${a.quantity.toLocaleString("en-US")} units to ${a.destination}`,
            accent: true,
          },
          {
            label: "Reconciliation with stage 5",
            value: (
              <Pill tone={a.reconciles_with_stage5 ? "green" : "red"} dot>
                {a.reconciles_with_stage5 ? "Reconciles (within 10%)" : "Does not reconcile"}
              </Pill>
            ),
            sub: a.reconciliation_note,
          },
          {
            label: "Section 122 surcharge",
            value: (
              <label className="flex cursor-pointer items-center gap-3 text-base font-medium">
                <button
                  type="button"
                  role="switch"
                  aria-checked={a.section_122_applied}
                  disabled={busy}
                  onClick={() => run({ section_122: !a.section_122_applied })}
                  className={`relative h-5 w-9 shrink-0 rounded-full transition-colors duration-150 disabled:opacity-50 ${a.section_122_applied ? "bg-ink" : "bg-line-2"}`}
                >
                  <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-[left] duration-150 ${a.section_122_applied ? "left-[18px]" : "left-0.5"}`} />
                </button>
                {a.section_122_applied ? "Applied" : "Not applied"} {busy && <Spinner />}
              </label>
            ),
            sub: "Temporary import surcharge scenario.",
          },
        ]}
      />
      <Card title="Landed cost per unit — breakdown">
        <StackedBar parts={a.landed_cost_breakdown} total={a.landed_cost_per_unit} />
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Freight options" fictional>
          <Table>
            <thead>
              <tr>
                <Th>Mode</Th>
                <Th>Transit</Th>
                <Th>Cost / unit</Th>
              </tr>
            </thead>
            <tbody>
              {a.freight_options.map((f) => (
                <tr key={f.mode}>
                  <Td className="font-medium">
                    <span className="flex items-center gap-2">{MODE_TEXT[f.mode] ?? f.mode} {f.mode === a.chosen_mode && <Pill tone="accent" dot>Chosen</Pill>}</span>
                  </Td>
                  <Td>
                    <LV v={f.transit_days} />
                  </Td>
                  <Td>
                    <LV v={f.cost_per_unit} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
        <Card title="Duties (HTS)">
          <div className="flex flex-col gap-4 text-base">
            <p>
              <span className="font-mono text-lg">{a.hts.code}</span>
              <span className="mt-1 block text-ink-2">{a.hts.description}</span>
            </p>
            <div className="grid grid-cols-2 gap-4 border-t border-line pt-4">
              <KV k="General rate">
                <LV v={a.hts.general_rate} />
              </KV>
              <KV k="Section 301">
                <LV v={a.hts.section_301_rate} />
              </KV>
            </div>
            <a href={a.hts.source_url} target="_blank" rel="noreferrer" className="break-all text-sm text-ink-2 underline decoration-line-2 underline-offset-4 hover:text-ink">
              {a.hts.source_url}
            </a>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Stage 12
export function FinancingView({ artifact: a }: StageViewProps<FinancingArtifact>) {
  return (
    <div className="flex flex-col gap-6">
      <Card
        title="Cash curve"
        right={
          <span className="flex items-center gap-2">
            All points <LabelBadge label={a.cash_curve[0]?.cumulative.label ?? "estimate"} small />
          </span>
        }
      >
        <div className="grid gap-8 lg:grid-cols-[220px_minmax(0,1fr)]">
          <div className="flex flex-col gap-4 lg:border-r lg:border-line lg:pr-8">
            <div className="flex flex-col gap-1.5">
              <span className="micro">Total cash</span>
              <LV v={a.total_cash} big />
            </div>
            {a.stage5_total && (
              <div className="flex flex-col gap-1.5">
                <span className="micro">Budget (stage 5)</span>
                <LV v={a.stage5_total} />
              </div>
            )}
            {a.reconciliation_note ? (
              <p className="text-sm text-ink-2">{a.reconciliation_note}</p>
            ) : (
              a.matches_stage5_total && <Pill tone="green" dot>Same as the stage 5 budget</Pill>
            )}
            <p className="text-sm text-ink-3">Hover the chart for each milestone.</p>
          </div>
          {a.cash_curve.length ? <CashChart points={a.cash_curve} /> : <p className="text-base text-ink-3">No cash points.</p>}
        </div>
      </Card>
      <Card title="Cash out by milestone">
        <Table>
          <thead>
            <tr>
              <Th>Date</Th>
              <Th>Milestone</Th>
              <Th>Description</Th>
              <Th right>Cash out</Th>
              <Th right>Cumulative</Th>
            </tr>
          </thead>
          <tbody>
            {a.cash_curve.map((p, i) => (
              <tr key={i}>
                <Td className="whitespace-nowrap font-mono text-sm">{fmtDate(p.date)}</Td>
                <Td className="font-mono text-sm text-ink-3">{p.milestone_id}</Td>
                <Td>{p.description}</Td>
                <Td right>
                  <LV v={p.cash_out} />
                </Td>
                <Td right>
                  <LV v={p.cumulative} />
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {a.options.map((o) => (
          <Card key={o.name} title={o.name} right={<Pill>{humanize(o.kind)}</Pill>}>
            <p className="text-base text-ink-2">
              {o.description}{" "}
              {o.cost && (
                <span className="whitespace-nowrap align-middle">
                  <LabelBadge label={o.cost.label} tip={`Figures in this text: ${o.cost.source_or_assumption}`} small />
                </span>
              )}
            </p>
            {o.cost && (
              <p className="mt-3 flex items-center gap-2 text-base">
                <span className="text-ink-2">Cost</span> <LV v={o.cost} />
              </p>
            )}
            <div className="mt-4 grid grid-cols-2 gap-4 border-t border-line pt-4 text-sm">
              <div>
                <p className="micro !text-measured-ink">For</p>
                <ul className="mt-1.5 flex flex-col gap-1">
                  {o.pros.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="micro !text-danger">Against</p>
                <ul className="mt-1.5 flex flex-col gap-1">
                  {o.cons.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Stage 13
function Listing({ l }: { l: ListingDraft }) {
  return (
    <Card title={l.channel === "shopify" ? "Shopify listing draft" : "Amazon listing draft"} right={<LV v={l.price} />}>
      <p className="text-md font-medium">{l.title}</p>
      <ul className="mt-3 list-disc pl-5 text-base">
        {l.bullets.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ul>
      <p className="mt-3 whitespace-pre-wrap text-base text-ink-2">{l.description}</p>
      {l.keywords.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {l.keywords.map((k) => (
            <Pill key={k}>{k}</Pill>
          ))}
        </div>
      )}
    </Card>
  );
}

export function BrandView({ artifact: a }: StageViewProps<BrandArtifact>) {
  return (
    <div className="flex flex-col gap-6">
      <Card title="Name options">
        <div className="grid gap-3 md:grid-cols-3">
          {a.name_options.map((n) => (
            <div key={n.name} className={`flex flex-col gap-2 rounded-md border p-4 ${a.chosen_name === n.name ? "border-ink" : "border-line"}`}>
              <div className="flex items-center justify-between gap-2">
                <p className="text-xl font-semibold tracking-[-0.025em]">{n.name}</p>
                {a.chosen_name === n.name && <Pill tone="accent" dot>Chosen</Pill>}
              </div>
              <p className="text-base text-ink-2">{n.rationale}</p>
            </div>
          ))}
        </div>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Packaging">
          <div className="grid gap-3 sm:grid-cols-2">
            <KV k="Box">{a.packaging.box_type}</KV>
            <KV k="Dimensions">
              <DimsView d={a.packaging.dimensions} />
            </KV>
            <KV k="Materials">{a.packaging.materials.join(", ")}</KV>
            <KV k="Printing">{a.packaging.printing}</KV>
            <KV k="In the box">{a.packaging.contents.join(", ")}</KV>
            <KV k="Unit cost">
              <LV v={a.packaging.unit_cost} />
            </KV>
          </div>
        </Card>
        <Card title="Landing copy">
          <div className="rounded-sm bg-paper p-6">
            <p className="text-xl font-semibold tracking-[-0.025em]">{a.landing_copy.headline}</p>
            <p className="mt-2 text-md text-ink-2">{a.landing_copy.subheadline}</p>
            <ul className="mt-4 list-disc pl-5 text-base">
              {a.landing_copy.bullets.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
            <span className="mt-5 inline-flex h-8 items-center rounded bg-ink px-3 text-sm font-medium text-white">{a.landing_copy.cta}</span>
          </div>
        </Card>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Listing l={a.shopify_listing} />
        <Listing l={a.amazon_listing} />
      </div>
    </div>
  );
}
