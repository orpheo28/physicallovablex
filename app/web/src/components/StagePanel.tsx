"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ComponentType } from "react";
import type { Project, StageResult, StageSummary } from "@/types/contracts";
import type { StageArtifact } from "@/lib/meta";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useNow } from "@/lib/useNow";
import { useEngineering } from "@/lib/studio";
import { fmtDate, PHASES, STAGES } from "@/lib/meta";
import { Generic } from "./Generic";
import { ScrollArea } from "./ScrollArea";
import { Arrow, Assumptions, Boundary, Btn, BtnLink, CachedBanner, Card, Chevron, CouldntLoad, Empty, ErrorBox, LayerTag, Loading, Spinner } from "./ui";
import { BriefView, DesignView, SpecView } from "./stages/Early";
import { CostsView, DFMView, MatchingView, ProductionView } from "./stages/Mid";
import { BrandView, FinancingView, LogisticsView, QCView, ToolingView } from "./stages/Late";
import { NegotiationView } from "./stages/Negotiation";
import type { StageViewProps } from "./stages/types";

const VIEWS: Record<number, unknown> = {
  1: BriefView,
  2: DesignView,
  3: SpecView,
  4: DFMView,
  5: CostsView,
  6: ProductionView,
  7: MatchingView,
  8: NegotiationView,
  9: ToolingView,
  10: QCView,
  11: LogisticsView,
  12: FinancingView,
  13: BrandView,
};

/** Views that lay out their own inner scroll regions (conversation panels) instead of one long scroll. */
const FILL = new Set([1, 8]);

export function StatusPill({ status }: { status: string }) {
  // Step status is not a trust label: plain text with a small ink / amber mark.
  if (status === "validated")
    return (
      <span className="inline-flex items-center gap-1 text-sm text-ink-2">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
          <path d="m3 8.5 3.2 3L13 4.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Validated
      </span>
    );
  if (status === "draft") return <span className="inline-flex items-center gap-1.5 text-sm text-estimate-ink"><span className="h-1.5 w-1.5 rounded-full bg-estimate" aria-hidden />Draft</span>;
  return <span className="text-sm text-ink-3">Not started</span>;
}

