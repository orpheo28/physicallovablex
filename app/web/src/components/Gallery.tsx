"use client";

import Link from "next/link";
import type { DesignArtifact, StageResult } from "@/types/contracts";
import { fileUrl } from "@/lib/api";
import { directionHero } from "@/lib/assets";
import { useApi } from "@/lib/useApi";
import { BUILD_TEXT, useShowcase, type ShowcaseCard } from "@/lib/showcase";
import { RetryImg } from "./RetryImg";
import { Still } from "./Still";
import { Arrow, ErrorBox, LabelBadge, Pill, Skeleton } from "./ui";

const STILL = "[&_img]:!w-auto [&_img]:max-w-full [&_img]:object-contain [&_img]:mix-blend-darken [&_img]:brightness-[1.03]";

function Placeholder() {
  return (
    <div className="flex h-full items-center justify-center text-ink-4" aria-hidden>
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
        <path d="M12 2.5 3.5 7.2v9.6L12 21.5l8.5-4.7V7.2L12 2.5Z" />
        <path d="m3.5 7.2 8.5 4.7 8.5-4.7M12 11.9v9.6" />
      </svg>
    </div>
  );
}

/** A card without a hero image: the studio still of its chosen design direction, if the project has one. */
function DirectionStill({ projectId, alt }: { projectId: string; alt: string }) {
  const s2 = useApi<StageResult>(`/projects/${projectId}/stages/2`);
  const design = s2.data?.artifact as DesignArtifact | undefined;
  const dir = design?.directions.find((d) => d.id === design.chosen_direction_id) ?? design?.directions[0];
  if (!dir) return s2.loading ? <Skeleton className="h-full w-full" /> : <Placeholder />;
  return <Still url={directionHero(projectId, dir.id)} alt={alt} className={`flex h-full w-full justify-center ${STILL}`} fallback={<Placeholder />} />;
}

const SYM: Record<string, string> = { USD: "$", EUR: "€", GBP: "£" };

/** The key figure: unit cost at the first order ("$27.64") or one installation ("$17,344"), with its trust dot. */
function KeyFigure({ c }: { c: ShowcaseCard }) {
  const u = c.unitCost;
  if (!u) return null;
  const sym = SYM[u.unit] ?? `${u.unit} `;
  const n = c.perInstallation || u.value >= 1000 ? Math.round(u.value).toLocaleString("en-US") : u.value.toFixed(2);
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap font-normal" data-tip={u.source_or_assumption} data-tip-label={u.label}>
      <span className="font-mono text-sm text-ink">
        {sym}
        {n}
        {!c.perInstallation && <span className="font-sans text-2xs text-ink-3">/unit</span>}
      </span>
      <LabelBadge label={u.label} tip={u.source_or_assumption} />
    </span>
  );
}

/** One showcase: a large image, the name, one clean line (category · build path · key figure). No border; the image lifts on hover. */
export function GalleryCard({ c, tall }: { c: ShowcaseCard; tall?: boolean }) {
  const href = c.studio ? `/projects/${c.projectId}/studio` : `/projects/${c.projectId}/wow`;
  const hero = fileUrl(c.hero);
  const life = fileUrl(c.lifestyle?.url);
  const meta = [c.category, c.strategy ? BUILD_TEXT[c.strategy] : null].filter(Boolean) as string[];
  return (
    <Link href={href} className="group flex min-w-0 flex-col gap-3 rounded-md outline-offset-4">
      <div className={`img-outline relative overflow-hidden rounded-md bg-paper-2 ${tall ? "h-[clamp(160px,24vh,240px)]" : "h-[clamp(128px,22vh,232px)]"}`}>
        <div className="h-full w-full transition-[scale] duration-500 ease-[cubic-bezier(0.2,0,0,1)] group-hover:scale-[1.03]">
          {hero ? (
            <RetryImg src={hero} alt={`${c.name}: ${c.heroLabel ?? "product render"}`} className="h-full w-full object-cover" fallback={<Placeholder />} />
          ) : (
            <DirectionStill projectId={c.projectId} alt={`${c.name}, rendered from the CAD`} />
          )}
        </div>
        {/* W27: the lifestyle photo fades in on hover (staged scene, labelled). */}
        {life && (
          <div className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-focus-visible:opacity-100">
            <RetryImg src={life} alt={`${c.name}: ${c.lifestyle?.label}`} className="h-full w-full object-cover" />
          </div>
        )}
        {c.heroLabel && (
          <span
            className="absolute bottom-2 left-2 flex items-center rounded-full bg-surface/90 px-2 py-0.5 text-2xs text-ink-2"
            data-tip={`${c.heroLabel}${c.lifestyle ? `. On hover: ${c.lifestyle.label}` : ""}`}
          >
            <span className="group-hover:hidden">AI photo · geometry from our CAD</span>
            <span className="hidden group-hover:inline">{life ? "AI photo · staged scene, illustrative" : "AI photo · geometry from our CAD"}</span>
          </span>
        )}
        {c.demo && (
          <span className="absolute left-2.5 top-2.5 flex">
            <Pill dot>Example project</Pill>
          </span>
        )}
      </div>
      <div className="flex min-w-0 flex-col gap-0.5 px-0.5">
        <p className="flex items-baseline justify-between gap-3 text-base font-medium text-ink">
          <span className="min-w-0">{c.name}</span>
          {c.unitCost && <KeyFigure c={c} />}
        </p>
        {meta.length > 0 ? (
          <p className="text-sm text-ink-3">
            {meta.join(" · ")}
            {c.unitCost && c.perInstallation ? " · per installation" : ""}
          </p>
        ) : c.line ? (
          <p className="line-clamp-2 text-sm text-ink-3" title={c.line}>
            {c.line}
          </p>
        ) : null}
      </div>
    </Link>
  );
}

/** "See what others made": the showcase under the prompt box. */
export function GalleryStrip({ limit = 4 }: { limit?: number }) {
  const { cards, error } = useShowcase(limit);
  return (
    <section aria-labelledby="gallery-h" data-gallery className="flex min-h-0 w-full flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <h2 id="gallery-h" className="text-md font-semibold tracking-[-0.01em] text-ink">
          See what others made
        </h2>
        <Link href="/examples" className="flex items-center gap-1.5 text-sm text-ink-2 transition-colors hover:text-ink">
          All examples <Arrow />
        </Link>
      </div>
      {error && <ErrorBox message={`Could not load the examples: ${error}`} />}
      <div className="grid grid-cols-4 gap-5">
        {!cards && !error && Array.from({ length: limit }).map((_, i) => <Skeleton key={i} className="h-[clamp(170px,28vh,280px)] w-full rounded-md" />)}
        {cards?.map((c) => (
          <GalleryCard key={c.projectId} c={c} />
        ))}
      </div>
    </section>
  );
}
