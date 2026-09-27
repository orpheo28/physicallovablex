"use client";

import Link from "next/link";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { errorMessage } from "@/lib/api";
import { useNow } from "@/lib/useNow";
import { PHASES, railName, STAGES } from "@/lib/meta";
import { startAutorun, type Through } from "@/lib/autofill";
import { animeNow, loadAnime, reducedMotion } from "@/lib/motion";
import { useProject } from "./project/ProjectContext";
import { StatusIcon, stepState } from "./project/StatusIcon";
import { ScrollArea } from "./ScrollArea";
import { Arrow, Btn, BtnLink, ErrorBox, Pill, Spinner } from "./ui";

const ROW = 44; // px per step row: the progress line is measured in rows

/**
 * Autofill stepper (main panel): POST /projects/{id}/autorun?through=13 (or 7) returns 202 at once;
 * the project shell polls GET /projects/{id} every 2 s and the 13 steps, grouped in the 4 phases,
 * follow the server's real status. At the end: the overview, with the Launch Dossier ready to download.
 */
export function AutorunPanel({ through: requested }: { through: Through }) {
  const { id, detail, autorun, running, reload, summary } = useProject();
  const router = useRouter();
  const sp = useSearchParams();
  const [postError, setPostError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const through = (autorun?.through === 13 || autorun?.through === 7 ? autorun.through : requested) as Through;
  const state = autorun?.state ?? "idle";
  const failed = state === "failed";
  const finished = state === "done";

  const begin = useCallback(() => {
    setStarting(true);
    setPostError(null);
    startAutorun(id, requested)
      .then(() => {
        reload();
        router.replace(`/projects/${id}?autorun=${requested}`, { scroll: false });
      })
      .catch((e) => setPostError(errorMessage(e)))
      .finally(() => setStarting(false));
  }, [id, requested, reload, router]);

  // ?start=1 (from "Autofill the remaining steps"): start the run here, once.
  const startedHere = useRef(false);
  useEffect(() => {
    if (sp.get("start") !== "1" || startedHere.current || running) return;
    startedHere.current = true;
    begin();
  }, [sp, running, begin]);

  // Land on the overview once a run we watched finishes.
  const [sawRunning, setSawRunning] = useState(false);
  if (running && !sawRunning) setSawRunning(true);
  useEffect(() => {
    if (!finished || !sawRunning) return;
    const t = setTimeout(() => router.push(`/projects/${id}/wow${through === 13 ? "?dossier=1" : ""}`), 900);
    return () => clearTimeout(t);
  }, [finished, sawRunning, router, id, through]);

  const started = autorun?.started_at ? new Date(autorun.started_at).getTime() : null;
  const ended = autorun?.finished_at ? new Date(autorun.finished_at).getTime() : null;
  const now = useNow(running);
  const elapsed = started ? Math.max(0, ((running ? now : (ended ?? now)) - started) / 1000) : 0;

  const inRun = (n: number) => n <= through;
  const doneN = (n: number): boolean => {
    const s = summary(n);
    if (!autorun || state === "idle") return (s?.status ?? "not_started") !== "not_started";
    if (!inRun(n)) return (s?.status ?? "not_started") !== "not_started";
    if (finished) return true;
    if (autorun.completed_stages.includes(n)) return true;
    // Stage 1 is skipped when the brief already exists.
    return n === 1 && (s?.status ?? "not_started") !== "not_started" && autorun.current_stage !== 1;
  };
  const current = running ? autorun?.current_stage ?? null : null;
  const total = through;
  const completed = STAGES.filter((m) => inRun(m.n) && doneN(m.n)).length;
  const error = postError ?? (failed ? (autorun?.error ?? "The run failed on the server.") : null);

  // ---- Motion 1: the line draws between steps as real progress arrives; completed steps get a check stroke.
  const root = useRef<HTMLDivElement>(null);
  const prevDone = useRef<Set<number> | null>(null);
  const prevLines = useRef<Record<number, number>>({});
  useEffect(() => void loadAnime(), []);
  const doneSet = new Set(STAGES.filter((m) => doneN(m.n)).map((m) => m.n));
  const doneKey = [...doneSet].join(",");
  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    const before = prevDone.current;
    prevDone.current = new Set(doneKey ? doneKey.split(",").map(Number) : []);
    if (before === null) {
      // First render: no drawing, record where the lines are.
      el.querySelectorAll<HTMLElement>("[data-line]").forEach((l) => (prevLines.current[Number(l.dataset.line)] = l.offsetHeight));
      return;
    }
    // anime is loaded on mount; progress arrives seconds later (if not loaded: no animation, final state).
    const a = reducedMotion() ? null : animeNow();
    el.querySelectorAll<HTMLElement>("[data-line]").forEach((l) => {
      const ph = Number(l.dataset.line);
      const target = l.offsetHeight;
      const from = prevLines.current[ph] ?? target;
      prevLines.current[ph] = target;
      if (!a || from === target) return;
      l.style.height = `${from}px`;
      a.animate(l, { height: [`${from}px`, `${target}px`], duration: 600, ease: "outExpo" });
    });
    if (!a) return;
    for (const n of prevDone.current) {
      if (before.has(n)) continue;
      const path = el.querySelector<SVGPathElement>(`[data-step="${n}"] [data-check]`);
      if (path) a.animate(path, { strokeDashoffset: [1, 0], duration: 320, delay: 180, ease: "outExpo" });
    }
  }, [doneKey]);

  const hideHref = `/projects/${id}?stage=${current ?? Math.min(13, completed + 1)}`;

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto]">
      <header className="px-8 pb-3 pt-4">
        <p className="micro">Autofill · {through === 13 ? "all 13 steps" : "steps 1–7"}</p>
        <h1 className="title mt-1 text-[26px] leading-[32px]">
          {through === 13 ? "Autofill all 13 steps with AI" : "Autofill steps 1–7 with AI"}
        </h1>
        <dl className="mt-3 grid max-w-[1180px] grid-cols-2 gap-x-10">
          <div>
            <dt className="micro !text-ink-3">What this does</dt>
            <dd className="mt-0.5 text-base text-ink-2">
              Runs every step in order with sensible defaults: the first design direction and default volumes
              {through === 13 ? ", then quotes with the recommended one auto-approved, and the launch steps." : "."}
            </dd>
          </div>
          <div>
            <dt className="micro !text-ink-3">What you decide here</dt>
            <dd className="mt-0.5 text-base text-ink">Nothing while it runs. Afterwards, open any step to review or change it.</dd>
          </div>
        </dl>
      </header>

      <ScrollArea className="h-full px-8 pb-6 pt-6">
        <div className="flex max-w-[1180px] flex-col gap-6">
          <div className="flex items-center gap-4">
            <span className="font-mono text-xl font-medium tracking-[-0.02em]">
              {completed}
              <span className="text-ink-3">/{total}</span>
            </span>
            <div className="h-[3px] flex-1 overflow-hidden rounded-full bg-paper-2">
              <div className="h-full origin-left bg-accent transition-[width] duration-500 ease-out" style={{ width: `${(completed / total) * 100}%` }} />
            </div>
            <span className="flex w-[260px] items-center justify-end gap-2 text-sm text-ink-2" role="status">
              {starting ? (
                <>
                  <Spinner /> Starting…
                </>
              ) : running ? (
                <>
                  <Spinner className="text-accent" /> Running on the server <span className="font-mono">{elapsed.toFixed(0)} s</span>
                </>
              ) : finished ? (
                <span className="font-medium text-measured-ink">
                  Done in <span className="font-mono">{elapsed.toFixed(0)} s</span>
                </span>
              ) : failed ? (
                <span className="text-danger">Stopped</span>
              ) : (
                "Not started"
              )}
            </span>
          </div>

          <div ref={root} className="grid grid-cols-4 gap-6">
            {PHASES.map((ph) => {
              const steps = ph.stages;
              const lastDone = steps.reduce((k, n, i) => (doneN(n) ? i : k), -1);
              return (
                <section key={ph.n} aria-label={`Phase ${ph.n}: ${ph.title}`} className="min-w-0">
                  <p className="flex items-center gap-2 pb-1">
                    <span className="micro !text-ink-3">{ph.n}</span>
                    <span className="micro">{ph.title}</span>
                  </p>
                  <ol className="relative mt-1">
                    {/* track + drawn line, centred on the 16 px status icons */}
                    <span className="absolute left-[7.5px] top-[22px] w-px bg-line-2" style={{ height: (steps.length - 1) * ROW }} aria-hidden />
                    <span data-line={ph.n} className="absolute left-[7.5px] top-[22px] w-px bg-ink" style={{ height: Math.max(0, lastDone) * ROW }} aria-hidden />
                    {steps.map((n) => {
                      const s = summary(n);
                      const d = doneN(n);
                      const active = current === n;
                      const out = !inRun(n) && state !== "idle";
                      const st = active ? stepState(undefined, { running: true }) : d ? stepState(s?.status === "validated" ? "validated" : "draft") : stepState(undefined);
                      return (
                        <li key={n} data-step={n} className="relative flex items-center gap-3" style={{ height: ROW }}>
                          <span className="relative z-10 rounded-full bg-paper">
                            <StatusIcon state={st} />
                          </span>
                          <span className={`min-w-0 flex-1 truncate text-base ${d || active ? "text-ink" : out ? "text-ink-4" : "text-ink-3"}`}>{railName(n)}</span>
                          {active && <span className="text-sm text-accent-ink">Running…</span>}
                          {d && s?.fallback && (
                            <span className="flex shrink-0">
                              <Pill tone="amber" dot>
                                Cached example
                              </Pill>
                            </span>
                          )}
                          {out && !d && <span className="text-sm text-ink-4">Not in this run</span>}
                        </li>
                      );
                    })}
                  </ol>
                </section>
              );
            })}
          </div>

          {running && elapsed > 120 && (
            <p className="text-sm text-estimate-ink">Live runs can take several minutes. You can leave this screen: the run continues on the server.</p>
          )}
          {error && <ErrorBox message={`Autofill failed: ${error}`} onRetry={begin} />}
          {finished && sawRunning && <p className="text-base font-medium text-measured-ink">Done. Opening the overview…</p>}
          {detail && !running && state === "idle" && !starting && !error && (
            <p className="text-base text-ink-2">Autofill has not started for this project.</p>
          )}
        </div>
      </ScrollArea>

      <footer data-noprint className="flex h-14 items-center gap-3 px-8">
        <Link href={hideHref} className="text-sm text-ink-2 transition-colors hover:text-ink">
          {running ? "Hide — it keeps running" : "Back to the steps"}
        </Link>
        <span className="ml-auto" />
        {!running && state === "idle" && !starting && (
          <Btn variant="primary" onClick={begin}>
            Start autofill
          </Btn>
        )}
        {(finished || failed) && (
          <BtnLink href={`/projects/${id}/wow${through === 13 && finished ? "?dossier=1" : ""}`} variant="primary">
            Open the overview <Arrow />
          </BtnLink>
        )}
      </footer>
    </div>
  );
}
