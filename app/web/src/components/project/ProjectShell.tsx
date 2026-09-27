"use client";

import Link from "next/link";
import { Suspense, useLayoutEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { PHASES, railName, STAGES } from "@/lib/meta";
import { autofillLabel, startAutorun, useAutofillMax } from "@/lib/autofill";
import { isExampleProject, useStudioAvailable } from "@/lib/studio";
import { errorMessage } from "@/lib/api";
import { firstTimeThisVisit, loadAnime, reducedMotion } from "@/lib/motion";
import { ResetDemo } from "../ResetDemo";
import { ScrollArea } from "../ScrollArea";
import { Spinner } from "../ui";
import { ProjectProvider, useProject } from "./ProjectContext";
import { StatusIcon, stepState } from "./StatusIcon";

/** Where the user is inside a project: a stage (1-13), the overview, the Factory Pack, or the autofill stepper. */
function useLocation() {
  const path = usePathname() ?? "";
  const sp = useSearchParams();
  const view = path.endsWith("/wow")
    ? "overview"
    : path.endsWith("/factory-pack")
      ? "pack"
      : path.endsWith("/studio")
        ? "studio"
        : sp.get("autorun")
          ? "autorun"
          : "stage";
  const raw = parseInt(sp.get("stage") ?? "1", 10);
  const stage = view === "stage" ? (raw >= 1 && raw <= 13 ? raw : 1) : null;
  return { view, stage } as const;
}

// ------------------------------------------------------------------ top bar progress (portal)

const noop = () => () => {};

function TopProgress() {
  const { detail, autorun, running } = useProject();
  const { view, stage } = useLocation();
  const slot = useSyncExternalStore(noop, () => document.getElementById("topbar-slot"), () => null);
  // Client-only (a portal): safe to read storage and the motion preference in the initializer.
  const [draw] = useState(() => !reducedMotion() && (() => {
    try {
      return !window.sessionStorage.getItem("plx:progress-drawn");
    } catch {
      return true;
    }
  })());
  const [drawn, setDrawn] = useState(!draw);
  const bar = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  // Motion 3: segments draw on first load (~600 ms), then the current step settles in the accent.
  useLayoutEffect(() => {
    if (!draw || drawn || started.current || !detail || !bar.current) return;
    started.current = true;
    firstTimeThisVisit("plx:progress-drawn");
    const el = bar.current;
    const safety = setTimeout(() => setDrawn(true), 2000);
    loadAnime().then((a) => {
      if (!a) return setDrawn(true);
      const segs = el.querySelectorAll<HTMLElement>("[data-seg]");
      const cur = el.querySelectorAll<HTMLElement>("[data-seg-current]");
      a.animate(segs, { scaleX: [0, 1], duration: 420, delay: a.stagger(14), ease: "outExpo" });
      a.animate(cur, { opacity: [0, 1], duration: 260, delay: 420, ease: "inOutQuad", onComplete: () => setDrawn(true) });
    });
    return () => clearTimeout(safety);
  }, [draw, drawn, detail]);

  // W26: the Studio is about the product; the 13-step progress lives in its icon rail instead.
  if (!slot || !detail || view === "studio") return null;
  const done = detail.stages.filter((s) => s.status !== "not_started").length;
  const runStage = running ? autorun?.current_stage : null;
  const label =
    view === "overview"
      ? `Overview · ${done} of 13 steps done`
      : view === "pack"
        ? `Factory Pack · ${done} of 13 steps done`
        : view === "autorun" || running
          ? runStage
            ? `Autofill · step ${runStage} of 13 · ${STAGES[runStage - 1]?.title}`
            : `Autofill · ${done} of 13 steps done`
          : `Step ${stage} of 13 · ${STAGES[(stage ?? 1) - 1]?.title}`;
  const current = view === "stage" && !running ? stage : runStage;

  return createPortal(
    <div className="flex min-w-0 items-center gap-3" aria-label="Project progress">
      <div ref={bar} className="flex items-center gap-[2px]" aria-hidden>
        {STAGES.map((m) => {
          const s = detail.stages.find((x) => x.stage === m.n)?.status;
          const c = s === "validated" ? "bg-ink" : s === "draft" ? "bg-estimate" : "bg-line-2";
          const isCur = current === m.n;
          return (
            <span
              key={m.n}
              data-seg
              className={`relative h-[2px] w-3 origin-left rounded-full ${c}`}
              style={draw && !drawn ? { transform: "scaleX(0)" } : undefined}
            >
              {isCur && <span data-seg-current className="absolute inset-0 rounded-full bg-accent" style={draw && !drawn ? { opacity: 0 } : undefined} />}
            </span>
          );
        })}
      </div>
      <span className="truncate whitespace-nowrap text-sm text-ink-2">
        {label.split(" · ").map((part, i) => (
          <span key={i} className={i === 0 ? "font-medium text-ink" : ""}>
            {i > 0 && <span className="px-1.5 text-ink-4">·</span>}
            {part}
          </span>
        ))}
      </span>
    </div>,
    slot,
  );
}

// ------------------------------------------------------------------ left rail

function RailItem({ href, active, icon, children, sub, compact }: { href: string; active: boolean; icon: ReactNode; children: ReactNode; sub?: ReactNode; compact?: boolean }) {
  if (compact)
    return (
      <li>
        <Link
          href={href}
          aria-current={active ? "page" : undefined}
          aria-label={typeof children === "string" ? children : undefined}
          title={typeof children === "string" ? children : undefined}
          className={`flex h-8 w-9 items-center justify-center rounded-sm transition-colors duration-150 ${active ? "bg-surface text-ink" : "text-ink-2 hover:bg-paper-2 hover:text-ink"}`}
        >
          {icon}
        </Link>
      </li>
    );
  return (
    <li>
      <Link
        href={href}
        aria-current={active ? "page" : undefined}
        className={`relative flex h-[30px] items-center gap-2.5 rounded-sm pl-2.5 pr-1.5 text-[13px] transition-colors duration-150 min-[1440px]:h-8 min-[1440px]:pl-3 min-[1440px]:text-[13.5px] ${
          active ? "bg-surface font-medium text-ink" : "text-ink-2 hover:bg-paper-2 hover:text-ink"
        }`}
      >
        {icon}
        <span className="min-w-0 flex-1 truncate" title={typeof children === "string" ? children : undefined}>
          {children}
        </span>
        {sub}
      </Link>
    </li>
  );
}

const ICON_STUDIO = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden className="shrink-0">
    <path d="M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z" strokeLinejoin="round" />
    <path d="M5.5 6.5h5M5.5 8.5h3" strokeLinecap="round" />
  </svg>
);
const ICON_OVERVIEW = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden className="shrink-0">
    <rect x="1.75" y="1.75" width="5.5" height="5.5" rx="1" />
    <rect x="8.75" y="1.75" width="5.5" height="5.5" rx="1" />
    <rect x="1.75" y="8.75" width="12.5" height="5.5" rx="1" />
  </svg>
);
const ICON_PACK = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden className="shrink-0">
    <path d="M3.5 1.75h6l3 3v9.5h-9z" strokeLinejoin="round" />
    <path d="M9.5 1.75v3h3M5.5 8.5h5M5.5 11h5" strokeLinecap="round" />
  </svg>
);

