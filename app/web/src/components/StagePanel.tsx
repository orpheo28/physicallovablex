"use client";

import { useState, type ComponentType } from "react";
import type { Project, StageResult, StageSummary } from "@/types/contracts";
import type { StageArtifact } from "@/lib/meta";
import { api, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useNow } from "@/lib/useNow";
import { fmtDate, STAGES } from "@/lib/meta";
import { Generic } from "./Generic";
import { Assumptions, Boundary, Btn, CachedBanner, Card, Chevron, Empty, ErrorBox, LayerTag, Loading, Pill, Spinner } from "./ui";
import { BriefView, DesignView, SpecView } from "./stages/Early";
import { CostsView, DFMView, MatchingView, ProductionView } from "./stages/Mid";
import { BrandView, FinancingView, LogisticsView, NegotiationView, QCView, ToolingView } from "./stages/Late";
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

export function StatusPill({ status }: { status: string }) {
  if (status === "validated") return <Pill tone="green" dot>Validated</Pill>;
  if (status === "draft") return <Pill tone="amber" dot>Draft</Pill>;
  return <Pill>Not started</Pill>;
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
    <div className="flex items-center gap-3 rounded-md border border-line bg-surface px-4 py-2.5 text-base" role="status">
      <Spinner />
      <span>{label}</span>
      <span className="font-mono text-sm text-ink-3">{s.toFixed(1)} s</span>
      <span className="h-[3px] flex-1 overflow-hidden rounded-full bg-paper-2">
        <span className="block h-full bg-accent transition-all duration-300" style={{ width: `${Math.min(95, (s / 30) * 100)}%` }} />
      </span>
    </div>
  );
}

export function StagePanel({
  project,
  n,
  summary,
  onChanged,
  goto,
  onAutorun,
}: {
  project: Project;
  n: number;
  summary?: StageSummary;
  onChanged: () => void;
  goto: (n: number) => void;
  onAutorun: () => void;
}) {
  const meta = STAGES[n - 1];
  const { data, error, status, loading, reload } = useApi<StageResult>(`/projects/${project.id}/stages/${n}`);
  const [override, setOverride] = useState<StageResult | null>(null);
  const [busy, setBusy] = useState<{ label: string; start: number } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const result = override ?? (status === 404 ? undefined : data);
  const notRun = !override && status === 404;

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
    act(`Running stage ${n} — ${meta.title}…`, async () => {
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
    act(`Running stage ${m} — ${STAGES[m - 1]?.title}…`, async () => {
      await api.post<StageResult>(`/projects/${project.id}/stages/${m}/run`, { inputs });
      onChanged();
      goto(m);
    });

  const View = VIEWS[n] as ComponentType<StageViewProps<StageArtifact>> | undefined;
  const artifact = result?.artifact;
  const st = result?.status ?? summary?.status ?? "not_started";

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start gap-x-6 gap-y-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="micro">Stage {String(n).padStart(2, "0")}</span>
            <LayerTag layer={meta.layer} />
            <StatusPill status={st} />
          </div>
          <h2 className="font-display mt-2.5 text-[34px] font-semibold uppercase leading-[36px]">{meta.title}</h2>
          <p className="mt-1 text-md text-ink-2">
            {meta.line.charAt(0).toUpperCase() + meta.line.slice(1)}
            {artifact && (
              <span className="ml-2 text-sm text-ink-3">
                {artifact.generated_by === "fixture" && project.id.startsWith("demo_")
                  ? "Pre-computed example"
                  : artifact.generated_by === "fixture"
                    ? `Cached example, ${fmtDate(artifact.generated_at)}`
                    : `Generated by ${artifact.generated_by}, ${fmtDate(artifact.generated_at)}`}
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          <Btn variant={notRun ? "primary" : "secondary"} disabled={!!busy} onClick={() => run({})}>
            {busy ? <Spinner /> : null} {notRun ? "Run stage" : "Re-run"}
          </Btn>
          <Btn
            variant={st === "draft" ? "ink" : "secondary"}
            disabled={!!busy || !artifact || st === "validated"}
            onClick={() => artifact && save(artifact, true)}
          >
            {st === "validated" ? "Validated" : "Validate"}
          </Btn>
        </div>
      </header>

      {busy && <RunningIndicator start={busy.start} label={busy.label} />}
      {actionError && <ErrorBox message={`Action failed: ${actionError}`} onRetry={() => setActionError(null)} />}

      {loading && !result && !notRun && <Loading text={`Loading stage ${n}…`} />}
      {error && status !== 404 && <ErrorBox message={`Could not load stage ${n}: ${error}`} onRetry={reload} />}

      {notRun && !busy && (
        <Empty
          title="This stage has not been run yet."
          body={`Run it to generate the ${meta.title.toLowerCase()} artifact${n > 1 ? " from the previous stages" : ""}.`}
          action={
            <>
              <Btn variant="primary" onClick={() => run({})}>
                Run stage {n}
              </Btn>
              {n >= 2 && n <= 7 && <Btn onClick={onAutorun}>Autorun stages 1–7</Btn>}
            </>
          }
        />
      )}

      {artifact && (
        <>
          {(artifact.fallback || result?.fallback) && <CachedBanner reason={artifact.fallback_reason} example={project.example} />}
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
              />
            ) : (
              <Card>
                <Generic value={artifact} />
              </Card>
            )}
          </Boundary>
          <div className="mt-2 flex flex-col gap-3">
            <Assumptions items={artifact.assumptions} />
            <details className="group text-sm text-ink-3">
              <summary className="inline-flex cursor-pointer items-center gap-1.5 transition-colors hover:text-ink">
                <Chevron className="-rotate-90 group-open:rotate-0" /> All fields (raw view)
              </summary>
              <div className="mt-3 rounded-md border border-line bg-surface p-5 text-ink">
                <Generic value={artifact} />
              </div>
            </details>
          </div>
        </>
      )}
    </div>
  );
}
