"use client";

import Link from "next/link";
import type { CostsArtifact, DesignArtifact, MatchingArtifact, SpecArtifact, StageResult } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { directionGlb, directionHero } from "@/lib/assets";
import { Still } from "./Still";
import { fmtValue } from "@/lib/meta";
import { ModelViewer } from "./ModelViewer";
import { DimsView } from "./blocks";
import { Arrow, LabelBadge, Skeleton } from "./ui";

const PID = "demo_desk_lamp";

/** The landing hero's object: the cached desk-lamp example, live from the API. */
export function HeroSpecimen() {
  const s2 = useApi<StageResult>(`/projects/${PID}/stages/2`);
  const s3 = useApi<StageResult>(`/projects/${PID}/stages/3`);
  const s5 = useApi<StageResult>(`/projects/${PID}/stages/5`);
  const s7 = useApi<StageResult>(`/projects/${PID}/stages/7`);
  const design = s2.data?.artifact as DesignArtifact | undefined;
  const spec = s3.data?.artifact as SpecArtifact | undefined;
  const costs = s5.data?.artifact as CostsArtifact | undefined;
  const match = s7.data?.artifact as MatchingArtifact | undefined;
  const failed = s3.error && s5.error;
  if (failed) return null;

  const dir = design?.directions.find((d) => d.id === design.chosen_direction_id) ?? design?.directions[0];
  const ref = costs?.tiers.find((t) => t.quantity === costs.reference_quantity) ?? costs?.tiers[1];

  return (
    <figure className="flex flex-col">
      <div className="relative">
        {design && dir ? (
          <Still
            url={directionHero(PID, dir.id)}
            alt="Magnetic desk lamp, rendered from the CAD"
            caption="Rendered from the CAD"
            height={420}
            className="flex h-[420px] justify-center bg-paper [&_img]:aspect-square [&_img]:!w-auto [&_img]:object-contain [&_img]:mix-blend-darken [&_img]:brightness-[1.03] [&_img]:[mask-image:linear-gradient(to_right,transparent,#000_10%,#000_90%,transparent)]"
            fallback={<ModelViewer url={directionGlb(PID, dir)} alt="Magnetic desk lamp, generated from the CAD" height={420} interactive={false} />}
          />
        ) : (
          <Skeleton className="h-[420px] w-full" />
        )}
        <span className="absolute left-0 top-0 inline-flex items-center gap-1.5 text-2xs font-medium text-ink-2">
          <span className="h-1.5 w-1.5 rounded-full bg-ink-4" aria-hidden />
          Example project
        </span>
      </div>
      <figcaption className="mt-2 border-t border-ink">
        <div className="flex items-baseline justify-between gap-4 py-3">
          <span className="text-base font-medium">“Magnetic rechargeable desk lamp, minimalist, sold €89”</span>
        </div>
        <dl className="grid grid-cols-3 border-t border-line text-sm">
          <div className="py-3 pr-3">
            <dt className="text-ink-2">Size</dt>
            <dd className="mt-1">{spec ? <DimsView d={spec.overall_dimensions} /> : <Skeleton className="h-4 w-24" />}</dd>
          </div>
          <div className="border-l border-line py-3 pl-3 pr-3">
            <dt className="text-ink-2">Unit cost{ref ? ` at ${ref.quantity.toLocaleString("en-US")}` : ""}</dt>
            <dd className="mt-1 flex flex-wrap items-center gap-2">
              {ref ? (
                <>
                  <span className="font-mono text-base" title={ref.unit_cost.source_or_assumption}>
                    {fmtValue(ref.unit_cost)}
                  </span>
                  <LabelBadge label={ref.unit_cost.label} tip={ref.unit_cost.source_or_assumption} small />
                </>
              ) : (
                <Skeleton className="h-4 w-16" />
              )}
            </dd>
          </div>
          <div className="border-l border-line py-3 pl-3">
            <dt className="text-ink-2">Factory shortlist</dt>
            <dd className="mt-1 flex flex-wrap items-center gap-2">
              {match ? (
                <>
                  <span className="font-mono text-base">{match.shortlist.length}</span>
                  <LabelBadge label="fictional" small />
                </>
              ) : (
                <Skeleton className="h-4 w-10" />
              )}
            </dd>
          </div>
        </dl>
        <Link
          href={`/projects/${PID}/wow`}
          className="group flex items-center justify-between border-t border-line py-3 text-base font-medium transition-colors hover:text-accent-ink"
        >
          Open this example
          <Arrow className="transition-transform duration-150 group-hover:translate-x-0.5" />
        </Link>
      </figcaption>
    </figure>
  );
}
