"use client";

import { useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Factory, NegotiationArtifact, NegotiationTurn, Quote } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { ScrollArea } from "../ScrollArea";
import { Btn, KV, LabelBadge, LV, Segmented, Spinner } from "../ui";
import type { StageViewProps } from "./types";

// ---------------------------------------------------------------- helpers

const usd = (n: number, d = 2) => `$${n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })}`;
const qty = (n: number) => n.toLocaleString("en-US");
const hhmm = (s: string) => {
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? "" : `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
};

function useFactoryNames() {
  const { data } = useApi<Factory[]>("/factories");
  return (id: string) => {
    const n = data?.find((f) => f.id === id)?.name ?? id;
    return /\(fictional\)/i.test(n) ? n : `${n} (fictional)`;
  };
}
const bare = (name: string) => name.replace(/\s*\(fictional\)\s*$/i, "");
const short = (name: string) => bare(name).split(/\s+/)[0];
const initials = (name: string) =>
  bare(name)
    .split(/\s+/)
    .filter((w) => /^[A-Za-z]/.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");

/** A counter-offer or a revised quote, as a before → after chip. */
function Diff({ label, from, to }: { label: string; from: string; to: string }) {
  return (
    <span className="inline-flex h-6 items-center gap-1.5 rounded-sm bg-surface px-2 font-mono text-[11.5px] text-ink-2">
      <span className="font-sans text-ink-3">{label}</span>
      <span className="text-ink-3 line-through decoration-ink-4">{from}</span>
      <span className="text-accent-ink" aria-label="to">
        →
      </span>
      <span className="font-medium text-ink">{to}</span>
    </span>
  );
}

function fmtField(key: string, v: unknown): { label: string; fmt: (x: number | string) => string } {
  if (/^unit_price_(\d+)$/.test(key)) return { label: `${qty(Number(key.split("_")[2]))} u`, fmt: (x) => usd(Number(x)) };
  if (key === "tooling_usd") return { label: "Tooling", fmt: (x) => usd(Number(x), 0) };
  if (key === "moq") return { label: "MOQ", fmt: (x) => qty(Number(x)) };
  if (key === "lead_time_days") return { label: "Lead", fmt: (x) => `${x} d` };
  if (key === "payment_terms") return { label: "Terms", fmt: (x) => String(x) };
  return { label: key.replace(/_/g, " "), fmt: (x) => (typeof v === "object" ? JSON.stringify(x) : String(x)) };
}

function quoteValue(q: Quote, key: string): number | string | undefined {
  const m = /^unit_price_(\d+)$/.exec(key);
  if (m) return q.tiers.find((t) => t.quantity === Number(m[1]))?.unit_price_usd;
  if (key === "tooling_usd") return q.tooling_usd;
  if (key === "moq") return q.moq;
  if (key === "lead_time_days") return q.lead_time_days;
  if (key === "payment_terms") return q.payment_terms;
  return undefined;
}

/** What changed from the previous version of a quote. */
function quoteDiffs(q: Quote, prev: Quote | undefined) {
  if (!prev) return [];
  const out: { label: string; from: string; to: string }[] = [];
  for (const t of q.tiers) {
    const p = prev.tiers.find((x) => x.quantity === t.quantity);
    if (p && p.unit_price_usd !== t.unit_price_usd) out.push({ label: `${qty(t.quantity)} u`, from: usd(p.unit_price_usd), to: usd(t.unit_price_usd) });
  }
  if (prev.tooling_usd !== q.tooling_usd) out.push({ label: "Tooling", from: usd(prev.tooling_usd, 0), to: usd(q.tooling_usd, 0) });
  if (prev.moq !== q.moq) out.push({ label: "MOQ", from: qty(prev.moq), to: qty(q.moq) });
  if (prev.lead_time_days !== q.lead_time_days) out.push({ label: "Lead", from: `${prev.lead_time_days} d`, to: `${q.lead_time_days} d` });
  if (prev.payment_terms !== q.payment_terms) out.push({ label: "Terms", from: prev.payment_terms, to: q.payment_terms });
  return out;
}

// ---------------------------------------------------------------- pieces

function Avatar({ who, name }: { who: NegotiationTurn["speaker"]; name: string }) {
  if (who === "platform_agent")
    return (
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-paper-2 text-[10px] font-semibold text-ink-2" aria-hidden>
        PLX
      </span>
    );
  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-fictional-soft text-[10.5px] font-semibold text-fictional-ink" aria-hidden>
      {initials(name)}
    </span>
  );
}

function QuoteCard({ q, prev, recommended, chosen, refQty }: { q: Quote; prev?: Quote; recommended: boolean; chosen: boolean; refQty: number }) {
  const diffs = quoteDiffs(q, prev);
  return (
    <div className={`relative mt-2 w-full max-w-[440px] overflow-hidden rounded-md ${recommended ? "bg-accent-soft/60" : "bg-paper"}`}>
      <div className="flex items-center justify-between gap-2 px-3.5 pb-1 pt-2.5">
        <span className="flex items-center gap-2 text-sm font-medium">
          Quote v{q.version} <span className="font-mono text-2xs font-normal text-ink-3">{q.id}</span>
        </span>
        <span className="flex items-center gap-1.5">
          {chosen && <span className="text-2xs font-medium text-measured-ink">Approved</span>}
          {recommended && <span className="text-2xs font-medium text-accent-ink">Recommended</span>}
          {!recommended && !chosen && <span className="text-2xs capitalize text-ink-3">{q.status}</span>}
        </span>
      </div>
      <div className="grid grid-cols-[auto_1fr] gap-x-6 px-3.5 pb-2.5 pt-1 text-sm">
        <table className="font-mono text-[12.5px]">
          <tbody>
            {q.tiers.map((t) => (
              <tr key={t.quantity}>
                <td className={`pr-3 text-ink-3 ${t.quantity === refQty ? "text-ink-2" : ""}`}>{qty(t.quantity)} u</td>
                <td className={`text-right ${t.quantity === refQty ? "font-medium text-ink" : "text-ink-2"}`}>{usd(t.unit_price_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[12.5px]">
          <dt className="text-ink-3">Tooling</dt>
          <dd className="font-mono">{usd(q.tooling_usd, 0)}</dd>
          <dt className="text-ink-3">MOQ</dt>
          <dd className="font-mono">{qty(q.moq)}</dd>
          <dt className="text-ink-3">Lead time</dt>
          <dd className="font-mono">{q.lead_time_days} d</dd>
          <dt className="text-ink-3">Terms</dt>
          <dd className="text-pretty">{q.payment_terms}</dd>
        </dl>
      </div>
      {(diffs.length > 0 || q.exceptions.length > 0) && (
        <div className="flex flex-wrap gap-1.5 px-3.5 py-2">
          {diffs.map((d) => (
            <Diff key={d.label} {...d} />
          ))}
          {q.exceptions.map((e) => (
            <span key={e} className="text-2xs text-estimate-ink">
              Exception: {e}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- view

export function NegotiationView({ artifact: a, busy, run, extras }: StageViewProps<NegotiationArtifact>) {
  const name = useFactoryNames();
  const [lang, setLang] = useState<"en" | "cn">("en");
  const [tab, setTab] = useState<string>("all");
  const [picker, setPicker] = useState(false);
  const [approving, setApproving] = useState<string | null>(null);
  const thread = useRef<HTMLDivElement>(null);

  const factories = useMemo(() => Array.from(new Set([...a.rfqs.map((r) => r.factory_id), ...a.quotes.map((q) => q.factory_id)])), [a]);
  const byId = useMemo(() => new Map(a.quotes.map((q) => [q.id, q])), [a]);
  const prevOf = (q: Quote) => a.quotes.filter((x) => x.factory_id === q.factory_id && x.version < q.version).sort((x, y) => y.version - x.version)[0];
  const latest = factories
    .map((f) => a.quotes.filter((q) => q.factory_id === f).sort((x, y) => y.version - x.version)[0])
    .filter((q): q is Quote => !!q);
  const turns = [...a.transcript].sort((x, y) => x.turn - y.turn).filter((t) => tab === "all" || t.factory_id === tab);
  const rec = a.recommendation;
  const recQuote = byId.get(rec.quote_id);
  const hasCn = a.transcript.some((t) => t.message_cn);
  const refQty = a.final_terms?.quantity ?? recQuote?.tiers[Math.min(1, (recQuote?.tiers.length ?? 1) - 1)]?.quantity ?? 0;
  const chosenId = a.user_approved ? (a.final_terms?.quote_id ?? rec.quote_id) : null;
  const chosen = chosenId ? byId.get(chosenId) : undefined;
  const autofill = a.assumptions.some((x) => x.id === "a8_autofill") && (!chosen || chosen.id === rec.quote_id);
  // Quotes seen for the first time in the thread get the full card; later mentions are referenced.
  const cardShown = new Set<string>();

  // The thread opens on (and follows) the latest turn.
  useLayoutEffect(() => {
    const el = thread.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [tab, lang, a.transcript.length]);

  async function approve(quoteId: string) {
    setApproving(quoteId);
    try {
      await run({ approve: true, quote_id: quoteId });
      setPicker(false);
    } finally {
      setApproving(null);
    }
  }

  const priceAt = (q: Quote) => q.tiers.find((t) => t.quantity === refQty)?.unit_price_usd ?? q.tiers[0]?.unit_price_usd;

  let composer: ReactNode;
  if (!a.user_approved && recQuote) {
    composer = (
      <>
        <span className="min-w-0 flex-1 text-sm text-ink-2 text-pretty">
          Recommended by the negotiation agent: <span className="text-ink">{bare(name(rec.factory_id))}</span>, quote v{recQuote.version}
        </span>
        <Btn variant="ghost" onClick={() => setPicker((o) => !o)} disabled={busy}>
          Pick another quote
        </Btn>
        <Btn variant="primary" onClick={() => approve(recQuote.id)} disabled={busy}>
          {approving === recQuote.id && <Spinner />}
          Approve {short(name(rec.factory_id))} v{recQuote.version} — {usd(priceAt(recQuote))} × {qty(refQty)}
        </Btn>
      </>
    );
  } else if (chosen) {
    composer = (
      <>
        {autofill ? (
          <span className="flex shrink-0 items-center gap-1.5 text-sm font-medium text-estimate-ink">
            <span className="h-1.5 w-1.5 rounded-full bg-estimate" aria-hidden />
            Auto-approved (autofill mode)
          </span>
        ) : (
          <span className="flex shrink-0 items-center gap-1.5 text-sm font-medium text-measured-ink">
            <span className="h-1.5 w-1.5 rounded-full bg-measured" aria-hidden />
            Approved by you
          </span>
        )}
        <span className="min-w-0 flex-1 text-sm text-ink text-pretty">
          {short(name(chosen.factory_id))} v{chosen.version} — <span className="font-mono">{usd(a.final_terms?.unit_price.value ?? priceAt(chosen))}</span> ×{" "}
          <span className="font-mono">{qty(refQty)}</span>
          {autofill && <span className="text-ink-2"> · review before any real order</span>}
        </span>
        <Btn variant="secondary" size="sm" onClick={() => setPicker((o) => !o)} disabled={busy}>
          Change factory
        </Btn>
      </>
    );
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(0,1fr)_360px] gap-5 min-[1440px]:grid-cols-[minmax(0,1fr)_400px]">
      {/* ---- conversation */}
      <section aria-label="Negotiation" className="relative flex min-h-0 flex-col overflow-hidden rounded-md bg-surface">
        <header className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3 pt-2.5">
          <div role="tablist" aria-label="Filter by factory" className="flex min-w-0 flex-1 flex-wrap items-center gap-1">
            {[{ id: "all", label: "All factories", n: a.transcript.length }, ...factories.map((f) => ({ id: f, label: short(name(f)), n: a.transcript.filter((t) => t.factory_id === f).length }))].map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={`flex h-7 shrink-0 items-center gap-1.5 rounded-full px-3 text-sm transition-colors duration-150 ${
                  tab === t.id ? "bg-paper-2 font-medium text-ink" : "text-ink-3 hover:text-ink"
                }`}
              >
                {t.label}
                <span className="font-mono text-2xs text-ink-3">{t.n}</span>
              </button>
            ))}
          </div>
          <Segmented
            label="Transcript language"
            value={lang}
            onChange={setLang}
            options={[
              { value: "en", label: "EN" },
              { value: "cn", label: "中文", disabled: !hasCn },
            ]}
          />
          <LabelBadge label="fictional" tip="Simulated factory agents — demo data" small text />
        </header>
        {lang === "cn" && (
          <p className="mx-4 mt-2 rounded-sm bg-estimate-soft px-3 py-1.5 text-sm text-estimate-ink">Chinese is machine-translated — to be reviewed by a native speaker.</p>
        )}

        <ScrollArea ref={thread} className="flex-1 px-5 py-4" label="Negotiation transcript">
          <ol className="flex flex-col gap-4">
            {turns.map((t) => {
              const factory = t.speaker === "factory_agent";
              const text = lang === "cn" && t.message_cn ? t.message_cn : t.message;
              const q = t.quote_id ? byId.get(t.quote_id) : undefined;
              if (t.speaker === "user")
                return (
                  <li key={t.id} className="flex items-center gap-3 py-1">
                    <span className="h-px flex-1 bg-line" aria-hidden />
                    <span className="flex max-w-[70%] flex-wrap items-center gap-x-2 text-sm text-ink-2">
                      <span className="font-medium text-ink">You</span> <span>{text}</span>
                      <span className="shrink-0 font-mono text-2xs text-ink-3">
                        #{String(t.turn).padStart(2, "0")} · {hhmm(t.created_at)}
                      </span>
                    </span>
                    <span className="h-px flex-1 bg-line" aria-hidden />
                  </li>
                );
              const changes = Object.entries(t.proposed_changes ?? {});
              const showCard = !!q && factory && !cardShown.has(q.id);
              if (q && showCard) cardShown.add(q.id);
              return (
                <li key={t.id} className={`flex items-start gap-3 ${factory ? "flex-row-reverse" : ""}`}>
                  <Avatar who={t.speaker} name={name(t.factory_id)} />
                  <div className={`flex min-w-0 max-w-[78%] flex-col ${factory ? "items-end" : "items-start"}`}>
                    <p className={`flex flex-wrap items-baseline gap-x-2 text-sm ${factory ? "justify-end" : ""}`}>
                      <span className="font-medium text-ink">{factory ? name(t.factory_id) : "Platform agent"}</span>
                      {!factory && <span className="text-ink-3">to {short(name(t.factory_id))}</span>}
                      <span className="font-mono text-2xs text-ink-3">
                        #{String(t.turn).padStart(2, "0")} · {hhmm(t.created_at)}
                      </span>
                    </p>
                    <div className={`mt-1 rounded-lg px-3.5 py-2.5 text-base ${factory ? "rounded-tr-sm bg-paper-2/60" : "rounded-tl-sm bg-paper"}`}>
                      <p className="whitespace-pre-wrap">{text}</p>
                      {changes.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          <span className="self-center text-2xs font-medium text-ink-3">Counter</span>
                          {changes.map(([k, v]) => {
                            const f = fmtField(k, v);
                            const was = q ? quoteValue(q, k) : undefined;
                            return was !== undefined && (typeof v === "number" || typeof v === "string") ? (
                              <Diff key={k} label={f.label} from={f.fmt(was)} to={f.fmt(v)} />
                            ) : (
                              <span key={k} className="inline-flex h-6 items-center rounded-sm bg-surface px-2 font-mono text-[11.5px] text-ink-2">
                                {f.label} {typeof v === "object" ? JSON.stringify(v) : String(v)}
                              </span>
                            );
                          })}
                        </div>
                      )}
                      {t.rationale && <p className="mt-1.5 text-sm text-ink-3">Why: {t.rationale}</p>}
                    </div>
                    {q && showCard && <QuoteCard q={q} prev={prevOf(q)} recommended={q.id === rec.quote_id} chosen={q.id === chosenId} refQty={refQty} />}
                    {q && !showCard && !factory && <span className="mt-1 font-mono text-2xs text-ink-3">re: {q.id}</span>}
                  </div>
                </li>
              );
            })}
          </ol>
        </ScrollArea>

        {/* ---- composer-like approval bar */}
        {picker && (
          <div className="mx-3 mb-2 rounded-md bg-paper px-4 py-3">
            <p className="micro">Pick the quote to approve</p>
            <ul className="mt-2 flex flex-col">
              {latest.map((q) => (
                <li key={q.id} className="flex items-center gap-3 border-b border-line py-2 text-sm last:border-b-0">
                  <span className="min-w-0 flex-1 font-medium">{name(q.factory_id)}</span>
                  <span className="font-mono text-ink-2">v{q.version}</span>
                  <span className="font-mono">{usd(priceAt(q))}</span>
                  <span className="text-ink-3">× {qty(refQty)}</span>
                  <span className="font-mono text-ink-2">{q.lead_time_days} d</span>
                  <span className="font-mono text-ink-2">tooling {usd(q.tooling_usd, 0)}</span>
                  {q.id === rec.quote_id && <span className="text-2xs font-medium text-accent-ink">Recommended</span>}
                  {q.id === chosenId ? (
                    <span className="text-sm text-measured-ink">Approved</span>
                  ) : (
                    <Btn size="sm" variant="secondary" disabled={busy} onClick={() => approve(q.id)}>
                      {approving === q.id && <Spinner />} Approve this one
                    </Btn>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        {composer && <div className="mx-3 mb-3 flex items-center gap-3 rounded-md bg-paper px-3 py-2">{composer}</div>}
      </section>

      {/* ---- recommendation + side-by-side, own scroll */}
      <ScrollArea className="h-full pb-2" label="Recommendation and quotes">
        <div className="flex flex-col gap-4">
          <section className="relative rounded-md bg-surface p-5">
            <p className="micro">Recommendation</p>
            <p className="mt-1.5 text-md font-medium tracking-[-0.01em]">{name(rec.factory_id)}</p>
            <p className="mt-1 text-sm text-ink-2">{rec.rationale}</p>
            {a.final_terms && (
              <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
                <KV k="Quantity">
                  <span className="font-mono">{qty(a.final_terms.quantity)}</span>
                </KV>
                <KV k="Unit price">
                  <LV v={a.final_terms.unit_price} />
                </KV>
                <KV k="Tooling">
                  <LV v={a.final_terms.tooling} />
                </KV>
                <KV k="Lead time">
                  <LV v={a.final_terms.lead_time_days} />
                </KV>
                <KV k="MOQ">
                  <span className="font-mono">{qty(a.final_terms.moq)}</span>
                </KV>
                <KV k="Payment">
                  <span className="text-sm">{a.final_terms.payment_terms}</span>
                </KV>
              </div>
            )}
          </section>

          <section className="relative rounded-md bg-surface px-5 pb-4 pt-4" aria-labelledby="cmp-h">
            <span className="absolute inset-y-3 left-0 w-[2px] rounded-full bg-fictional/50" aria-hidden />
            <header className="flex items-center justify-between gap-2">
              <h3 id="cmp-h" className="text-base font-semibold tracking-[-0.01em]">
                Latest quotes
              </h3>
              <LabelBadge label="fictional" small text />
            </header>
            <table className="mt-2 w-full table-fixed border-collapse text-sm">
              <thead>
                <tr>
                  <th className="w-[76px]" />
                  {latest.map((q) => {
                    const isRec = q.id === rec.quote_id;
                    return (
                      <th key={q.id} scope="col" className={`rounded-t-sm px-2 pb-1.5 pt-2 text-left align-bottom font-medium ${isRec ? "bg-accent-soft/70" : ""}`}>
                        {isRec && <span className="block text-2xs font-medium text-accent-ink">Recommended</span>}
                        <span className="block leading-5 text-ink">{short(name(q.factory_id))}</span>
                        <span className="block text-2xs font-normal text-ink-3">
                          <span className="font-mono">v{q.version}</span> {q.status}
                        </span>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    [`Unit @${qty(refQty)}`, (q: Quote) => <span className="font-mono font-medium text-ink">{usd(priceAt(q))}</span>],
                    ["Tooling", (q: Quote) => <span className="font-mono">{usd(q.tooling_usd, 0)}</span>],
                    ["MOQ", (q: Quote) => <span className="font-mono">{qty(q.moq)}</span>],
                    ["Lead time", (q: Quote) => <span className="font-mono">{q.lead_time_days} d</span>],
                    ["Terms", (q: Quote) => <span className="text-2xs leading-4 text-ink-2">{q.payment_terms}</span>],
                  ] as [string, (q: Quote) => ReactNode][]
                ).map(([k, cell], i, all) => (
                  <tr key={k} className="border-t border-line/70">
                    <th scope="row" className="py-2 pr-2 text-left align-top text-sm font-normal text-ink-3">
                      {k}
                    </th>
                    {latest.map((q) => (
                      <td key={q.id} className={`px-2 py-2 align-top text-ink-2 ${q.id === rec.quote_id ? `bg-accent-soft/70 ${i === all.length - 1 ? "rounded-b-sm" : ""}` : ""}`}>
                        {cell(q)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          {extras}
        </div>
      </ScrollArea>
    </div>
  );
}