/** Compact status marker for lists: filled ink = validated, amber = draft, hollow = not started. */
export function StatusDot({ status }: { status: string }) {
  const label = status === "validated" ? "Validated" : status === "draft" ? "Draft" : "Not started";
  if (status === "validated")
    return (
      <span title={label} aria-label={label} className="flex h-3.5 w-3.5 items-center justify-center text-ink-2">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
          <path d="m3 8.5 3.2 3L13 4.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  if (status === "draft") return <span title={label} aria-label={label} className="h-3.5 w-3.5 rounded-full border-[1.5px] border-estimate bg-estimate-soft" />;
  return <span title={label} aria-label={label} className="h-3.5 w-3.5 rounded-full border border-line-2" />;
}

export function RunningIndicator({ start, label }: { start: number; label: string }) {
  const now = useNow(true);
  const s = Math.max(0, ((now || start) - start) / 1000);
  return (
    <div className="flex items-center gap-3 rounded-md bg-surface px-4 py-2.5 text-base" role="status">
      <Spinner />
      <span>{label}</span>
      <span className="font-mono text-sm text-ink-3">{s.toFixed(1)} s</span>
      <span className="h-[3px] flex-1 overflow-hidden rounded-full bg-paper-2">
        <span className="block h-full bg-accent transition-[width] duration-300" style={{ width: `${Math.min(95, (s / 30) * 100)}%` }} />
      </span>
    </div>
  );
}

/**
 * One stage, as a desktop panel: a fixed header (what this step does / what you decide here),
 * the stage content in its own scroll region, and a sticky footer with ← Previous and one primary Next.
 */
export function StagePanel({
  project,
  n,
  summary,
  nextSummary,
  onChanged,
  goto,
  onAutorun,
  autoRun,
  autorunNote,
}: {
  project: Project;
  n: number;
  summary?: StageSummary;
  nextSummary?: StageSummary;
  onChanged: () => void;
  goto: (n: number, opts?: { run?: boolean }) => void;
  onAutorun: () => void;
  /** Arrived via "Next" on a stage that has not run yet: run it now. */
  autoRun?: boolean;
  /** Shown above the content while an autofill run is in progress. */
  autorunNote?: React.ReactNode;
}) {
  const eng = useEngineering(project.id, n === 7 ? (summary?.updated_at ?? null) : undefined);
  const base = STAGES[n - 1];
  // Site-install products (solar…) are fitted by installers, not made by factories.
  const meta = n === 7 && eng.data?.partner_word === "installers" ? { ...base, title: "Installer shortlist", jargon: "Installer matching" } : base;
  const phase = PHASES.find((p) => p.stages.includes(n))!;
  // A step the server lists as not started has nothing to GET (it would 404): skip the request.
  const known404 = summary?.status === "not_started";
  // N3: on a showcase or a step the server lists as done, a 404 / error is a load failure: retried, then calm.
  const mustExist = !known404 && (!!summary || project.id.startsWith("demo_") || !!project.tags?.includes("Example"));
  const { data, error, status, loading, reload } = useApi<StageResult>(known404 ? null : `/projects/${project.id}/stages/${n}`, { retryNotFound: mustExist });
  const [override, setOverride] = useState<StageResult | null>(null);
  const [busy, setBusy] = useState<{ label: string; start: number } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Our own run/save result wins until the server has something newer (e.g. autofill re-ran this step).
  const fetched = status === 404 ? undefined : data;
  const newer = (x?: StageResult, y?: StageResult) => !!x && !!y && x.artifact.generated_at > y.artifact.generated_at;
  const result = override && !newer(fetched, override) ? override : fetched;
  const notRun = !override && ((status === 404 && !mustExist) || (known404 && !data));

  async function act(label: string, fn: () => Promise<void>) {
    setBusy({ label, start: Date.now() });
    setActionError(null);
    try {
      await fn();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  const run = (inputs: Record<string, unknown>) =>
    act(`Running step ${n} — ${meta.title}…`, async () => {
      const r = await api.post<StageResult>(`/projects/${project.id}/stages/${n}/run`, { inputs });
      setOverride(r);
      onChanged();
    });

  const save = (artifact: StageArtifact, validate = false) =>
    act(validate ? "Validating…" : "Saving…", async () => {
      const r = await api.put<StageResult>(`/projects/${project.id}/stages/${n}`, { artifact, validate_stage: validate });
      setOverride(r);
      onChanged();
    });

  const runOther = (m: number, inputs: Record<string, unknown>) =>
    act(`Running step ${m} — ${STAGES[m - 1]?.title}…`, async () => {
      await api.post<StageResult>(`/projects/${project.id}/stages/${m}/run`, { inputs });
      onChanged();
      goto(m);
    });

  // "Next" onto a stage that was never run: run it on arrival (once).
  const autoRan = useRef(false);
  useEffect(() => {
    if (!autoRun || autoRan.current || !notRun || busy) return;
    autoRan.current = true;
    void run({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRun, notRun, busy]);

  // The server updated this stage (autofill finished it): refetch in place, no remount, no flicker.
  const version = summary?.updated_at ?? null;
  const seen = useRef(version);
  useEffect(() => {
    if (seen.current === version) return;
    seen.current = version;
    if (!busy) reload();
  }, [version, busy, reload]);

  const View = VIEWS[n] as ComponentType<StageViewProps<StageArtifact>> | undefined;
  const artifact = result?.artifact;
  const st = result?.status ?? summary?.status ?? "not_started";
  const fill = FILL.has(n) && !!artifact && !!View && !!result;
  const next = n < 13 ? STAGES[n] : null;
  const prev = n > 1 ? STAGES[n - 2] : null;
  const nextNotRun = !!next && (nextSummary?.status ?? "not_started") === "not_started";

  const provenance = artifact
    ? artifact.generated_by === "fixture" && project.id.startsWith("demo_")
      ? "Pre-computed example"
      : artifact.generated_by === "fixture"
        ? `Cached example, ${fmtDate(artifact.generated_at)}`
        : `Generated by ${artifact.generated_by}, ${fmtDate(artifact.generated_at)}`
    : null;

  const extras = artifact ? (
    <div className="flex flex-col gap-3">
      <Assumptions items={artifact.assumptions} />
      <details className="group text-sm text-ink-3">
        <summary className="inline-flex cursor-pointer items-center gap-1.5 transition-colors hover:text-ink">
          <Chevron className="-rotate-90 group-open:rotate-0" /> All fields (raw view)
        </summary>
        <div className="mt-3 rounded-md bg-surface p-5 text-ink">
          <Generic value={artifact} />
        </div>
      </details>
    </div>
  ) : null;

  const notices = (
    <>
      {autorunNote}
      {busy && <RunningIndicator start={busy.start} label={busy.label} />}
      {actionError && <ErrorBox message={`Action failed: ${actionError}`} onRetry={() => setActionError(null)} />}
      {artifact && (artifact.fallback || result?.fallback) && <CachedBanner reason={artifact.fallback_reason} example={project.example} />}
    </>
  );

  const body = (
    <>
      {loading && !result && !notRun && <Loading text={`Loading step ${n}…`} />}
      {error && (status !== 404 || mustExist) && <CouldntLoad what={`step ${n}`} onRetry={reload} />}
      {notRun && !busy && (
        <Empty
          title="This step has not been run yet."
          body={`Run it to generate the ${meta.title.toLowerCase()}${n > 1 ? " from the previous steps" : ""}.`}
          action={
            <>
              <Btn variant="primary" onClick={() => run({})}>
                Run step {n} — {meta.title}
              </Btn>
              {n >= 2 && <Btn onClick={onAutorun}>Autofill the remaining steps</Btn>}
            </>
          }
        />
      )}
      {artifact && (
        <Boundary
          resetKey={`${n}-${artifact.generated_at}-${result?.status}`}
          fallback={
            <Card>
              <p className="mb-3 text-sm text-ink-3">Showing the raw artifact (this layout could not render it).</p>
              <Generic value={artifact} />
            </Card>
          }
        >
          {View && result ? (
            <View
              artifact={artifact}
              result={result}
              project={project}
              busy={!!busy}
              run={run}
              save={(a, v) => save(a, v)}
              runOther={runOther}
              goto={goto}
              onAutorun={onAutorun}
              extras={extras}
            />
          ) : (
            <Card>
              <Generic value={artifact} />
            </Card>
          )}
        </Boundary>
      )}
    </>
  );

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto]">
      <header className="px-8 pb-3 pt-4">
        <div className="flex items-start gap-6">
          <div className="min-w-0 flex-1">
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink-3">
              <span>
                Step <span className="font-mono">{n}</span> of <span className="font-mono">13</span> · {phase.title} · {meta.jargon}
              </span>
              <LayerTag layer={meta.layer} />
              <StatusPill status={st} />
              {provenance && <span>{provenance}</span>}
            </p>
            <h1 className="title mt-1 text-[26px] leading-[32px]">{meta.title}</h1>
          </div>
          <div className="flex shrink-0 gap-2 pt-0.5">
            {!notRun && (
              <Btn size="sm" variant="ghost" disabled={!!busy} onClick={() => run({})} title="Run this step again from the previous steps">
                {busy ? <Spinner /> : null} Re-run
              </Btn>
            )}
            {st !== "validated" && (
              <Btn size="sm" variant={st === "draft" ? "ink" : "ghost"} disabled={!!busy || !artifact} onClick={() => artifact && save(artifact, true)} title="Mark this step as checked by you">
                Validate
              </Btn>
            )}
          </div>
        </div>
        <dl className="mt-2 grid max-w-[1180px] grid-cols-2 gap-x-10 text-sm">
          <div>
            <dt className="text-ink-3">What this step does</dt>
            <dd className="mt-0.5 text-ink-2 text-pretty">{meta.does}</dd>
          </div>
          <div>
            <dt className="text-ink-3">What you decide here</dt>
            <dd className="mt-0.5 text-ink text-pretty">{meta.decide}</dd>
          </div>
        </dl>
      </header>

      {fill ? (
        <div className="flex min-h-0 flex-col gap-3 px-8 pb-4 pt-3">
          {notices}
          <div className="min-h-0 flex-1">{body}</div>
        </div>
      ) : (
        <ScrollArea className="h-full px-8 pb-8 pt-3" label={`${meta.title} content`}>
          <div className="flex flex-col gap-5">
            {notices}
            {body}
            {extras && <div className="mt-1">{extras}</div>}
          </div>
        </ScrollArea>
      )}

      <footer data-noprint className="flex h-14 items-center gap-3 px-8">
        {prev ? (
          <Btn variant="ghost" onClick={() => goto(n - 1)} className="-ml-3">
            <span aria-hidden>←</span>
            <span>
              Previous<span className="hidden text-ink-3 xl:inline">: {prev.title}</span>
            </span>
          </Btn>
        ) : (
          <span />
        )}
        <span className="ml-auto truncate text-sm text-ink-3">
          {next ? (nextNotRun ? "Not run yet — it runs when you continue" : `Step ${n + 1} of 13 is ready`) : "Last step — your Launch Dossier is ready"}
        </span>
        {next ? (
          <Btn variant={notRun || (n === 1 && nextNotRun) ? "secondary" : "primary"} disabled={!!busy} onClick={() => goto(n + 1, { run: nextNotRun })}>
            Next: {next.title} <Arrow />
          </Btn>
        ) : (
          <BtnLink href={`/projects/${project.id}/wow?dossier=1`} variant="primary">
            Next: Overview &amp; Launch Dossier <Arrow />
          </BtnLink>
        )}
      </footer>
    </div>
  );
}

export function AutorunNote({ step, through, projectId }: { step: number | null; through: number; projectId: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md bg-surface px-4 py-2.5 text-sm" role="status">
      <Spinner className="text-accent" />
      <span>
        Autofill is running{step ? (
          <>
            {" "}— step <span className="font-mono">{step}</span> of {through}, {STAGES[step - 1]?.title}
          </>
        ) : null}
        . This page updates as steps finish.
      </span>
      <Link href={`/projects/${projectId}?autorun=${through}`} className="ml-auto font-medium text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink">
        View progress
      </Link>
    </div>
  );
}
