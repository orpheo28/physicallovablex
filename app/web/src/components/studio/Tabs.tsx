"use client";

import { useEffect, useState } from "react";
import { API_BASE, fileUrl } from "@/lib/api";
import type { Version } from "@/types/contracts";
import type { Engineering, Verdict } from "@/lib/studio";
import { BUILD_TEXT } from "@/lib/showcase";
import { ScrollArea } from "../ScrollArea";
import { LabelBadge, LV, Pill, Severity, Spinner } from "../ui";

export type TabId = "product" | "engineering" | "code" | "firmware" | "drawings";

const VERDICT: Record<Verdict, { tone: "green" | "amber" | "red" | "zinc"; text: string }> = {
  pass: { tone: "green", text: "Pass" },
  warn: { tone: "amber", text: "Warn" },
  fail: { tone: "red", text: "Fail" },
  info: { tone: "zinc", text: "Info" },
};

function Soon() {
  return (
    <div className="flex h-full items-center justify-center text-sm text-ink-3">Coming with the engineering layer.</div>
  );
}

function Section({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <section>
      <div className="flex items-center justify-between pb-0.5">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {right}
      </div>
      <div className="mt-2">{children}</div>
    </section>
  );
}

function CheckList({ checks }: { checks: Engineering["checks"] }) {
  return (
    <ul className="divide-y divide-line">
      {checks.map((c) => (
        <li key={c.id} className="grid grid-cols-[56px_minmax(0,1fr)_auto] items-start gap-3 py-2 text-sm" title={c.formula}>
          <span className="flex pt-0.5">
            <Pill tone={VERDICT[c.verdict].tone} dot>
              {VERDICT[c.verdict].text}
            </Pill>
          </span>
          <span className="min-w-0">
            <span className="text-ink">{c.name}</span>
            {c.threshold && <span className="block text-2xs text-ink-3">{c.threshold}</span>}
          </span>
          <LV v={c.value} />
        </li>
      ))}
    </ul>
  );
}

/** Engineering (W20): physics checks, standards, power budget, prototype path — each figure with its label. */
type EngState = { data?: Engineering; error?: string; loading: boolean; available: boolean };

