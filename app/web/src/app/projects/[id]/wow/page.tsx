"use client";

import Link from "next/link";
import { Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { CostsArtifact, DesignArtifact, EngineeringArtifact, LabeledValue, MatchingArtifact, ProductPhoto, SpecArtifact, StageResult, Version } from "@/types/contracts";
import { useApi, useFileExists } from "@/lib/useApi";
import { fileUrl } from "@/lib/api";
import { directionGlb, directionHero, directionRender } from "@/lib/assets";
import { fmtValue } from "@/lib/meta";
import { photoOf } from "@/lib/photos";
import { autofillLabel, useApiPaths, useAutofillMax } from "@/lib/autofill";
import { installFigures, partnerTitle, perInstallation, useEngineering } from "@/lib/studio";
import { animeNow, firstTimeThisVisit, loadAnime, reducedMotion } from "@/lib/motion";
import { useProject } from "@/components/project/ProjectContext";
import { ModelViewer } from "@/components/ModelViewer";
import { RetryImg } from "@/components/RetryImg";
import { ScrollArea } from "@/components/ScrollArea";
import { ExportButton } from "@/components/ExportButton";
import { MoreMenu } from "@/components/MoreMenu";
import { BreakEven, DimsView } from "@/components/blocks";
import { Arrow, Boundary, BtnLink, CachedBanner, CouldntLoad, LabelBadge, LV, Segmented, Skeleton } from "@/components/ui";

function Missing({ n, what, href, label, complete, onRetry }: { n: number; what: string; href: string; label: string; complete: boolean; onRetry: () => void }) {
  // A complete project (or a showcase) has every step: a missing block is a load failure, never "run autofill".
  if (complete) return <CouldntLoad what={what.charAt(0).toLowerCase() + what.slice(1)} onRetry={onRetry} className="my-3" />;
  return (
    <div className="flex flex-col items-start gap-3 py-5">
      <p className="text-base text-ink-2">
        {what} appears once step {n} has run.
      </p>
      <BtnLink variant="primary" href={href}>
        {label}
      </BtnLink>
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

type View = "auto" | "3d" | "cad" | "concept" | "lifestyle";

/** The product, filling its column: studio still on graph paper when one exists, else the live 3D model. */
function Product({
  projectId,
  design,
  spec,
  versionRender,
  photos,
}: {
  projectId: string;
  design?: DesignArtifact;
  spec?: SpecArtifact;
  versionRender?: string | null;
  photos?: ProductPhoto[] | null;
}) {
  const dirId = design?.chosen_direction_id ?? spec?.direction_id ?? design?.directions[0]?.id;
  const dir = design?.directions.find((d) => d.id === dirId);
  const glb = directionGlb(projectId, dir, dirId) ?? spec?.cad_files.find((f) => f.format === "glb")?.url;
  // Only the demo projects ship a studio render (hero_dN.png); generated projects skip the request.
  const hero = dirId && projectId.startsWith("demo_") ? fileUrl(directionHero(projectId, dirId)) : null;
  // Studio projects: the concept render of the CURRENT version (the direction's render shows the first look).
  // W27: the hero_studio photo of the current version (styled from our CAD) replaces the concept render when present.
  const heroPhoto = photoOf(photos, "hero_studio");
  const lifePhoto = photoOf(photos, "lifestyle");
  const concept = heroPhoto ? fileUrl(heroPhoto.url) : versionRender !== undefined ? fileUrl(versionRender) : dir ? fileUrl(directionRender(dir)) : null;
  const life = fileUrl(lifePhoto?.url);
  const heroOk = useFileExists(hero).ok;
  const conceptOk = useFileExists(concept).ok;
  const lifeOk = useFileExists(life).ok;
  const [view, setView] = useState<View>("auto");

  const options: { value: View; label: string }[] = [];
  if (heroOk) options.push({ value: "cad", label: "Studio render" });
  options.push({ value: "3d", label: "3D model" });
  if (conceptOk) options.push({ value: "concept", label: heroPhoto ? "Photo" : "Concept" });
  if (lifeOk) options.push({ value: "lifestyle", label: "Lifestyle" });
  const v: View = view === "auto" ? (heroOk ? "cad" : "3d") : options.some((o) => o.value === view) ? view : "3d";
  const alt = spec?.product_name ?? dir?.name ?? "Product";

  return (
    <div className="relative h-full min-h-0 overflow-hidden rounded-md">
      {v === "3d" ? (
        <>
          <GraphPaper />
          <div className="relative h-full">
            <ModelViewer url={glb} alt={alt} height="100%" />
          </div>
        </>
      ) : (
        <div className={`relative flex h-full justify-center bg-paper ${v === "cad" ? "items-center" : "items-start pt-10"}`}>
          {v === "cad" && <GraphPaper />}
          <RetryImg
            src={(v === "cad" ? hero : v === "lifestyle" ? life : concept) ?? ""}
            fallback={<ModelViewer url={glb} alt={alt} height="100%" />}
            alt={dir?.name ?? "Product render"}
            className={
              v === "cad"
                ? "relative aspect-square h-full max-w-full object-contain mix-blend-darken brightness-[1.03] [mask-image:linear-gradient(to_right,transparent,#000_10%,#000_90%,transparent)]"
                : "img-outline max-h-[calc(100%-28px)] max-w-full self-start rounded-md object-contain"
            }
          />
        </div>
      )}
      {options.length > 1 && (
        <div className="absolute right-0 top-0">
          <Segmented label="Product view" value={v} options={options} onChange={setView} />
        </div>
      )}
      <p className="absolute bottom-0 left-0 max-w-full text-2xs text-ink-3">
        {v === "3d" && (
          <>
            Full product, generated from the CAD{dir ? <> — direction <span className="text-ink">{dir.name}</span></> : null}. Drag to rotate.
          </>
        )}
        {v === "cad" && <>Rendered from the CAD{dir ? <> — direction <span className="text-ink">{dir.name}</span></> : null}.</>}
        {v === "concept" && (heroPhoto ? heroPhoto.label : "AI concept render — illustrative, not the CAD.")}
        {v === "lifestyle" && lifePhoto?.label}
      </p>
    </div>
  );
}

/**
 * Rooftop solar: one installation of the CURRENT version — installed price vs installer cost (N1), then what it
 * produces and saves (engineering, PVGIS Sourced).
 */
function InstallationBlock({ e, inst }: { e: EngineeringArtifact; inst: { installed: LabeledValue | null; installer: LabeledValue | null } }) {
  const sol = e.solar;
  const cells: [string, LabeledValue | null | undefined][] = [
    ["Energy per year", sol?.annual_energy],
    ["Savings per year", sol?.annual_savings],
    ["Payback", sol?.payback],
  ];
  return (
    <div>
      <div className="relative py-3">
        <p className="text-sm text-ink-2">One turnkey installation{sol ? ` · ${sol.module_count.value} modules, ${sol.peak_power.value} ${sol.peak_power.unit}` : ""}</p>
        <div className="mt-1.5 grid grid-cols-2 gap-x-8">
          {(
            [
              ["Installed price", inst.installed],
              ["Installer cost", inst.installer],
            ] as const
          ).map(([k, v]) => (
            <div key={k} className="min-w-0">
              <p className="text-sm text-ink-3">{k}</p>
              {v ? (
                <>
                  <p className="mt-0.5 flex items-center gap-2" data-tip={v.source_or_assumption} data-tip-label={v.label}>
                    <span className="font-mono text-[clamp(22px,3vh,28px)] font-medium tracking-[-0.02em]">{fmtValue(v)}</span>
                    <LabelBadge label={v.label} tip={v.source_or_assumption} small />
                  </p>
                  <p className="mt-0.5 text-2xs text-ink-3 text-pretty">{v.source_or_assumption}</p>
                </>
              ) : (
                <p className="mt-0.5 text-ink-4">—</p>
              )}
            </div>
          ))}
        </div>
      </div>
      {sol && (
        <dl className="grid grid-cols-3 gap-x-8">
          {cells.map(([k, v]) => (
            <div key={k} className="py-1.5">
              <dt className="text-sm text-ink-3">{k}</dt>
              <dd className="mt-1">
                <LV v={v} />
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

function SpecStrip({ spec, design }: { spec: SpecArtifact; design?: DesignArtifact }) {
  const dir = design?.directions.find((d) => d.id === (design?.chosen_direction_id ?? spec.direction_id));
  const cells: [string, React.ReactNode][] = [
    ["Overall size", <DimsView key="d" d={spec.overall_dimensions} />],
    ["Weight", <LV key="w" v={spec.weight} />],
    ["Material", dir?.material ?? spec.parts[0]?.material ?? "—"],
    [
      "Parts",
      <span key="p">
        <span className="font-mono">{spec.parts.length}</span> {spec.parts.length === 1 ? "part" : "parts"} · <span className="font-mono">{spec.bom.length}</span>{" "}
        {spec.bom.length === 1 ? "line" : "lines"}
      </span>,
    ],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-8 gap-y-2 min-[1700px]:grid-cols-4">
      {cells.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="text-sm text-ink-3">{k}</dt>
          <dd className="mt-0.5 text-sm text-ink">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Launch Dossier ready (after Make it): a quiet status line under the title; the download is the header's primary action. */
function DossierReady() {
  return (
    <p className="mt-3 flex items-start gap-2 text-sm text-ink-2" role="status">
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden className="mt-0.5 shrink-0">
        <circle cx="8" cy="8" r="7.25" fill="#111111" />
        <path d="m4.8 8.3 2.2 2.1 4.3-4.6" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>
        <span className="font-medium text-ink">Launch Dossier ready.</span> All 13 steps are filled in; the PDF bundles the Factory Pack (EN + 中文), every step and the
        assumption register.
      </span>
    </p>
  );
}

function Overview() {
  const { id, detail, title, fullTitle } = useProject();
  const sp = useSearchParams();
  const max = useAutofillMax();
  const dossier = sp.get("dossier") === "1";
  // N3: a complete project (13/13) or a recorded showcase never offers autofill; a failed load is retried, then calm.
  const doneCount = detail?.stages.filter((x) => x.status !== "not_started").length ?? 0;
  const showcaseProject = !!detail && (detail.project.tags?.includes("Example") || id.startsWith("demo_"));
  const complete = doneCount >= 13 || showcaseProject;
  const s1 = useApi<StageResult>(`/projects/${id}/stages/1`, { retryNotFound: complete });
  const s2 = useApi<StageResult>(`/projects/${id}/stages/2`, { retryNotFound: complete });
  const s3 = useApi<StageResult>(`/projects/${id}/stages/3`, { retryNotFound: complete });
  const s5 = useApi<StageResult>(`/projects/${id}/stages/5`, { retryNotFound: complete });
  const s7 = useApi<StageResult>(`/projects/${id}/stages/7`, { retryNotFound: complete });
  const reloadAll = () => [s1, s2, s3, s5, s7].forEach((s) => s.reload());

  const design = s2.status === 404 ? undefined : (s2.data?.artifact as DesignArtifact | undefined);
  const spec = s3.status === 404 ? undefined : (s3.data?.artifact as SpecArtifact | undefined);
  const costs = s5.status === 404 ? undefined : (s5.data?.artifact as CostsArtifact | undefined);
  const match = s7.status === 404 ? undefined : (s7.data?.artifact as MatchingArtifact | undefined);
  const brief = s1.status === 404 ? undefined : s1.data?.artifact;
  // API field first (ProjectDetail.has_fallback); client computation only if an older API omits it
  const fbStage = detail?.has_fallback ?? detail?.stages.some((s) => s.stage <= 7 && s.fallback);
  const anyFallback = [brief, design, spec, costs, match].find((a) => a?.fallback);
  const showCached = !!(fbStage || anyFallback);
  const other = [s2, s3, s5, s7].find((s) => s.error && s.status !== 404);
  const p = detail?.project;
  const name = p ? title : spec?.product_name;
  const autofillHref = `/projects/${id}?autorun=${max}&start=1`;
  // "Autofill all 13 steps" only on a project with nothing done yet; otherwise it fills the remaining steps.
  const autofillCta = doneCount > 0 ? "Autofill the remaining steps" : autofillLabel(max);
  const paths = useApiPaths();
  const vs = useApi<Version[]>(paths?.has("/projects/{project_id}/versions") ? `/projects/${id}/versions` : null);
  const currentVersion = vs.data?.find((v) => v.is_current);
  const eng = useEngineering(id, s7.data?.artifact.generated_at ?? null);
  const partner = partnerTitle(eng.data, false);
  const perInst = perInstallation(eng.data, costs);
  const inst = installFigures(currentVersion?.preview, costs, eng.data);

  // ---- Motion 2: entrance, once per visit (~1.2 s). Final state first for reduced motion or a repeat visit.
  const root = useRef<HTMLDivElement>(null);
  const key = `plx:wow:${id}`;
  const [pending, setPending] = useState(() => {
    if (typeof window === "undefined" || reducedMotion()) return false;
    try {
      return !window.sessionStorage.getItem(key);
    } catch {
      return true;
    }
  });
  const started = useRef(false);
  const settled = !s2.loading && !s3.loading && !s5.loading && !s7.loading;
  useEffect(() => void loadAnime(), []);
  useLayoutEffect(() => {
    if (!pending || !settled || started.current || !root.current) return;
    started.current = true;
    firstTimeThisVisit(key);
    const el = root.current;
    const go = (a: NonNullable<ReturnType<typeof animeNow>>) => {
      const product = el.querySelector<HTMLElement>("[data-anim='product']");
      if (product) a.animate(product, { opacity: [0, 1], translateY: [8, 0], duration: 600, ease: "outExpo" });
      el.querySelectorAll<HTMLElement>("[data-ticker]").forEach((t, i) => {
        const value = Number(t.dataset.value);
        const unit = t.dataset.unit ?? "";
        const final = t.dataset.final ?? "";
        // From 70 % of the value, not 0: a "$0.00" first frame reads as missing data (QA F18).
        const o = { v: value * 0.7 };
        t.textContent = fmtValue({ value: o.v, unit });
        a.animate(o, {
          v: value,
          duration: 700,
          delay: 150 + i * 80,
          ease: "outExpo",
          onUpdate: () => (t.textContent = fmtValue({ value: o.v, unit })),
          onComplete: () => (t.textContent = final),
        });
      });
      const rows = el.querySelectorAll<HTMLElement>("[data-row]");
      if (rows.length) a.animate(rows, { opacity: [0, 1], translateY: [4, 0], duration: 400, delay: a.stagger(80, { start: 350 }), ease: "outExpo" });
      const bars = el.querySelectorAll<HTMLElement>("[data-bar]");
      if (bars.length) a.animate(bars, { scaleX: [0, 1], duration: 600, delay: a.stagger(90, { start: 450 }), ease: "inOutQuad" });
    };
    const a = animeNow();
    if (a) go(a);
    else loadAnime().then((m) => (m ? go(m) : setPending(false)));
    const t = setTimeout(() => setPending(false), 1400);
    return () => clearTimeout(t);
  }, [pending, settled, key]);

  const hide = pending ? { opacity: 0 } : undefined;

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)]">
      <header className="flex min-h-[52px] items-center gap-2 px-8">
        <p className="text-sm font-medium text-ink">Overview</p>
        <span className="text-sm text-ink-3">From one sentence to a factory shortlist</span>
        <span className="ml-auto" />
        <BtnLink href={`/projects/${id}/factory-pack`} variant="ghost">
          Factory Pack
        </BtnLink>
        <MoreMenu
          items={[
            { label: "Open step by step", href: `/projects/${id}?stage=1` },
            { label: "Back to the Studio", href: `/projects/${id}/studio` },
          ]}
        />
        <ExportButton projectId={id} label={dossier ? "Download Launch Dossier" : "Export Launch Dossier"} />
      </header>

      <div ref={root} className="flex min-h-0 flex-col gap-4 px-8 pb-4 pt-2">
        {(showCached || (other && !complete)) && (
          <div className="flex flex-col gap-2">
            {showCached && <CachedBanner scope="project" reason={anyFallback?.fallback_reason} example={p?.example} />}
            {other && !complete && <CouldntLoad what="part of this overview" onRetry={reloadAll} />}
          </div>
        )}

        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,0.92fr)_minmax(0,1fr)] gap-x-10 min-[1440px]:gap-x-12">
          {/* The object */}
          <div data-anim="product" className="flex min-h-0 flex-col gap-4" style={pending ? { opacity: 0, transform: "translateY(8px)" } : undefined}>
            <div className="min-h-0 flex-1">
            {s3.loading && !s3.data ? (
              <Skeleton className="h-full w-full rounded-md" />
            ) : spec || design ? (
              <Boundary fallback={<Oops />}>
                <Product
                  projectId={id}
                  design={design}
                  spec={spec}
                  versionRender={currentVersion ? (currentVersion.preview?.render_url ?? null) : undefined}
                  photos={currentVersion?.preview?.photos}
                />
              </Boundary>
            ) : (
              <Missing n={3} what="The 3D product" href={autofillHref} label={autofillCta} complete={complete} onRetry={reloadAll} />
            )}
            </div>
            {spec && <SpecStrip spec={spec} design={design} />}
          </div>

          {/* The numbers */}
          <ScrollArea className="h-full" label="Costs and factory shortlist">
            <div className="flex min-w-0 flex-col pb-2">
              {name ? (
                <h1 className="title text-[clamp(28px,4.2vh,40px)] leading-[1.08]" title={fullTitle}>
                  {name}
                </h1>
              ) : (
                <Skeleton className="h-11 w-3/4" />
              )}
              {p?.prompt && <p className="mt-2 text-md text-ink-2 text-pretty">&ldquo;{p.prompt}&rdquo;</p>}
              {dossier && <DossierReady />}

              <section className="mt-[clamp(16px,3vh,32px)]" aria-labelledby="cost-h">
                <div className="flex items-baseline justify-between pb-1">
                  <h2 id="cost-h" className="text-base font-semibold tracking-[-0.01em] text-ink">
                    {perInst ? "Cost per installation" : "Unit cost, ex-works"}
                  </h2>
                  <Link href={`/projects/${id}?stage=5`} className="text-sm text-ink-3 transition-colors hover:text-ink">
                    Costs &amp; investment
                  </Link>
                </div>
                {s5.loading && !s5.data ? (
                  <Skeleton className="mt-4 h-24 w-full" />
                ) : perInst && eng.data && (inst.installed || inst.installer) ? (
                  // Per installation (rooftop solar): one site = one sale — no volume tiers, one currency (the engineering's).
                  <Boundary fallback={<Oops />}>
                    <InstallationBlock e={eng.data} inst={inst} />
                  </Boundary>
                ) : costs ? (
                  <Boundary fallback={<Oops />}>
                    <div className="grid gap-x-8" style={{ gridTemplateColumns: `repeat(${Math.min(3, costs.tiers.length)}, minmax(0, 1fr))` }}>
                      {costs.tiers.slice(0, 3).map((t) => {
                        const ref = t.quantity === costs.reference_quantity;
                        const text = fmtValue(t.unit_cost);
                        return (
                          <div key={t.quantity} className="relative py-[clamp(8px,1.4vh,14px)]">
                            <p className="flex items-center gap-2 whitespace-nowrap text-sm text-ink-3">
                              <span className="font-mono">{t.quantity.toLocaleString("en-US")}</span> {perInst || costs.unit_basis === "per_installation" ? (t.quantity === 1 ? "installation" : "installations") : "units"}
                              {ref && <span className="rounded-full bg-paper-2 px-2 text-2xs font-medium text-ink-2">first order</span>}
                            </p>
                            <p className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1">
                              <span className="relative inline-block font-mono text-[clamp(22px,3vh,28px)] font-medium leading-[1.2] tracking-[-0.02em]" title={t.unit_cost.source_or_assumption}>
                                <span style={pending ? { visibility: "hidden" } : undefined}>{text}</span>
                                {pending && (
                                  <span
                                    data-ticker
                                    data-value={t.unit_cost.value}
                                    data-unit={t.unit_cost.unit}
                                    data-final={text}
                                    aria-hidden
                                    className="absolute left-0 top-0 whitespace-nowrap"
                                  />
                                )}
                              </span>
                              <LabelBadge label={t.unit_cost.label} tip={t.unit_cost.source_or_assumption} small />
                            </p>
                            <p className="mt-1 flex flex-wrap items-center gap-1.5 text-sm text-ink-2">
                              Margin <LV v={t.margin_pct} />
                            </p>
                          </div>
                        );
                      })}
                    </div>
                    <dl className="mt-1 grid grid-cols-3 gap-x-8">
                      <div className="py-1.5">
                        <dt className="whitespace-nowrap text-sm text-ink-3">Cash, first {costs.reference_quantity.toLocaleString("en-US")}</dt>
                        <dd className="mt-1">
                          <LV v={costs.total_cash_needed} />
                        </dd>
                      </div>
                      <div className="py-1.5">
                        <dt className="text-sm text-ink-3">Break-even</dt>
                        <dd className="mt-1">
                          <BreakEven v={costs.breakeven_units} />
                        </dd>
                      </div>
                      <div className="py-1.5">
                        <dt className="text-sm text-ink-3">Retail price</dt>
                        <dd className="mt-1">
                          <LV v={costs.target_retail_price} />
                        </dd>
                      </div>
                    </dl>
                  </Boundary>
                ) : (
                  <Missing n={5} what="Unit cost" href={autofillHref} label={autofillCta} complete={complete} onRetry={reloadAll} />
                )}
              </section>

              <section className="mt-[clamp(16px,3vh,32px)]" aria-labelledby="fac-h">
                <div className="flex items-center gap-3 pb-1">
                  <h2 id="fac-h" className="text-base font-semibold tracking-[-0.01em] text-ink">
                    {partner} shortlist
                  </h2>
                  <LabelBadge label="fictional" tip="Simulated network records — demo data" small text />
                  <Link href={`/projects/${id}?stage=8`} className="ml-auto flex items-center gap-1.5 text-sm font-medium text-ink transition-colors hover:text-accent-ink">
                    Request quotes <Arrow />
                  </Link>
                </div>
                {s7.loading && !s7.data ? (
                  <Skeleton className="mt-4 h-40 w-full" />
                ) : match ? (
                  <Boundary fallback={<Oops />}>
                    <ol className="mt-1 flex flex-col gap-[clamp(8px,1.4vh,14px)]">
                      {[...match.shortlist]
                        .sort((a, b) => a.rank - b.rank)
                        .slice(0, 3)
                        .map((m) => (
                          <li key={m.factory_id} data-row style={hide} className="grid grid-cols-[16px_minmax(0,1fr)_88px] items-start gap-x-3">
                            <span className="pt-0.5 font-mono text-sm text-ink-4">{m.rank}</span>
                            <div className="min-w-0">
                              <Link href={`/factories/${m.factory_id}`} className="text-base font-medium transition-colors hover:text-accent-ink">
                                {m.factory_name}
                              </Link>
                              <p className="mt-0.5 text-sm text-ink-3 text-pretty">{m.reasons.slice(0, 2).join(" · ")}</p>
                            </div>
                            <div className="flex flex-col items-end gap-1.5 pt-1" data-tip={m.score.source_or_assumption} data-tip-label="fictional">
                              <span className="font-mono text-sm text-ink">
                                {Math.round(m.score.value)}
                                <span className="text-ink-4"> / 100</span>
                              </span>
                              <span className="h-[3px] w-full overflow-hidden rounded-full bg-paper-2">
                                <span
                                  data-bar
                                  className="block h-full origin-left rounded-full bg-ink-3"
                                  style={{ width: `${Math.min(100, Math.max(0, m.score.value))}%`, ...(pending ? { transform: "scaleX(0)" } : {}) }}
                                />
                              </span>
                            </div>
                          </li>
                        ))}
                    </ol>
</Boundary>
                ) : (
                  <Missing n={7} what={`The ${partner.toLowerCase()} shortlist`} href={autofillHref} label={autofillCta} complete={complete} onRetry={reloadAll} />
                )}
              </section>
            </div>
          </ScrollArea>
        </div>

      </div>
    </div>
  );
}

export default function WowPage() {
  return (
    <Suspense fallback={<Skeleton className="m-8 h-96" />}>
      <Overview />
    </Suspense>
  );
}
