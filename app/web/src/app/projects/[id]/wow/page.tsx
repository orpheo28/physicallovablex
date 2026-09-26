"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import type { CostsArtifact, DesignArtifact, MatchingArtifact, ProjectDetail, SpecArtifact, StageResult } from "@/types/contracts";
import { useApi, useFileExists } from "@/lib/useApi";
import { fileUrl } from "@/lib/api";
import { directionGlb, directionHero, directionRender } from "@/lib/assets";
import { fmtValue } from "@/lib/meta";
import { ModelViewer } from "@/components/ModelViewer";
import { RetryImg } from "@/components/RetryImg";
import { AutorunDialog } from "@/components/Autorun";
import { ExportButton } from "@/components/ExportButton";
import { BreakEven, DimsView } from "@/components/blocks";
import { Arrow, Boundary, BtnLink, Btn, CachedBanner, ErrorBox, LabelBadge, LV, Segmented, Skeleton } from "@/components/ui";

function Missing({ n, what, onAutorun }: { n: number; what: string; onAutorun: () => void }) {
  return (
    <div className="flex flex-col items-start gap-3 border-t border-line py-6">
      <p className="text-base text-ink-2">
        {what} appears once stage {n} has run.
      </p>
      <Btn variant="primary" onClick={onAutorun}>
        Run stages 1–7
      </Btn>
    </div>
  );
}

function Oops() {
  return <p className="py-4 text-sm text-ink-3">This block could not be displayed.</p>;
}

/** Faint graph paper behind the product, fading out toward the edges. */
function GraphPaper() {
  return <div aria-hidden className="graph-paper absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,#000_35%,transparent_72%)]" />;
}

type View = "auto" | "3d" | "cad" | "concept";

