"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Version, VersionChange } from "@/types/contracts";
import { useNow } from "@/lib/useNow";
import { animeNow, loadAnime, reducedMotion } from "@/lib/motion";
import { ScrollArea } from "../ScrollArea";
import { LabelBadge, Spinner } from "../ui";

const STEPS = ["CAD", "BOM", "Costs", "DFM", "Factories"];

const hhmm = (s: string | null) => {
  if (!s) return "";
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
};
const secs = (v: Version) => (v.finished_at ? Math.max(0, (new Date(v.finished_at).getTime() - new Date(v.created_at).getTime()) / 1000) : null);

const fmtMoney = (v: { value: number; unit: string }) => (v.unit === "USD" ? `$${v.value.toFixed(2)}` : `${v.value} ${v.unit}`);

/** Area words for changes whose label alone is not self-explanatory (W21c: "Component upgraded", "Uses the existing …"). */
function isComponentKind(c: VersionChange) {
  return c.area === "component" || c.area === "certification" || c.area === "feature";
}

/**
 * One change as a quiet row (W26): label, before → after, trust dot. A component with a structured risk
 * (W21b: expensive, low stock…) gets an amber line with its reasons and the LCSC alternative.
 */
function ChangeRow({ c }: { c: VersionChange }) {
  const risk = c.risk && c.risk.level !== "low" ? c.risk : null;
  const long = (c.after?.length ?? 0) + (c.before?.length ?? 0) > 34 || isComponentKind(c);
  return (
    <li data-chip className="flex min-w-0 flex-col gap-1 py-1.5">
      {/* Inline flow, so the trust dot stays glued to the end of the value when a long value wraps. */}
      <p className="min-w-0 text-sm leading-5">
        <span className={`text-ink-2 ${long ? "block" : "mr-2"}`}>{c.label}</span>
        {c.before && (
          <>
            <span className="break-words text-ink-3 line-through decoration-ink-4/70">{c.before}</span>
            <span className="mx-1.5 text-ink-4" aria-label="to">
              →
            </span>
          </>
        )}
        {c.after && <span className="break-words font-medium text-ink">{c.after}</span>}
        <span className="ml-1.5 inline-block">
          <LabelBadge label={c.label_kind} small />
        </span>
      </p>
      {risk && (
        <span className="flex flex-col gap-0.5 rounded-sm bg-estimate-soft px-2.5 py-1.5 text-2xs text-estimate-ink">
          <span className="flex items-start gap-1.5 font-medium">
            <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden className="mt-[3px] shrink-0">
              <path d="M8 2 1.5 13.5h13L8 2Z" strokeLinejoin="round" />
              <path d="M8 6.5v3.2M8 11.6v.2" strokeLinecap="round" />
            </svg>
            {risk.level === "high" ? "High" : "Medium"} component risk{risk.reasons.length ? `: ${risk.reasons.join(" · ")}` : ""}
          </span>
          {risk.alternative ? (
            <span className="flex flex-wrap items-center gap-x-1.5 pl-[17px] text-ink-2">
              Cheaper alternative: <span className="font-medium text-ink">{risk.alternative.part}</span>
              <span className="font-mono">{risk.alternative.lcsc_pn}</span>
              <span className="font-mono text-ink">{fmtMoney(risk.alternative.price)}</span>
              <LabelBadge label={risk.alternative.label} tip={risk.alternative.price.source_or_assumption} small />
            </span>
          ) : (
            <span className="pl-[17px] text-ink-3">No cheaper in-stock alternative in LCSC</span>
          )}
        </span>
      )}
    </li>
  );
}

/** "Working on v4…": the recompute chain, lit in its usual order while the job runs (the server reports only running / done). */
function Working({ v, first }: { v: Version; first: boolean }) {
  const now = useNow(true, 200);
  const start = new Date(v.created_at).getTime();
  const elapsed = now ? Math.max(0, (now - start) / 1000) : 0;
  const typical = first ? 27 : 6; // measured live: start 26.6 s, refines 3.8-7.1 s
  const at = Math.min(STEPS.length - 1, Math.floor(elapsed / (typical / STEPS.length)));
  return (
    <div className="mt-1.5 flex flex-col gap-1">
      <ol className="flex flex-wrap items-center gap-x-1.5 text-sm" aria-label="Recomputing">
        {STEPS.map((s, i) => (
          <li key={s} className={`flex items-center gap-1.5 transition-colors duration-300 ${i < at ? "text-ink-2" : i === at ? "font-medium text-ink" : "text-ink-4"}`}>
            {i > 0 && <span className="text-ink-4">›</span>}
            {i === at && <Spinner className="!h-3 !w-3 text-accent" />}
            {s}
          </li>
        ))}
      </ol>
      <p className="text-2xs text-ink-3">
        <span className="font-mono">{elapsed.toFixed(0)} s</span> · usually {first ? "about 30 s for the first version" : "4–7 s"}
      </p>
    </div>
  );
}

