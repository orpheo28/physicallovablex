"use client";

import Link from "next/link";
import { Suspense } from "react";
import type { Project } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { StartProject } from "@/components/StartProject";
import { ExampleCard } from "@/components/ExampleCard";
import { ErrorBox, Skeleton } from "@/components/ui";

function Examples() {
  const { data, error, reload } = useApi<Project[]>("/projects");
  const demos = data?.filter((p) => p.id.startsWith("demo_")) ?? [];
  const recent = data?.filter((p) => !p.id.startsWith("demo_")).slice(-3).reverse() ?? [];
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between border-b border-line-2 pb-2">
        <h2 className="micro">Open an example</h2>
        <span className="text-sm text-ink-3">Pre-computed, all 13 stages</span>
      </div>
      {error && <ErrorBox message={`Could not load the examples: ${error}`} onRetry={reload} />}
      {!data && !error && (
        <div className="grid gap-5 sm:grid-cols-2">
          <Skeleton className="h-[360px] w-full" />
          <Skeleton className="h-[360px] w-full" />
        </div>
      )}
      {data && demos.length === 0 && (
        <p className="text-base text-ink-3">No examples loaded. Use Reset demo on the Projects page to restore them.</p>
      )}
      {demos.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2">
          {demos.map((p) => (
            <ExampleCard key={p.id} p={p} />
          ))}
        </div>
      )}
      {recent.length > 0 && (
        <div className="mt-4">
          <p className="micro border-b border-line-2 pb-2">Your recent projects</p>
          <ul>
            {recent.map((p) => (
              <li key={p.id}>
                <Link href={`/projects/${p.id}`} className="flex items-baseline justify-between gap-4 border-b border-line py-2.5 text-base transition-colors hover:text-accent-ink">
                  <span className="truncate font-medium">{p.name}</span>
                  <span className="shrink-0 font-mono text-sm text-ink-3">{p.id}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  return (
    <div className="mx-auto grid max-w-[1320px] gap-x-16 gap-y-14 px-6 pt-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:px-10">
      <Suspense fallback={<Skeleton className="h-80 w-full" />}>
        <StartProject />
      </Suspense>
      <Examples />
    </div>
  );
}
