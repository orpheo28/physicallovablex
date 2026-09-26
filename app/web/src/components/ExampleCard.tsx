"use client";

import Link from "next/link";
import type { DesignArtifact, Project, StageResult } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { directionGlb, directionHero } from "@/lib/assets";
import { ModelViewer } from "./ModelViewer";
import { Still } from "./Still";
import { Arrow, Pill, Skeleton } from "./ui";

const STILL = "[&_img]:aspect-square [&_img]:!w-auto [&_img]:object-contain [&_img]:mix-blend-darken [&_img]:brightness-[1.03] [&_img]:[mask-image:linear-gradient(to_right,transparent,#000_10%,#000_90%,transparent)]";

/** A cached demo project, shown by its CAD still, opening on the overview. */
export function ExampleCard({ p }: { p: Project }) {
  const s2 = useApi<StageResult>(`/projects/${p.id}/stages/2`);
  const design = s2.data?.artifact as DesignArtifact | undefined;
  const dir = design?.directions.find((d) => d.id === design.chosen_direction_id) ?? design?.directions[0];
  const validated = Object.values(p.stage_status ?? {}).filter((s) => s === "validated").length;
  return (
    <Link
      href={`/projects/${p.id}/wow`}
      className="group flex flex-col overflow-hidden rounded-md border border-line bg-paper transition-colors duration-150 hover:border-line-2"
    >
      <div className="relative flex h-[260px] items-center justify-center">
        <span className="absolute left-3 top-3 z-10">
          <Pill dot>Example project</Pill>
        </span>
        {dir ? (
          <Still
            url={directionHero(p.id, dir.id)}
            alt={`${p.name}, rendered from the CAD`}
            height={260}
            className={`flex h-[260px] w-full justify-center bg-paper ${STILL}`}
            fallback={<ModelViewer url={directionGlb(p.id, dir)} alt={p.name} height={260} interactive={false} />}
          />
        ) : s2.error ? null : (
          <Skeleton className="h-[260px] w-full" />
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1.5 border-t border-line bg-surface px-5 py-4">
        <span className="text-md font-medium">{p.name}</span>
        <span className="truncate text-base text-ink-2">&ldquo;{p.prompt}&rdquo;</span>
        <span className="mt-2 flex items-center justify-between text-sm">
          <span className="text-ink-3">
            <span className="font-mono text-ink-2">{validated}</span>/13 stages validated
          </span>
          <span className="flex items-center gap-1.5 font-medium text-ink transition-colors group-hover:text-accent-ink">
            Open example <Arrow className="transition-transform duration-150 group-hover:translate-x-0.5" />
          </span>
        </span>
      </div>
    </Link>
  );
}