/** A 28 px progress ring around a phase icon: the arc shows the share of steps done. */
function PhaseRing({ frac, tone, children }: { frac: number; tone: "ink" | "amber" | "accent"; children: ReactNode }) {
  const r = 12.5;
  const c = 2 * Math.PI * r;
  const col = tone === "accent" ? "#FF4F00" : tone === "amber" ? "#C98A0B" : "#5F5E5A";
  return (
    <span className="relative flex h-7 w-7 items-center justify-center">
      <svg width="28" height="28" viewBox="0 0 28 28" className="absolute inset-0 -rotate-90" aria-hidden>
        <circle cx="14" cy="14" r={r} fill="none" stroke="#E6E4DF" strokeWidth="1.5" />
        {frac > 0 && <circle cx="14" cy="14" r={r} fill="none" stroke={col} strokeWidth="1.5" strokeLinecap="round" strokeDasharray={`${c * frac} ${c}`} />}
      </svg>
      {children}
    </span>
  );
}

const PHASE_ICON: Record<number, ReactNode> = {
  // Design: a pencil
  1: (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M10.5 2.5 13.5 5.5 5.5 13.5H2.5v-3z" />
    </svg>
  ),
  // Make it manufacturable: a gear
  2: (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden>
      <circle cx="8" cy="8" r="2.5" />
      <path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" />
    </svg>
  ),
  // Source: a factory
  3: (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" aria-hidden>
      <path d="M1.5 14V7l4 2.5V7l4 2.5V3h5v11z" />
    </svg>
  ),
  // Launch: a box
  4: (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" aria-hidden>
      <path d="M8 1.75 14 4.75v6.5L8 14.25 2 11.25v-6.5z" />
      <path d="m2 4.75 6 3 6-3M8 7.75v6.5" />
    </svg>
  ),
};