function Answer({
  v,
  selected,
  prevN,
  onPreview,
  onRestore,
  onRetry,
  canRestore,
  cached,
}: {
  v: Version;
  selected: boolean;
  prevN: number | null;
  onPreview: () => void;
  onRestore: () => void;
  onRetry: () => void;
  canRestore: boolean;
  cached?: boolean;
}) {
  const running = v.status === "running";
  // F6: v1 of a project whose brief is a pre-computed example describes that example, not the prompt.
  const fromExample = cached && v.n === 1 && v.status === "done";
  const failed = v.status === "failed";
  const t = secs(v);
  const actions = v.status === "done" && !v.is_current;
  return (
    <div
      data-vcard={v.n}
      className={`group -mx-3 rounded-md px-3 py-2.5 transition-colors duration-150 ${selected ? "bg-surface" : actions ? "hover:bg-surface/60" : ""}`}
    >
      <p className="text-base leading-6 text-ink">
        {running ? `Working on v${v.n}…` : failed ? "Nothing changed." : fromExample ? "First version from a pre-computed example" : v.summary || `Version ${v.n}`}
      </p>
      {fromExample && <p className="mt-0.5 text-sm text-ink-3">AI was unavailable, so this is not built from your prompt: {v.summary}</p>}

      {running && <Working v={v} first={v.n === 1} />}

      {failed && (
        <div className="mt-1 text-sm text-ink-2">
          <p>{v.error ?? "This change could not be applied."}</p>
          {prevN !== null && !/still current/i.test(v.error ?? "") && <p className="mt-1 text-ink-3">v{prevN} is still the current product.</p>}
          <button onClick={onRetry} className="mt-1.5 text-sm font-medium text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink">
            Put this prompt back in the box
          </button>
        </div>
      )}

      {v.status === "done" && v.changes.length > 0 && (
        <ul className="mt-1 flex flex-col divide-y divide-line/70">
          {v.changes.map((c, i) => (
            <ChangeRow key={`${c.label}-${i}`} c={c} />
          ))}
        </ul>
      )}
      {v.status === "done" && v.n > 1 && !v.changes.some((c) => c.area === "cost" || c.area === "price") && (
        // F11: say "no change" instead of silence (PRD §8.2).
        <p className="mt-1 text-2xs text-ink-3">Cost unchanged{!v.changes.some((c) => c.area === "certification") ? " · certifications unchanged" : ""}</p>
      )}
      {v.status === "done" && (v.render_pending || v.background_pending) && (
        <p className="mt-1.5 flex items-center gap-2 text-2xs text-ink-3">
          <Spinner className="!h-2.5 !w-2.5" />
          {[v.render_pending && "rendering the new look", v.background_pending && "AI design review and production plan updating"].filter(Boolean).join(" · ")}
        </p>
      )}

      <div className="mt-1.5 flex min-h-6 items-center gap-3 text-2xs text-ink-3">
        <span className="font-mono">v{v.n}</span>
        {!running && <span className="font-mono">{hhmm(v.created_at)}</span>}
        {t !== null && !failed && <span>built in <span className="font-mono">{t.toFixed(1)} s</span></span>}
        {v.is_current && (
          <span className="flex items-center gap-1.5 font-medium text-ink">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
            Current
          </span>
        )}
        {actions && (
          <span className={`ml-auto flex items-center gap-1 transition-opacity duration-150 ${selected ? "opacity-100" : "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100"}`}>
            <button onClick={onPreview} aria-pressed={selected} className="press rounded-sm px-2 py-1 text-sm font-medium text-ink-2 hover:bg-paper-2 hover:text-ink">
              {selected ? "Previewing" : "Preview"}
            </button>
            {canRestore && (
              <button onClick={onRestore} className="press rounded-sm px-2 py-1 text-sm font-medium text-ink-2 hover:bg-paper-2 hover:text-ink">
                Restore v{v.n}
              </button>
            )}
          </span>
        )}
      </div>
    </div>
  );
}

