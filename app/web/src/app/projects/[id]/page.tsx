"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useProject } from "@/components/project/ProjectContext";
import { AutorunNote, StagePanel } from "@/components/StagePanel";
import { AutorunPanel } from "@/components/Autorun";
import { useAutofillMax } from "@/lib/autofill";
import { CachedBanner, ErrorBox, Skeleton, CouldntLoad } from "@/components/ui";

function PanelSkeleton() {
  return (
    <div className="flex h-full flex-col" role="status" aria-label="Loading project">
      <div className="border-b border-line px-8 pb-4 pt-4">
        <Skeleton className="h-3 w-64" />
        <Skeleton className="mt-3 h-7 w-80" />
        <Skeleton className="mt-4 h-4 w-full max-w-[900px]" />
      </div>
      <div className="flex-1 px-8 pt-6">
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

function Dashboard() {
  const { id, detail, error, status, reload, running, autorun, summary } = useProject();
  const sp = useSearchParams();
  const router = useRouter();
  const max = useAutofillMax();
  const raw = parseInt(sp.get("stage") ?? "1", 10);
  const stage = raw >= 1 && raw <= 13 ? raw : 1;
  const goto = (n: number, opts?: { run?: boolean }) => router.push(`/projects/${id}?stage=${n}${opts?.run ? "&run=1" : ""}`, { scroll: false });
  const autorunParam = sp.get("autorun");

  if (error && !detail)
    return (
      <div className="max-w-3xl px-8 py-16">
        {status === 404 ? (
          <ErrorBox message={`Project “${id}” not found. Reset the demo or pick a project.`} onRetry={reload} />
        ) : (
          <CouldntLoad what="this project" onRetry={reload} />
        )}
        <p className="mt-4 text-base">
          <Link href="/projects" className="underline decoration-line-2 underline-offset-4 hover:decoration-ink">
            Back to projects
          </Link>
        </p>
      </div>
    );
  if (!detail) return <PanelSkeleton />;
  if (autorunParam) return <AutorunPanel through={autorunParam === "13" ? 13 : 7} />;

  const through = autorun?.through ?? max;
  return (
    <StagePanel
      key={`${id}-${stage}`}
      project={detail.project}
      n={stage}
      summary={summary(stage)}
      nextSummary={summary(stage + 1)}
      onChanged={reload}
      goto={goto}
      onAutorun={() => router.push(`/projects/${id}?autorun=${max}&start=1`)}
      autoRun={sp.get("run") === "1"}
      autorunNote={
        running ? <AutorunNote step={autorun?.current_stage ?? null} through={through} projectId={id} /> : detail.has_fallback && !detail.fallback_stages?.includes(stage) ? (
          <CachedBanner scope="project" />
        ) : null
      }
    />
  );
}

export default function ProjectPage() {
  return (
    <Suspense fallback={<PanelSkeleton />}>
      <Dashboard />
    </Suspense>
  );
}