/** Studio (W26b): the 13 steps collapse into the 4 phases — an icon with a progress ring each, names and counts on hover. — status icons, names on hover. */
function CompactRail() {
  const { id, summary, running, autorun } = useProject();
  return (
    <aside data-chrome aria-label="Project steps" className="flex h-full min-h-0 flex-col items-center bg-paper pb-3 pt-2">
      <Link href="/projects" title="All projects" aria-label="All projects" className="mb-2 flex h-8 w-9 items-center justify-center rounded-sm text-ink-3 transition-colors hover:bg-paper-2 hover:text-ink">
        <span aria-hidden>←</span>
      </Link>
      <nav aria-label="Steps" className="flex min-h-0 flex-col items-center">
        <ul className="flex flex-col items-center gap-0.5">
          <RailItem compact href={`/projects/${id}/studio`} active icon={ICON_STUDIO}>
            Studio
          </RailItem>
          <RailItem compact href={`/projects/${id}/wow`} active={false} icon={ICON_OVERVIEW}>
            Overview
          </RailItem>
          <RailItem compact href={`/projects/${id}/factory-pack`} active={false} icon={ICON_PACK}>
            Factory Pack
          </RailItem>
        </ul>
        <span className="my-2.5 h-px w-5 bg-line-2" aria-hidden />
        <ul className="flex flex-col items-center gap-1.5">
          {PHASES.map((ph) => {
            const sts = ph.stages.map((n) => summary(n)?.status ?? "not_started");
            const done = sts.filter((x) => x !== "not_started").length;
            const draft = sts.some((x) => x === "draft");
            const isRunning = running && !!autorun?.current_stage && ph.stages.includes(autorun.current_stage);
            const next = ph.stages.find((n) => (summary(n)?.status ?? "not_started") === "not_started") ?? ph.stages[0];
            const label = `${ph.title}: ${done} of ${ph.stages.length} steps done${draft ? " (some drafts)" : ""}`;
            return (
              <li key={ph.n}>
                <Link
                  href={`/projects/${id}?stage=${next}`}
                  title={label}
                  aria-label={label}
                  className="flex h-10 w-10 items-center justify-center rounded-sm text-ink-2 transition-colors hover:bg-paper-2 hover:text-ink"
                >
                  <PhaseRing frac={done / ph.stages.length} tone={isRunning ? "accent" : draft ? "amber" : "ink"}>
                    {PHASE_ICON[ph.n]}
                  </PhaseRing>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}

function Rail() {
  const { id, detail, running, autorun, summary, reload, title, fullTitle } = useProject();
  const { view, stage } = useLocation();
  const router = useRouter();
  const max = useAutofillMax();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const p = detail?.project;
  const done = detail?.stages.filter((s) => s.status !== "not_started").length ?? 0;
  // m1: an example built step by step has no Studio (hidden while an example's versions load).
  const hasStudio = useStudioAvailable(id, isExampleProject(id, p?.tags)) === true;
  // N3: never offer "Autofill all 13 steps" once a step is done, nor on a recorded showcase.
  const showcaseProject = !!p && (p.tags?.includes("Example") || p.id.startsWith("demo_"));

  async function autofill() {
    setBusy(true);
    setErr(null);
    try {
      await startAutorun(id, max);
      reload();
      router.push(`/projects/${id}?autorun=${max}`);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside data-chrome aria-label="Project steps" className="flex h-full min-h-0 flex-col bg-paper">
      <div className="px-4 pb-2 pt-3">
        <p className="flex min-w-0 items-start gap-2">
          <Link href="/projects" title="All projects" aria-label="All projects" className="shrink-0 text-ink-3 transition-colors hover:text-ink">
            ←
          </Link>
          <span className="text-base font-semibold leading-5 tracking-[-0.01em]" title={fullTitle}>
            {p ? title : "Loading…"}
          </span>
        </p>
        {p && (
          <p className="mt-0.5 pl-[18px] text-2xs text-ink-3">
            {p.mode === "prototype" ? "Prototype mode" : "Idea mode"}
            {p.id.startsWith("demo_") ? " · Example project" : p.example ? ` · Fallback set: ${p.example.replace(/_/g, " ")}` : ""}
          </p>
        )}
      </div>

      <ScrollArea className="flex-1 px-2 pb-2 pt-2">
        <nav aria-label="Steps">
          <ul>
            {hasStudio && (
              <RailItem
                href={`/projects/${id}/studio`}
                active={view === "studio"}
                icon={ICON_STUDIO}
              >
                Studio
              </RailItem>
            )}
            <RailItem
              href={`/projects/${id}/wow`}
              active={view === "overview"}
              icon={ICON_OVERVIEW}
              sub={<span className="font-mono text-[11px] text-ink-3">{done}/13</span>}
            >
              Overview
            </RailItem>
            {/* Top group (QA F25: always visible at 1280×800, not below the 13 steps). */}
            <RailItem
              href={`/projects/${id}/factory-pack`}
              active={view === "pack"}
              icon={ICON_PACK}
            >
              Factory Pack
            </RailItem>
          </ul>
          {PHASES.map((ph) => (
            <div key={ph.n} className="mt-2.5 min-[1440px]:mt-3.5">
              <p className="px-3 pb-1 text-2xs font-medium text-ink-3">{ph.title}</p>
              <ol>
                {ph.stages.map((n) => {
                  const s = summary(n);
                  const active = view === "stage" && stage === n;
                  const isRunning = running && autorun?.current_stage === n;
                  return (
                    <RailItem
                      key={n}
                      href={`/projects/${id}?stage=${n}`}
                      active={active}
                      icon={<StatusIcon state={stepState(s?.status, { active, running: isRunning })} />}
                      sub={
                        s?.fallback ? (
                          <span className="text-[10px] font-medium text-estimate-ink" title="Cached example">
                            cached
                          </span>
                        ) : isRunning ? (
                          <Spinner className="text-accent" />
                        ) : null
                      }
                    >
                      {railName(n)}
                    </RailItem>
                  );
                })}
              </ol>
            </div>
          ))}
        </nav>
      </ScrollArea>

      <div className="flex flex-col items-start gap-1 px-3 py-2">
        {running ? (
          <Link href={`/projects/${id}?autorun=${autorun?.through ?? max}`} className="flex items-center gap-2 px-1 text-sm font-medium text-ink hover:text-accent-ink">
            <Spinner className="text-accent" /> Autofill running — view progress
          </Link>
        ) : done === 0 && !showcaseProject ? (
          <button onClick={autofill} disabled={busy} className="flex items-center gap-2 px-1 text-sm font-medium text-ink transition-colors hover:text-accent-ink disabled:opacity-45">
            {busy ? <Spinner /> : <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />}
            {autofillLabel(max)}
          </button>
        ) : null}
        {err && <span className="px-1 text-sm text-danger">{err}</span>}
        <ResetDemo onDone={() => router.push("/")} />
      </div>
    </aside>
  );
}

/** Project shell: left rail (13 steps in 4 phases) + main panel; fills the app shell, never scrolls as a page. */
function Rails() {
  const { view } = useLocation();
  return view === "studio" ? <CompactRail /> : <Rail />;
}

function ShellGrid({ children }: { children: ReactNode }) {
  const path = usePathname() ?? "";
  const studio = path.endsWith("/studio");
  return (
    <div
      data-shell
      className={`grid h-full min-h-0 ${studio ? "grid-cols-[56px_minmax(0,1fr)]" : "grid-cols-[248px_minmax(0,1fr)] min-[1440px]:grid-cols-[256px_minmax(0,1fr)]"}`}
    >
      {children}
    </div>
  );
}

export function ProjectShell({ id, children }: { id: string; children: ReactNode }) {
  return (
    <ProjectProvider id={id}>
      <ShellGrid>
        <Suspense fallback={<aside />}>
          <Rails />
          <TopProgress />
        </Suspense>
        <div className="flex min-h-0 min-w-0 flex-col">{children}</div>
      </ShellGrid>
    </ProjectProvider>
  );
}
