"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import type { ProjectDetail, StageSummary } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { STAGES } from "@/lib/meta";
import { StagePanel, StatusDot } from "@/components/StagePanel";
import { AutorunDialog } from "@/components/Autorun";
import { ExportButton } from "@/components/ExportButton";
import { ResetDemo } from "@/components/ResetDemo";
import { Btn, BtnLink, CachedBanner, ErrorBox, Pill, Skeleton } from "@/components/ui";

function Stepper({ stages, current, onPick }: { stages: StageSummary[]; current: number; onPick: (n: number) => void }) {
  const validated = stages.filter((s) => s.status === "validated").length;
  const draft = stages.filter((s) => s.status === "draft").length;
  return (
    <div>
      <div className="flex gap-1" role="list" aria-label="Stage progress">
        {STAGES.map((m) => {
          const s = stages.find((x) => x.stage === m.n);
          const c = s?.status === "validated" ? "bg-ink" : s?.status === "draft" ? "bg-estimate" : "bg-line-2";
          const active = m.n === current;
          return (
            <button
              key={m.n}
              role="listitem"
              onClick={() => onPick(m.n)}
              title={`${m.n}. ${m.title} — ${(s?.status ?? "not_started").replace("_", " ")}`}
              aria-label={`Stage ${m.n}, ${m.title}`}
              aria-current={active ? "step" : undefined}
              className="group flex flex-1 flex-col gap-1.5 pt-1 text-left"
            >
              <span className={`h-[2px] w-full rounded-full transition-colors duration-150 ${active ? "bg-accent" : c} group-hover:opacity-80`} />
              <span className={`font-mono text-[10.5px] ${active ? "text-accent-ink" : "text-ink-3"}`}>{String(m.n).padStart(2, "0")}</span>
            </button>
          );
        })}
      </div>
      <p className="mt-1 text-sm text-ink-2">
        <span className="font-mono text-ink">{validated}</span>/13 validated
        {draft ? (
          <>
            {" "}
            · <span className="font-mono text-ink">{draft}</span> draft
          </>
        ) : null}
      </p>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="mx-auto max-w-[1320px] px-6 py-8 lg:px-10" role="status" aria-label="Loading project">
      <Skeleton className="h-4 w-48" />
      <Skeleton className="mt-5 h-8 w-96" />
      <Skeleton className="mt-3 h-4 w-72" />
      <Skeleton className="mt-8 h-2 w-full" />
      <div className="mt-10 grid gap-10 lg:grid-cols-[232px_1fr]">
        <div className="flex flex-col gap-3">
          {Array.from({ length: 13 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-40" />
          ))}
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    </div>
  );
}

function Dashboard() {
  const { id } = useParams<{ id: string }>();
  const sp = useSearchParams();
  const router = useRouter();
  const { data, error, status, loading, reload } = useApi<ProjectDetail>(`/projects/${id}`);
  const [autorun, setAutorun] = useState(false);
  const raw = parseInt(sp.get("stage") ?? "1", 10);
  const stage = raw >= 1 && raw <= 13 ? raw : 1;
  const goto = (n: number) => router.replace(`/projects/${id}?stage=${n}`, { scroll: false });

  if (error && !data)
    return (
      <div className="mx-auto max-w-3xl px-6 py-16">
        <ErrorBox message={status === 404 ? `Project “${id}” not found. Reset the demo or pick a project.` : `Could not load the project: ${error}`} onRetry={reload} />
        <p className="mt-4 text-base">
          <Link href="/projects" className="underline decoration-line-2 underline-offset-4 hover:decoration-ink">
            Back to projects
          </Link>
        </p>
      </div>
    );
  if (!data) return loading ? <DashboardSkeleton /> : null;

  const p = data.project;
  return (
    <div className="mx-auto max-w-[1320px] px-6 pt-8 lg:px-10">
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm text-ink-3">
        <Link href="/projects" className="transition-colors hover:text-ink">
          Projects
        </Link>
        <span aria-hidden>/</span>
        <span className="truncate text-ink-2">{p.name}</span>
      </nav>

      <div className="mt-4 flex flex-wrap items-end gap-x-8 gap-y-4">
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-[34px] font-semibold uppercase leading-[36px]">{p.name}</h1>
          <p className="mt-1.5 flex flex-wrap items-center gap-2 text-base text-ink-2">
            <span className="truncate">&ldquo;{p.prompt}&rdquo;</span>
            <Pill>{p.mode === "prototype" ? "Prototype mode" : "Idea mode"}</Pill>
            {p.id.startsWith("demo_") ? (
              <Pill dot>
                Example project
              </Pill>
            ) : p.example ? (
              <Pill dot>Fallback set: {p.example.replace(/_/g, " ")}</Pill>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Btn variant="ghost" onClick={() => setAutorun(true)}>
            Autorun 1–7
          </Btn>
          <BtnLink href={`/projects/${id}/wow`}>Overview</BtnLink>
          <BtnLink href={`/projects/${id}/factory-pack`}>Factory Pack</BtnLink>
          <ExportButton projectId={id} />
        </div>
      </div>

      {(data.has_fallback ?? data.stages.some((s) => s.stage <= 7 && s.fallback)) &&
        !(data.fallback_stages?.includes(stage) ?? data.stages.find((s) => s.stage === stage)?.fallback) && (
        <div className="mt-5">
          <CachedBanner scope="project" />
        </div>
      )}

      <div className="mt-7">
        <Stepper stages={data.stages} current={stage} onPick={goto} />
      </div>

      <div className="mt-8 grid gap-10 border-t border-line pt-8 lg:grid-cols-[232px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-6 lg:sticky lg:top-20 lg:self-start">
          <nav aria-label="Stages">
            <ol className="flex flex-col">
              {STAGES.map((m) => {
                const s = data.stages.find((x) => x.stage === m.n);
                const active = m.n === stage;
                return (
                  <li key={m.n}>
                    <button
                      onClick={() => goto(m.n)}
                      aria-current={active ? "page" : undefined}
                      className={`relative flex h-9 w-full items-center gap-3 rounded-sm pl-3 pr-2 text-left text-base transition-colors duration-150 ${
                        active ? "bg-surface font-medium text-ink" : "text-ink-2 hover:bg-paper-2 hover:text-ink"
                      }`}
                    >
                      {active && <span className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-accent" aria-hidden />}
                      <span className={`w-5 font-mono text-2xs ${active ? "text-accent-ink" : "text-ink-3"}`}>{String(m.n).padStart(2, "0")}</span>
                      <span className="flex-1 truncate">{m.title}</span>
                      {s?.fallback && (
                        <span className="text-[10px] font-medium text-estimate-ink" title="Cached example">
                          cached
                        </span>
                      )}
                      <StatusDot status={s?.status ?? "not_started"} />
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>
          <div className="flex flex-col items-start gap-1 border-t border-line pt-4 text-sm">
            <ResetDemo onDone={() => router.push("/projects")} />
          </div>
        </aside>
        <section className="min-w-0 pb-4">
          <StagePanel
            key={`${id}-${stage}`}
            project={p}
            n={stage}
            summary={data.stages.find((s) => s.stage === stage)}
            onChanged={reload}
            goto={goto}
            onAutorun={() => setAutorun(true)}
          />
        </section>
      </div>
      {autorun && <AutorunDialog projectId={id} onClose={() => setAutorun(false)} onDone={reload} />}
    </div>
  );
}

export default function ProjectPage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <Dashboard />
    </Suspense>
  );
}