function Stage({ projectId, design, spec }: { projectId: string; design?: DesignArtifact; spec?: SpecArtifact }) {
  const dirId = design?.chosen_direction_id ?? spec?.direction_id ?? design?.directions[0]?.id;
  const dir = design?.directions.find((d) => d.id === dirId);
  const glb = directionGlb(projectId, dir, dirId) ?? spec?.cad_files.find((f) => f.format === "glb")?.url;
  // Only the demo projects ship a studio render (hero_dN.png); generated projects skip the request.
  const hero = dirId && projectId.startsWith("demo_") ? fileUrl(directionHero(projectId, dirId)) : null;
  const concept = dir ? fileUrl(directionRender(dir)) : null;
  const heroOk = useFileExists(hero).ok;
  const conceptOk = useFileExists(concept).ok;
  const [view, setView] = useState<View>("auto");

  // A still rendered from the CAD reads better than a live viewer when it exists; 3D stays one click away.
  const options: { value: View; label: string }[] = [];
  if (heroOk) options.push({ value: "cad", label: "Studio render" });
  options.push({ value: "3d", label: "3D model" });
  if (conceptOk) options.push({ value: "concept", label: "Concept" });
  const v: View = view === "auto" ? (heroOk ? "cad" : "3d") : options.some((o) => o.value === view) ? view : "3d";

  return (
    <div className="flex flex-col">
      <div className="relative">
        {v === "3d" ? (
          <div className="relative">
            <GraphPaper />
            <div className="relative">
              <ModelViewer url={glb} alt={spec?.product_name ?? dir?.name ?? "Product"} height={560} />
            </div>
          </div>
        ) : (
          <div className={`relative flex h-[560px] items-center justify-center overflow-hidden rounded-md ${v === "concept" ? "bg-surface" : "bg-paper"}`}>
            {v === "cad" && <GraphPaper />}
            <RetryImg
              src={(v === "cad" ? hero : concept) ?? ""}
              fallback={<ModelViewer url={glb} alt={spec?.product_name ?? dir?.name ?? "Product"} height={560} />}
              alt={dir?.name ?? "Product render"}
              className={`${v === "cad" ? "relative aspect-square h-full max-w-full object-contain mix-blend-darken brightness-[1.03] [mask-image:linear-gradient(to_right,transparent,#000_10%,#000_90%,transparent)]" : "h-full w-full object-cover"}`}
            />
          </div>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-2">
          {v === "3d" && (
            <>
              Full product, generated from the CAD{dir ? <> — direction <span className="text-ink">{dir.name}</span></> : null}. Drag to rotate.
            </>
          )}
          {v === "cad" && <>Rendered from the CAD{dir ? <> — direction <span className="text-ink">{dir.name}</span></> : null}.</>}
          {v === "concept" && "AI concept render — illustrative, not the CAD."}
        </p>
        {options.length > 1 && <Segmented label="Product view" value={v} options={options} onChange={setView} />}
      </div>
      {spec && (
        <dl className="mt-8 grid grid-cols-2 border-t border-line sm:grid-cols-4">
          <div className="border-b border-line py-4 pr-4 sm:border-b-0">
            <dt className="micro">Overall size</dt>
            <dd className="mt-1.5 text-base">
              <DimsView d={spec.overall_dimensions} />
            </dd>
          </div>
          <div className="border-b border-l border-line py-4 pl-4 sm:border-b-0 sm:pr-4">
            <dt className="micro">Weight</dt>
            <dd className="mt-1.5 text-base">
              <LV v={spec.weight} />
            </dd>
          </div>
          <div className="border-line py-4 pr-4 sm:border-l sm:pl-4">
            <dt className="micro">Material</dt>
            <dd className="mt-1.5 text-base">{dir?.material ?? spec.parts[0]?.material ?? "—"}</dd>
          </div>
          <div className="border-l border-line py-4 pl-4">
            <dt className="micro">Parts · BOM lines</dt>
            <dd className="mt-1.5 text-base">
              <span className="font-mono">{spec.parts.length}</span> {spec.parts.length === 1 ? "part" : "parts"} ·{" "}
              <span className="font-mono">{spec.bom.length}</span> {spec.bom.length === 1 ? "line" : "lines"}
            </dd>
          </div>
        </dl>
      )}
    </div>
  );
}

export default function WowPage() {
  const { id } = useParams<{ id: string }>();
  const [autorun, setAutorun] = useState(false);
  const project = useApi<ProjectDetail>(`/projects/${id}`);
  const s1 = useApi<StageResult>(`/projects/${id}/stages/1`);
  const s2 = useApi<StageResult>(`/projects/${id}/stages/2`);
  const s3 = useApi<StageResult>(`/projects/${id}/stages/3`);
  const s5 = useApi<StageResult>(`/projects/${id}/stages/5`);
  const s7 = useApi<StageResult>(`/projects/${id}/stages/7`);
  const reloadAll = () => {
    project.reload();
    s1.reload();
    s2.reload();
    s3.reload();
    s5.reload();
    s7.reload();
  };

  const design = s2.status === 404 ? undefined : (s2.data?.artifact as DesignArtifact | undefined);
  const spec = s3.status === 404 ? undefined : (s3.data?.artifact as SpecArtifact | undefined);
  const costs = s5.status === 404 ? undefined : (s5.data?.artifact as CostsArtifact | undefined);
  const match = s7.status === 404 ? undefined : (s7.data?.artifact as MatchingArtifact | undefined);
  const brief = s1.status === 404 ? undefined : s1.data?.artifact;
  // API field first (ProjectDetail.has_fallback); client computation only if an older API omits it
  const fbStage = project.data?.has_fallback ?? project.data?.stages.some((s) => s.stage <= 7 && s.fallback);
  const anyFallback = [brief, design, spec, costs, match].find((a) => a?.fallback);
  const showCached = !!(fbStage || anyFallback);
  const other = [s2, s3, s5, s7].find((s) => s.error && s.status !== 404);
  const p = project.data?.project;
  const name = p?.name ?? spec?.product_name;

  return (
    <div className="mx-auto max-w-[1320px] px-6 pb-8 pt-8 lg:px-10">
      <div className="flex flex-wrap items-center gap-3">
        <nav aria-label="Breadcrumb" className="flex min-w-0 flex-1 items-center gap-2 text-sm text-ink-3">
          <Link href="/projects" className="transition-colors hover:text-ink">
            Projects
          </Link>
          <span aria-hidden>/</span>
          <Link href={`/projects/${id}`} className="truncate transition-colors hover:text-ink">
            {name ?? id}
          </Link>
          <span aria-hidden>/</span>
          <span className="text-ink-2">Overview</span>
        </nav>
        <Btn variant="ghost" onClick={() => setAutorun(true)}>
          Re-run 1–7
        </Btn>
        <BtnLink href={`/projects/${id}?stage=1`}>Open all 13 stages</BtnLink>
        <ExportButton projectId={id} />
      </div>

      {(showCached || other) && (
        <div className="mt-5 flex flex-col gap-2">
          {showCached && <CachedBanner scope="project" reason={anyFallback?.fallback_reason} example={p?.example} />}
          {other && <ErrorBox message={`Could not load a stage: ${other.error}`} onRetry={reloadAll} />}
        </div>
      )}

      <div className="mt-6 grid gap-x-14 gap-y-10 lg:grid-cols-[minmax(0,1.12fr)_minmax(0,1fr)]">
        {/* The object */}
        <div className="lg:sticky lg:top-20 lg:self-start">
          {s3.loading && !s3.data ? (
            <Skeleton className="h-[560px] w-full rounded-md" />
          ) : spec || design ? (
            <Boundary fallback={<Oops />}>
              <Stage projectId={id} design={design} spec={spec} />
            </Boundary>
          ) : (
            <Missing n={3} what="The 3D product" onAutorun={() => setAutorun(true)} />
          )}
        </div>

        {/* The numbers */}
        <div className="flex min-w-0 flex-col">
          <p className="micro">From one sentence to a factory shortlist</p>
          {name ? (
            <h1 className="font-display mt-3 text-[60px] font-semibold uppercase leading-[0.95] text-balance">{name}</h1>
          ) : (
            <Skeleton className="mt-3 h-11 w-3/4" />
          )}
          {p?.prompt && <p className="mt-4 max-w-[52ch] text-md text-ink-2">&ldquo;{p.prompt}&rdquo;</p>}

          <section className="mt-10" aria-labelledby="cost-h">
            <div className="flex items-baseline justify-between border-b border-line-2 pb-2">
              <h2 id="cost-h" className="micro">
                Unit cost, ex-works
              </h2>
              <span className="text-sm text-ink-3">Stage 5 · Investment</span>
            </div>
            {s5.loading && !s5.data ? (
              <Skeleton className="mt-4 h-24 w-full" />
            ) : costs ? (
              <Boundary fallback={<Oops />}>
                <div className="grid grid-cols-3">
                  {costs.tiers.slice(0, 3).map((t, i) => {
                    const ref = t.quantity === costs.reference_quantity;
                    return (
                      <div key={t.quantity} className={`relative py-5 ${i > 0 ? "border-l border-line pl-5" : "pr-5"}`}>
                        {ref && <span className="absolute -top-px left-0 right-0 h-[2px] bg-accent" aria-hidden />}
                        <p className="flex items-center gap-2 text-sm text-ink-2">
                          <span className="font-mono">{t.quantity.toLocaleString("en-US")}</span> units
                          {ref && <span className="text-2xs font-medium text-accent-ink">first order</span>}
                        </p>
                        <p className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1">
                          <span className="font-mono text-xl font-medium tracking-[-0.02em]" title={t.unit_cost.source_or_assumption}>
                            {fmtValue(t.unit_cost)}
                          </span>
                          <LabelBadge label={t.unit_cost.label} tip={t.unit_cost.source_or_assumption} small />
                        </p>
                        <p className="mt-2 flex flex-wrap items-center gap-1.5 text-sm text-ink-2">
                          Margin <LV v={t.margin_pct} />
                        </p>
                      </div>
                    );
                  })}
                </div>
                <dl className="grid grid-cols-3 border-t border-line">
                  <div className="py-4 pr-5">
                    <dt className="text-sm text-ink-2">Cash for the first {costs.reference_quantity.toLocaleString("en-US")}</dt>
                    <dd className="mt-1">
                      <LV v={costs.total_cash_needed} />
                    </dd>
                  </div>
                  <div className="border-l border-line py-4 pl-5">
                    <dt className="text-sm text-ink-2">Break-even</dt>
                    <dd className="mt-1">
                      <BreakEven v={costs.breakeven_units} />
                    </dd>
                  </div>
                  <div className="border-l border-line py-4 pl-5">
                    <dt className="text-sm text-ink-2">Retail price</dt>
                    <dd className="mt-1">
                      <LV v={costs.target_retail_price} />
                    </dd>
                  </div>
                </dl>
              </Boundary>
            ) : (
              <Missing n={5} what="Unit cost" onAutorun={() => setAutorun(true)} />
            )}
          </section>

          <section className="mt-8" aria-labelledby="fac-h">
            <div className="flex items-center justify-between border-b border-line-2 pb-2">
              <h2 id="fac-h" className="micro">
                Factory shortlist
              </h2>
              <LabelBadge label="fictional" tip="Simulated network records — demo data" small />
            </div>
            {s7.loading && !s7.data ? (
              <Skeleton className="mt-4 h-40 w-full" />
            ) : match ? (
              <Boundary fallback={<Oops />}>
                <ol>
                  {[...match.shortlist]
                    .sort((a, b) => a.rank - b.rank)
                    .slice(0, 3)
                    .map((m) => (
                      <li key={m.factory_id} className="grid grid-cols-[28px_1fr_auto] items-start gap-x-3 border-b border-line py-4">
                        <span className="pt-0.5 font-mono text-sm text-ink-3">{String(m.rank).padStart(2, "0")}</span>
                        <div className="min-w-0">
                          <Link href={`/factories/${m.factory_id}`} className="text-base font-medium transition-colors hover:text-accent-ink">
                            {m.factory_name}
                          </Link>
                          <p className="mt-0.5 text-sm text-ink-2">{m.reasons.slice(0, 2).join(" · ")}</p>
                        </div>
                        <div className="flex w-[108px] flex-col items-end gap-1.5 pt-0.5" title={m.score.source_or_assumption}>
                          <span className="font-mono text-base">
                            {Math.round(m.score.value)}
                            <span className="text-ink-3">/100</span>
                          </span>
                          <span className="h-[3px] w-full overflow-hidden rounded-full bg-paper-2">
                            <span className="block h-full bg-ink" style={{ width: `${Math.min(100, Math.max(0, m.score.value))}%` }} />
                          </span>
                        </div>
                      </li>
                    ))}
                </ol>
                <div className="mt-6 flex flex-wrap items-center gap-2">
                  <BtnLink href={`/projects/${id}?stage=8`} variant="ink">
                    Request quotes <Arrow />
                  </BtnLink>
                  <BtnLink href={`/projects/${id}/factory-pack`} variant="ghost">
                    Read the Factory Pack
                  </BtnLink>
                </div>
              </Boundary>
            ) : (
              <Missing n={7} what="The factory shortlist" onAutorun={() => setAutorun(true)} />
            )}
          </section>
        </div>
      </div>
      {autorun && <AutorunDialog projectId={id} onClose={() => setAutorun(false)} onDone={reloadAll} />}
    </div>
  );
}