/** Left pane: the conversation. The founder's prompts, and each answer is a real product version. */
export function Conversation({
  versions,
  prompt,
  selected,
  busy,
  onSelect,
  onRestore,
  onSend,
  sending,
  sendError,
  suggestions,
  cached,
}: {
  versions: Version[];
  prompt: string;
  selected: number | null;
  busy: boolean;
  onSelect: (n: number | null) => void;
  onRestore: (n: number) => void;
  onSend: (message: string) => Promise<boolean>;
  sending: boolean;
  sendError: string | null;
  suggestions: string[];
  cached?: boolean;
}) {
  const [draft, setDraft] = useState("");
  const thread = useRef<HTMLDivElement>(null);
  const running = versions.some((v) => v.status === "running");
  const current = versions.find((v) => v.is_current)?.n ?? null;

  // Follow the latest turn.
  const tail = versions.map((v) => `${v.n}:${v.status}`).join(",");
  useLayoutEffect(() => {
    const el = thread.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [tail]);

  // Motion: a new version card slides in; when a version completes, its change chips stagger in.
  const seen = useRef<Map<number, string> | null>(null);
  useEffect(() => void loadAnime(), []);
  useLayoutEffect(() => {
    const el = thread.current;
    const before = seen.current;
    seen.current = new Map(versions.map((v) => [v.n, v.status]));
    if (!el || before === null || reducedMotion()) return;
    const a = animeNow();
    if (!a) return;
    for (const v of versions) {
      const card = el.querySelector<HTMLElement>(`[data-vcard="${v.n}"]`);
      if (!card) continue;
      if (!before.has(v.n)) a.animate(card, { opacity: [0, 1], translateY: [6, 0], duration: 360, ease: "outExpo" });
      else if (before.get(v.n) === "running" && v.status === "done") {
        const chips = card.querySelectorAll<HTMLElement>("[data-chip]");
        if (chips.length) a.animate(chips, { opacity: [0, 1], translateY: [3, 0], duration: 300, delay: a.stagger(40), ease: "outExpo" });
      }
    }
  }, [tail, versions]);

  async function send(text: string) {
    const m = text.trim();
    if (!m || sending) return;
    const ok = await onSend(m);
    if (ok) setDraft("");
  }

  const ready = !!draft.trim() && !sending;

  return (
    <section aria-label="Studio conversation" className="flex h-full min-h-0 flex-col">
      <ScrollArea ref={thread} className="flex-1 pb-4 pl-6 pr-5 pt-2" label="Versions">
        <ol className="flex flex-col gap-5">
          {versions.map((v, i) => {
            const prev = [...versions.slice(0, i)].reverse().find((x) => x.status === "done");
            return (
              <li key={v.n} className="flex flex-col gap-2">
                <div className="flex justify-end">
                  <p className="max-w-[85%] rounded-lg rounded-br-sm bg-paper-2 px-3.5 py-2 text-base text-ink">{v.n === 1 && /studio start/i.test(v.message) ? prompt : v.message}</p>
                </div>
                <Answer
                  v={v}
                  selected={selected === v.n}
                  prevN={v.status === "failed" ? (current ?? prev?.n ?? null) : null}
                  onPreview={() => onSelect(selected === v.n ? null : v.n)}
                  onRestore={() => onRestore(v.n)}
                  onRetry={() => setDraft(v.message)}
                  canRestore={!busy}
                  cached={cached}
                />
              </li>
            );
          })}
        </ol>
      </ScrollArea>

      <div className="px-4 pb-4 pt-1">
        {suggestions.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5 px-1 max-[1439px]:[&>button:nth-child(n+3)]:hidden">
            {suggestions.slice(0, 3).map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                disabled={sending || running}
                className="press h-7 rounded-full bg-paper-2/80 px-3 text-sm text-ink-2 hover:bg-paper-2 hover:text-ink disabled:opacity-45"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        <form
          className="rounded-lg bg-surface shadow-float transition-shadow duration-150 focus-within:shadow-[0_0_0_1px_rgb(17_17_17/0.18),0_2px_4px_rgb(17_17_17/0.04),0_12px_32px_-12px_rgb(17_17_17/0.18)]"
          onSubmit={(e) => {
            e.preventDefault();
            send(draft);
          }}
        >
          <textarea
            name="change"
            autoComplete="off"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                send(draft);
              }
            }}
            rows={1}
            maxLength={1000}
            placeholder={running ? "Wait for this version, or type the next change…" : "Describe a change: “make it pink”, “thinner, 8 mm”…"}
            aria-label="Describe a change"
            className="block max-h-40 min-h-[44px] w-full resize-none rounded-t-lg bg-transparent px-4 pb-0 pt-3 text-base text-ink outline-none [field-sizing:content] placeholder:text-ink-3 focus-visible:outline-none min-[1440px]:min-h-[64px]"
          />
          <div className="flex items-center gap-2 px-3 pb-2">
            <span className="min-w-0 flex-1 truncate pl-1 text-2xs text-ink-3">
              {sendError ? <span className="text-danger">{sendError}</span> : <>Enter to send · Shift+Enter for a new line{running ? " · changes queue in order" : ""}</>}
            </span>
            <button
              type="submit"
              aria-label="Send"
              disabled={!ready}
              className={`press flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${ready ? "bg-ink text-white hover:bg-[#2a2a2a]" : "bg-paper-2 text-ink-4"} disabled:cursor-not-allowed`}
            >
              {sending ? (
                <Spinner />
              ) : (
                <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
                  <path d="M8 13V3M3.5 7.5 8 3l4.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
