"use client";

import Link from "next/link";
import type { Project } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { Arrow, BtnLink, Empty, ErrorBox, Loading, Pill } from "@/components/ui";
import { ResetDemo } from "@/components/ResetDemo";
import { fmtDate } from "@/lib/meta";

function Progress({ validated, draft }: { validated: number; draft: number }) {
  return (
    <span className="flex items-center gap-3">
      <span className="flex gap-[2px]" aria-hidden>
        {Array.from({ length: 13 }).map((_, i) => (
          <span key={i} className={`h-2.5 w-[3px] rounded-[1px] ${i < validated ? "bg-ink" : i < validated + draft ? "bg-estimate" : "bg-line-2"}`} />
        ))}
      </span>
      <span className="w-[74px] font-mono text-sm text-ink-2">{validated}/13</span>
    </span>
  );
}

export default function ProjectsPage() {
  const { data, error, loading, reload } = useApi<Project[]>("/projects");
  return (
    <div className="mx-auto max-w-[1320px] px-6 pt-10 lg:px-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="title text-[28px] leading-[34px]">Projects</h1>
        <div className="flex items-center gap-2">
          <ResetDemo onDone={reload} />
          <BtnLink href="/new" variant="primary">
            New project
          </BtnLink>
        </div>
      </div>
      <div className="mt-8">
        {error && <ErrorBox message={error} onRetry={reload} />}
        {loading && !data && <Loading text="Loading projects…" rows={4} />}
        {data && data.length === 0 && (
          <Empty
            title="No projects yet."
            body="Reset the demo to load the two cached examples, or start a new project from a sentence."
            action={
              <>
                <BtnLink href="/new" variant="primary">
                  New project
                </BtnLink>
                <ResetDemo onDone={reload} />
              </>
            }
          />
        )}
        {data && data.length > 0 && (
          <ul className="overflow-hidden rounded-md bg-surface">
            <li className="hidden grid-cols-[minmax(0,1fr)_140px_160px_110px_20px] items-center gap-6 border-b border-line-2 px-6 py-2.5 md:grid">
              <span className="micro">Project</span>
              <span className="micro">Mode</span>
              <span className="micro">Stages validated</span>
              <span className="micro">Created</span>
              <span />
            </li>
            {data.map((p) => {
              const validated = Object.values(p.stage_status ?? {}).filter((s) => s === "validated").length;
              const drafted = Object.values(p.stage_status ?? {}).filter((s) => s === "draft").length;
              return (
                <li key={p.id} className="border-b border-line last:border-b-0">
                  <Link
                    href={`/projects/${p.id}`}
                    className="group grid items-center gap-x-6 gap-y-2 px-6 py-4 transition-colors duration-150 hover:bg-sunken md:grid-cols-[minmax(0,1fr)_140px_160px_110px_20px]"
                  >
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 text-md font-medium">
                        {p.name}
                        {p.id.startsWith("demo_") && (
                          <Pill dot>
                            Example project
                          </Pill>
                        )}
                      </p>
                      <p className="mt-0.5 truncate text-base text-ink-2">&ldquo;{p.prompt}&rdquo;</p>
                    </div>
                    <span className="text-base text-ink-2">{p.mode === "prototype" ? "Prototype" : "Idea"}</span>
                    <Progress validated={validated} draft={drafted} />
                    <span className="font-mono text-sm text-ink-3">{fmtDate(p.created_at)}</span>
                    <Arrow className="hidden text-ink-3 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-ink md:block" />
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