/** How this product gets built (W21 build_strategy): full design, module assembly or ODM customisation. */
export function BuildStrategyBlock({ e }: { e: Engineering }) {
  const bs = e.build_strategy;
  if (!bs) return null;
  const odm = bs.strategy === "odm_customization";
  return (
    <section className="rounded-md bg-surface p-5">
      <p className="micro">Build path</p>
      <p className="mt-1 text-md font-medium">{bs.title || BUILD_TEXT[bs.strategy]}</p>
      <p className="mt-1 text-sm text-ink-2">{bs.explanation}</p>
      {bs.path.length > 0 && (
        <ol className={`mt-3 flex flex-col gap-1 rounded-sm px-3 py-2 text-sm ${odm ? "bg-estimate-soft text-estimate-ink" : "bg-paper-2/60 text-ink-2"}`}>
          {bs.path.map((step, i) => (
            <li key={step} className="grid grid-cols-[18px_1fr]">
              <span className="font-mono text-2xs">{i + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      )}
      <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
        <div title={bs.moq.source_or_assumption}>
          <p className="micro">MOQ</p>
          <p className="mt-0.5">
            <LV v={bs.moq} />
          </p>
        </div>
        <div>
          <p className="micro">Entry cost</p>
          <p className="mt-0.5">
            <LV v={bs.entry_cost} />
          </p>
        </div>
        <div>
          <p className="micro">Lead time</p>
          <p className="mt-0.5">
            <LV v={bs.lead_time} />
          </p>
        </div>
      </div>
      {(bs.customisable.length > 0 || bs.not_customisable.length > 0) && (
        <div className="mt-3 grid grid-cols-2 gap-4">
          {[
            ["You can customise", bs.customisable],
            ["Stays as the base", bs.not_customisable],
          ].map(([title, items]) =>
            (items as string[]).length ? (
              <div key={title as string}>
                <p className="micro">{title as string}</p>
                <ul className="mt-1 flex flex-wrap gap-1">
                  {(items as string[]).map((i) => (
                    <li key={i} className="rounded-full bg-paper-2 px-2 py-px text-2xs text-ink-2">
                      {i}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null,
          )}
        </div>
      )}
      {bs.certifications_note && <p className="mt-3 text-2xs text-ink-3">Certifications: {bs.certifications_note}</p>}
    </section>
  );
}

export function EngineeringTab({ eng }: { eng: EngState }) {
  const { data: e, error, loading, available } = eng;
  if (!available) return <Soon />;
  if (loading && !e)
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
        <Spinner /> Computing the engineering checks…
      </div>
    );
  if (!e) return <div className="flex h-full items-center justify-center text-sm text-ink-3">{error ? `Engineering unavailable: ${error}` : "No engineering data yet."}</div>;
  const counts = e.checks.reduce<Record<string, number>>((m, c) => ((m[c.verdict] = (m[c.verdict] ?? 0) + 1), m), {});
  // C2: measured assembly checks (interference, clearance, screw engagement, fasteners) get their own group
  const assembly = e.checks.filter((c) => c.domain === "assembly");
  const physics = e.checks.filter((c) => c.domain !== "assembly");
  return (
    <ScrollArea className="h-full pr-2" label="Engineering">
      <div className="flex flex-col gap-5 pb-2">
        <BuildStrategyBlock e={e} />
        <p className="text-sm text-ink-2">
          <span className="font-medium text-ink">{e.category_title}</span> · checks {counts.pass ?? 0} pass · {counts.warn ?? 0} warn · {counts.fail ?? 0} fail
        </p>
        <Section title={`Physics checks · ${physics.length}`}>
          <CheckList checks={physics} />
        </Section>
        {assembly.length > 0 && (
          <Section title={`Assembly · ${assembly.length}`}>
            {e.assembly?.summary && <p className="mb-1.5 text-sm text-ink-2">{e.assembly.summary}</p>}
            <CheckList checks={assembly} />
          </Section>
        )}
        {e.electronics && (
          <Section
            title="Power budget"
            right={e.electronics.battery_life ? <span className="flex items-center gap-2 text-sm text-ink-2">Battery life <LV v={e.electronics.battery_life} /></span> : undefined}
          >
            <p className="mb-1.5 text-sm text-ink-2">
              {e.electronics.mcu_part}
              {e.electronics.radio.length ? ` · ${e.electronics.radio.join(", ")}` : ""} · average <LV v={e.electronics.average_current} />
            </p>
            <ul className="divide-y divide-line">
              {e.electronics.power_budget.map((l) => (
                <li key={l.block + l.part} className="flex items-center justify-between gap-3 py-1.5 text-sm">
                  <span className="min-w-0 truncate">
                    {l.block} <span className="text-ink-3">· {l.part}</span>
                  </span>
                  <LV v={l.average_current} />
                </li>
              ))}
            </ul>
            <p className="mt-1.5 text-2xs text-ink-3">{e.electronics.pcb_note}</p>
          </Section>
        )}
        <Section title={`Standards · ${e.standards.length}`}>
          <ul className="divide-y divide-line">
            {e.standards.map((s) => (
              <li key={s.code} className="py-2 text-sm">
                <p className="flex flex-wrap items-center gap-2">
                  {s.url ? (
                    <a href={s.url} target="_blank" rel="noreferrer" className="font-mono text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink">
                      {s.code}
                    </a>
                  ) : (
                    <span className="font-mono">{s.code}</span>
                  )}
                  <span className="text-ink-2">{s.title}</span>
                  <LabelBadge label={s.citation_label} tip={s.citation_note} small />
                </p>
                <p className="mt-0.5 text-2xs text-ink-3">{s.applies_because}</p>
              </li>
            ))}
          </ul>
        </Section>
        {e.risks.length > 0 && (
          <Section title={`Design risks · ${e.risks.length}`}>
            <ul className="divide-y divide-line">
              {e.risks.map((r) => (
                <li key={r.id} className="grid grid-cols-[76px_minmax(0,1fr)] gap-3 py-2 text-sm">
                  <Severity level={r.severity} />
                  <span>
                    {r.risk}
                    <span className="block text-2xs text-ink-3">Fix: {r.mitigation}</span>
                  </span>
                </li>
              ))}
            </ul>
          </Section>
        )}
        <Section title="Prototype path" right={<span className="flex items-center gap-2 text-sm text-ink-2"><LV v={e.prototype.total_cost} /> · <LV v={e.prototype.timeline_weeks} /></span>}>
          <p className="text-sm text-ink-2">
            {e.prototype.units} units · {e.prototype.enclosure_method}
          </p>
          <ol className="mt-1.5 flex flex-col gap-1 text-sm">
            {e.prototype.assembly_steps.map((s, i) => (
              <li key={s} className="grid grid-cols-[20px_1fr]">
                <span className="font-mono text-2xs text-ink-3">{i + 1}</span>
                {s}
              </li>
            ))}
          </ol>
        </Section>
      </div>
    </ScrollArea>
  );
}

// ------------------------------------------------------------------ CAD code (W19 route, W21 fields)

// Version.cad_pending / cad_note and VersionPreview.code_url / cad_label / cad_source are W21 fields. The AI program
// index k in code_url (/cad/code/{k}) is not the version number: colour-only versions keep the previous program.
type VersionX = Version & { attempts?: unknown; preview: (Version["preview"] & { attempts?: unknown; code_attempts?: unknown }) | null };

/** Self-repair count, only if the API reports attempts (a number of tries or a list): N× repaired = tries − 1. */
function repairs(v: VersionX): number | null {
  // W21c: Version.cad_attempts (0 = no AI CAD run) and cad_repairs.
  if (typeof v.cad_attempts === "number" && v.cad_attempts > 0) return typeof v.cad_repairs === "number" ? v.cad_repairs : Math.max(0, v.cad_attempts - 1);
  const raw = v.preview?.code_attempts ?? v.preview?.attempts ?? v.attempts;
  const n = typeof raw === "number" ? raw : Array.isArray(raw) ? raw.length : null;
  return n === null ? null : Math.max(0, n - 1);
}

function codePath(projectId: string, v: VersionX | undefined): { path: string; known: boolean } | null {
  if (!v) return null;
  const url = v.preview?.code_url;
  if (url) return { path: url.startsWith("/backend/") ? url.slice("/backend".length) : url, known: true };
  return { path: `/projects/${projectId}/cad/code/${v.n}`, known: false };
}

const programNo = (url: string | null | undefined) => (url ? /\/cad\/code\/(\d+)/.exec(url)?.[1] ?? null : null);

/** Fetch a program: a listed code_url directly; the conventional route only after a server-side existence check (no console 404). */
function useCode(target: { path: string; known: boolean } | null, enabled: boolean) {
  const [st, setSt] = useState<{ key: string; code: string | null }>({ key: "", code: null });
  const key = enabled && target ? target.path : "";
  useEffect(() => {
    if (!enabled || !target) return;
    let live = true;
    const get = () => fetch(`${API_BASE}${target.path}`, { cache: "no-store" }).then(async (r) => (r.ok ? r.text() : null));
    const run = target.known
      ? get()
      : fetch(`/file-status?path=${encodeURIComponent(target.path)}`, { cache: "no-store" })
          .then((r) => r.json() as Promise<{ exists?: boolean }>)
          .then((j) => (j.exists ? get() : null));
    run.then((code) => live && setSt({ key: target.path, code })).catch(() => live && setSt({ key: target.path, code: null }));
    return () => {
      live = false;
    };
  }, [enabled, target?.path, target?.known]); // eslint-disable-line react-hooks/exhaustive-deps
  return { loading: !!key && st.key !== key, code: st.key === key ? st.code : null };
}

type Row = { t: "same" | "add" | "del"; text: string; a?: number; b?: number };

/** Line diff (LCS). Programs are a few hundred lines, so the O(n·m) table is fine. */
export function lineDiff(oldText: string, newText: string): Row[] {
  const A = oldText.replace(/\n$/, "").split("\n");
  const B = newText.replace(/\n$/, "").split("\n");
  const n = A.length;
  const m = B.length;
  const L: Uint16Array[] = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const rows: Row[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) rows.push({ t: "same", text: B[j], a: ++i, b: ++j });
    else if (L[i + 1][j] >= L[i][j + 1]) rows.push({ t: "del", text: A[i], a: ++i });
    else rows.push({ t: "add", text: B[j], b: ++j });
  }
  while (i < n) rows.push({ t: "del", text: A[i], a: ++i });
  while (j < m) rows.push({ t: "add", text: B[j], b: ++j });
  return rows;
}

/** The AI-written build123d program of this version (W19), read-only with line numbers, and a diff vs the previous version. */
export function CadCodeTab({ projectId, version, versions, available }: { projectId: string; version: Version | undefined; versions: Version[]; available: boolean }) {
  const v = version as VersionX | undefined;
  const [diff, setDiff] = useState(false);
  // Diff against the latest earlier version whose program differs (e.g. v4's 8 mm edit vs the v1 program).
  const prev = versions.filter((x) => x.status === "done" && v && x.n < v.n && (x.preview?.code_url ?? null) !== (v.preview?.code_url ?? null)).at(-1) as
    | VersionX
    | undefined;
  const k = programNo(v?.preview?.code_url) ?? String(v?.n ?? "");
  const pk = programNo(prev?.preview?.code_url) ?? String(prev?.n ?? "");
  const shared = v?.preview?.code_url ? versions.filter((x) => x.n !== v.n && x.preview?.code_url === v.preview?.code_url).map((x) => x.n) : [];
  const cur = useCode(codePath(projectId, v), available && !!v && !v.cad_pending);
  const old = useCode(codePath(projectId, prev), available && diff && !!prev);
  if (!available) return <Soon />;
  if (!v) return <Soon />;
  if (v.cad_pending || v.status === "running")
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
        <Spinner /> Writing CAD code…
      </div>
    );
  if (cur.loading)
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
        <Spinner /> Loading the CAD program…
      </div>
    );
  if (!cur.code)
    return (
      <div className="flex h-full flex-col items-center justify-center gap-1 text-center text-sm text-ink-3">
        <span>No CAD program for v{v.n}.</span>
        <span>This version was built from a parametric shape family (build123d templates), not generated code.</span>
      </div>
    );
  const fixes = repairs(v);
  const rows: Row[] = diff && old.code ? lineDiff(old.code, cur.code) : cur.code.replace(/\n$/, "").split("\n").map((text, i) => ({ t: "same" as const, text, b: i + 1 }));
  const added = rows.filter((r) => r.t === "add").length;
  const removed = rows.filter((r) => r.t === "del").length;
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-md bg-surface">
      <div className="flex items-center gap-3 px-4 py-2.5 text-2xs text-ink-3">
        <span className="shrink-0 whitespace-nowrap font-mono">model_v{k}.py · build123d · read-only</span>
        <span className="min-w-0 truncate" title={v.cad_note ?? undefined}>
          {v.preview?.cad_source?.startsWith("seed:")
            ? `Parametric family program (${v.preview.cad_source.slice(5)})`
            : `Generated by AI${v.preview?.cad_source?.startsWith("llm:") ? ` (${v.preview.cad_source.slice(4)})` : ""}`}
          {fixes !== null ? (fixes > 0 ? ` · Self-repaired ${fixes}×` : " · Ran first time, no self-repair needed") : ""}
          {shared.length > 0 ? ` · also used by ${shared.map((x) => `v${x}`).join(", ")} (no geometry change)` : ""}
        </span>
        <span className="ml-auto shrink-0 whitespace-nowrap font-mono">{diff && old.code ? `+${added} −${removed} vs program ${pk}` : `${rows.length} lines`}</span>
        {prev && (
          <button
            onClick={() => setDiff((d) => !d)}
            aria-pressed={diff}
            className={`press shrink-0 whitespace-nowrap rounded-full px-2.5 py-0.5 font-medium ${diff ? "bg-ink text-white" : "bg-paper-2 text-ink-2 hover:text-ink"}`}
          >
            Diff vs v{prev.n}
          </button>
        )}
      </div>
      {diff && old.loading && <p className="px-3 py-1.5 text-2xs text-ink-3">Loading v{prev?.n}…</p>}
      {diff && !old.loading && !old.code && <p className="px-3 py-1.5 text-2xs text-ink-3">v{prev?.n} has no program to compare with.</p>}
      {v.preview?.cad_label && <p className="mx-4 mb-1 rounded-sm bg-paper px-3 py-1.5 text-2xs text-ink-2">{v.preview.cad_label}</p>}
      {v.cad_note && <p className="mx-4 mb-1 rounded-sm bg-estimate-soft px-3 py-1.5 text-2xs text-estimate-ink">{v.cad_note}</p>}
      <ScrollArea className="flex-1" label="CAD program">
        <pre className="font-mono text-[12px] leading-[19px]">
          {rows.map((r, i) => (
            <div
              key={i}
              className={`grid grid-cols-[40px_40px_16px_minmax(0,1fr)] ${r.t === "add" ? "bg-accent-soft" : r.t === "del" ? "bg-paper-2 text-ink-3 line-through decoration-ink-4" : "hover:bg-sunken"}`}
            >
              <span className="select-none pr-2 text-right text-ink-4">{diff ? (r.a ?? "") : ""}</span>
              <span className="select-none pr-2 text-right text-ink-4">{r.b ?? ""}</span>
              <span className={`select-none ${r.t === "add" ? "text-accent-ink" : "text-ink-4"}`}>{r.t === "add" ? "+" : r.t === "del" ? "−" : ""}</span>
              <code className="whitespace-pre-wrap break-words pr-3">{r.text || " "}</code>
            </div>
          ))}
        </pre>
      </ScrollArea>
    </div>
  );
}

/** Firmware project from the engineering artifact: framework, files, download (generated, not compiled). */
export function FirmwareTab({ eng }: { eng: EngState }) {
  const { data: e, loading, available } = eng;
  if (!available) return <Soon />;
  if (loading && !e)
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
        <Spinner /> Loading…
      </div>
    );
  const f = e?.firmware;
  if (!f) return <div className="flex h-full items-center justify-center text-sm text-ink-3">No firmware for this product (no electronics).</div>;
  const href = fileUrl(f.url);
  return (
    <ScrollArea className="h-full" label="Firmware">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-md font-medium capitalize">{f.framework}</span>
          <span className="text-sm text-ink-2">
            {f.mcu_family.toUpperCase()} · {f.connectivity}
          </span>
          {href && (
            <a href={href} download className="ml-auto inline-flex h-8 items-center gap-2 rounded border border-ink bg-ink px-3 text-sm font-medium text-white hover:bg-[#2a2a2a]">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
                <path d="M8 2v8.5M4.5 7 8 10.5 11.5 7M3 13.5h10" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Download firmware.zip
            </a>
          )}
        </div>
        <p className="rounded-sm bg-estimate-soft px-3 py-2 text-sm text-estimate-ink">
          {f.note}. Generated by {f.generated_by}
          {f.pending_llm ? " — an AI-written version is being generated." : "."}
        </p>
        <ul className="divide-y divide-line rounded-md bg-surface px-1 font-mono text-sm">
          {f.files.map((x) => (
            <li key={x} className="px-3 py-1.5">
              {x}
            </li>
          ))}
        </ul>
      </div>
    </ScrollArea>
  );
}
