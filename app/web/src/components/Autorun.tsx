"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { AutorunResult, AutorunStatus, ProjectDetail, StageSummary } from "@/types/contracts";
import { api, ApiError, errorMessage } from "@/lib/api";
import { useNow } from "@/lib/useNow";
import { STAGES } from "@/lib/meta";
import { Btn, ErrorBox, Pill, Spinner } from "./ui";

const STEPS = STAGES.slice(0, 7);

/** A stage counts as done in this run once the server stamped it after the run started. */
function doneSince(s: StageSummary | undefined, start: number) {
  if (!s || s.status === "not_started" || !s.updated_at) return false;
  const t = new Date(s.updated_at).getTime();
  return Number.isFinite(t) && t >= start - 1500;
}

/**
 * Modal: POST /projects/{id}/autorun. While it runs, GET /projects/{id} every 2 s drives
 * the stepper from the real stage statuses; then land on the overview (wow) screen.
 */
export function AutorunDialog({ projectId, onClose, onDone }: { projectId: string; onClose: () => void; onDone?: () => void }) {
  const router = useRouter();
  const [start, setStart] = useState<number | null>(null);
  const [postError, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [sync, setSync] = useState<AutorunResult | null>(null); // only if the API answered synchronously
  const [briefExisted, setBriefExisted] = useState(false);
  const status: AutorunStatus | null | undefined = detail?.autorun;
  const serverDone = status?.state === "done";
  const serverFailed = status?.state === "failed";
  const finished = !!sync || (start !== null && serverDone);
  const error = postError ?? (start !== null && serverFailed ? (status?.error ?? "The run failed on the server.") : null);
  const running = start !== null && !finished && !error;
  const now = useNow(running);
  const elapsed = start ? Math.max(0, ((now || start) - start) / 1000) : 0;
  const dialogRef = useRef<HTMLDivElement>(null);

  // POST returns 202 at once; GET /projects/{id} every 2 s is the source of truth for progress.
  useEffect(() => {
    if (!running) return;
    let cancelled = false;
    let inflight = false; // never stack polls: one request at a time, each capped at 5 s
    const tick = () => {
      if (inflight) return;
      inflight = true;
      api
        .poll<ProjectDetail>(`/projects/${projectId}`, 5000)
        .then((d) => !cancelled && setDetail(d))
        .catch(() => undefined)
        .finally(() => (inflight = false));
    };
    tick();
    const t = setInterval(tick, 2000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [running, projectId]);

  useEffect(() => {
    if (!finished) return;
    onDone?.();
    const t = setTimeout(() => router.push(`/projects/${projectId}/wow`), 900);
    return () => clearTimeout(t);
  }, [finished, onDone, router, projectId]);

  useEffect(() => {
    dialogRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function go() {
    setError(null);
    setSync(null);
    setDetail(null);
    try {
      const d = await api.get<ProjectDetail>(`/projects/${projectId}`);
      setBriefExisted(d.stages.some((s) => s.stage === 1 && s.status !== "not_started"));
    } catch {
      setBriefExisted(false);
    }
    setStart(Date.now());
    try {
      const r = await api.post<AutorunResult>(`/projects/${projectId}/autorun`);
      if (r.results.length > 0) setSync(r); // synchronous API (older build): all results at once
    } catch (e) {
      // A dropped connection does not stop the server-side run: keep following it by polling.
      if (!(e instanceof ApiError && (e.status === 0 || e.status >= 500))) setError(errorMessage(e));
    }
  }

  const byStage = new Map(sync?.results.map((r) => [r.stage, r]) ?? []);
  const summary = new Map((detail?.stages ?? []).map((s) => [s.stage, s]));
  const doneN = (n: number) => {
    if (start === null) return false;
    if (byStage.has(n) || serverDone) return true;
    // Prefer the server's autorun status; fall back to update times if the API has none.
    if (status) return status.completed_stages.includes(n) || (n === 1 && briefExisted && status.current_stage !== 1);
    return doneSince(summary.get(n), start) || (n === 1 && briefExisted);
  };
  const current = running ? (status?.current_stage ?? STEPS.find((s) => !doneN(s.n))?.n) : undefined;
  const completed = STEPS.filter((s) => doneN(s.n)).length;
  const allDone = completed === STEPS.length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="autorun-title"
        className="w-full max-w-[520px] rounded-md border border-line-2 bg-surface outline-none"
      >
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <h2 id="autorun-title" className="text-md font-semibold tracking-[-0.01em]">
            From brief to factory shortlist
          </h2>
          <button onClick={onClose} className="text-sm text-ink-2 transition-colors hover:text-ink">
            {running ? "Hide — keeps running" : "Close"}
          </button>
        </div>
        <div className="px-6 py-5">
          <p className="text-base text-ink-2">
            Runs stages 1 to 7 with sensible defaults: the chosen (or first) design direction and default volumes. You can edit any stage
            afterwards.
          </p>

          <div className="mt-5 flex items-center gap-3">
            <div className="h-[3px] flex-1 overflow-hidden rounded-full bg-paper-2">
              <div className="h-full bg-accent transition-[width] duration-500 ease-out" style={{ width: `${(completed / STEPS.length) * 100}%` }} />
            </div>
            <span className="font-mono text-sm text-ink-2">
              {completed}/{STEPS.length}
            </span>
          </div>

          <ol className="mt-4">
            {STEPS.map((s) => {
              const r = byStage.get(s.n);
              const done = doneN(s.n);
              const active = current === s.n;
              const cached = r?.fallback ?? (done && summary.get(s.n)?.fallback);
              return (
                <li key={s.n} className="flex h-10 items-center gap-3 border-b border-line text-base last:border-b-0">
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full text-2xs transition-colors duration-200 ${
                      done ? "bg-ink text-white" : active ? "border border-accent text-accent-ink" : "border border-line-2 text-ink-3"
                    }`}
                  >
                    {done ? (
                      <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden>
                        <path d="m3 8.5 3.2 3L13 4.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : active ? (
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                    ) : (
                      <span className="font-mono">{s.n}</span>
                    )}
                  </span>
                  <span className={`flex-1 ${done || active ? "text-ink" : "text-ink-3"}`}>{s.title}</span>
                  {active && <span className="text-sm text-ink-2">Running…</span>}
                  {cached && (
                    <Pill tone="amber" dot>
                      Cached example
                    </Pill>
                  )}
                </li>
              );
            })}
          </ol>

          {running && !allDone && (
            <p className="mt-4 flex items-center gap-2 text-sm text-ink-2">
              <Spinner /> Running on the server <span className="font-mono">{elapsed.toFixed(0)} s</span>
            </p>
          )}
          {running && elapsed > 120 && !allDone && (
            <p className="mt-2 text-sm text-estimate-ink">
              Live runs can take several minutes. You can hide this window: the run continues on the server.
            </p>
          )}
          {finished && <p className="mt-4 text-base font-medium text-measured-ink">Done. Opening the overview…</p>}
          {error && (
            <div className="mt-4">
              <ErrorBox message={`Autorun failed: ${error}`} onRetry={go} />
            </div>
          )}
          {start === null && (
            <div className="mt-6 flex justify-end gap-2">
              <Btn variant="ghost" onClick={onClose}>
                Cancel
              </Btn>
              <Btn variant="primary" onClick={go}>
                Start autorun
              </Btn>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
