"use client";

import type { ReactNode } from "react";
import { useParams } from "next/navigation";
import type { FactoryPack } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { fmtDate } from "@/lib/meta";
import { BOMTable, CertificationsByMarket, DimsView, FileLink, IssuesTable, PartsTable, TiersTable } from "@/components/blocks";
import { Generic } from "@/components/Generic";
import { Lockup } from "@/components/Lockup";
import { ScrollArea } from "@/components/ScrollArea";
import { Boundary, Btn, CachedBanner, ErrorBox, LabelBadge, Loading, LV } from "@/components/ui";
import { ExportButton } from "@/components/ExportButton";

const SECTIONS = [
  "Product summary and target markets",
  "Structured spec",
  "CAD (STEP) and drawings",
  "BOM with component risk and alternatives",
  "DFM alerts and resolutions",
  "Certification checklist by market",
  "Target quantities and cost estimate",
  "Questions for the factory (EN + CN)",
  "Assumption register",
];

function Sec({ n, children, aside }: { n: number; children: ReactNode; aside?: ReactNode }) {
  return (
    <section id={`s${n}`} className="scroll-mt-4 border-t border-line-2 pt-5 [break-inside:avoid-page]">
      <h2 className="flex items-baseline gap-4">
        <span className="w-8 shrink-0 font-mono text-sm text-ink-3">§{n}</span>
        <span className="flex-1 text-lg font-semibold tracking-[-0.015em]">{SECTIONS[n - 1]}</span>
        {aside && <span className="text-sm text-ink-3">{aside}</span>}
      </h2>
      <div className="mt-5 pl-12 max-md:pl-0">
        <Boundary fallback={<p className="text-sm text-ink-3">This section could not be displayed.</p>}>{children}</Boundary>
      </div>
    </section>
  );
}

function TitleBlock({ fp }: { fp: FactoryPack }) {
  const cells: [string, ReactNode][] = [
    ["Document", <span key="d" className="font-mono">{fp.id}</span>],
    ["Revision", <span key="r" className="font-mono">v{fp.version}</span>],
    ["Issued", <span key="i" className="font-mono">{fmtDate(fp.created_at)}</span>],
    ["Project", <span key="p" className="font-mono">{fp.project_id}</span>],
    ["Markets", fp.target_markets.join(", ") || "—"],
    ["Quantities", <span key="q" className="font-mono">{fp.target_quantities.map((q) => q.toLocaleString("en-US")).join(" / ")}</span>],
  ];
  return (
    <div className="grid grid-cols-2 gap-y-1 rounded-md bg-paper py-1 sm:grid-cols-3">
      {cells.map(([k, v]) => (
        <div key={k} className="px-4 py-3">
          <div className="text-2xs text-ink-3">{k}</div>
          <div className="mt-0.5 break-words text-sm">{v}</div>
        </div>
      ))}
    </div>
  );
}

export default function FactoryPackPage() {
  const { id } = useParams<{ id: string }>();
  const { data: fp, error, loading, reload } = useApi<FactoryPack>(`/projects/${id}/factory-pack`);

  return (
    <div data-shell className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)]">
      <div data-noprint className="flex min-h-[52px] items-center gap-3 px-8">
        <p className="micro">Factory Pack</p>
        <span className="min-w-0 flex-1 truncate text-sm text-ink-3">The spec a factory can quote and build without back-and-forth{fp ? ` · ${fp.id} · v${fp.version}` : ""}</span>
        <Btn variant="ghost" onClick={() => window.print()}>
          Print
        </Btn>
        <ExportButton projectId={id} />
      </div>

      {error && !fp && (
        <div className="px-8 pt-6">
          <ErrorBox message={`Could not load the Factory Pack: ${error}`} onRetry={reload} />
        </div>
      )}
      {loading && !fp && (
        <div className="px-8">
          <Loading text="Assembling the Factory Pack…" rows={6} />
        </div>
      )}
      {fp && (
        <Boundary fallback={<Generic value={fp} />}>
          <div data-shell className="grid min-h-0 grid-cols-[200px_minmax(0,1fr)] gap-8 pl-8">
            <nav data-noprint aria-label="Sections" className="pt-6">
              <p className="micro">Contents</p>
              <ol className="mt-3 flex flex-col">
                {SECTIONS.map((s, i) => (
                  <li key={s}>
                    <a href={`#s${i + 1}`} className="grid grid-cols-[28px_1fr] py-1.5 text-sm text-ink-2 transition-colors hover:text-ink">
                      <span className="font-mono text-ink-3">§{i + 1}</span>
                      {s}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>

            <ScrollArea className="h-full pb-10 pr-8 pt-6" label="Factory Pack document">
            <article className="mx-auto max-w-[1080px] rounded-md bg-surface px-12 py-10 print:border-0 print:p-0">
              <header>
                <div className="flex items-start justify-between gap-6">
                  <div>
                    <p className="flex items-center gap-3 text-sm font-medium">
                      <Lockup tag={false} />
                      <span className="micro">Factory Pack</span>
                    </p>
                    <h1 className="title mt-6 text-[40px] leading-[1.08]">{fp.product_name}</h1>
                    <p className="mt-2 text-md text-ink-2">The spec a factory can quote and build without back-and-forth.</p>
                  </div>
                </div>
                <div className="mt-8">
                  <TitleBlock fp={fp} />
                </div>
                {fp.fallback && (
                  <div className="mt-4">
                    <CachedBanner scope="project" />
                  </div>
                )}
              </header>

              <div className="mt-12 flex flex-col gap-12">
                <Sec n={1}>
                  <p className="max-w-[72ch] text-md">{fp.product_summary}</p>
                  {fp.product_summary_cn && (
                    <p className="mt-3 max-w-[72ch] text-base text-ink-2">
                      {fp.product_summary_cn}{" "}
                      <span className="text-sm text-estimate-ink">(machine-translated — to be reviewed by a native speaker)</span>
                    </p>
                  )}
                  <p className="mt-4 text-base">
                    <span className="text-ink-2">Markets:</span> {fp.target_markets.join(", ")}
                  </p>
                </Sec>
                <Sec n={2} aside={`${fp.spec.parts.length} parts`}>
                  <dl className="mb-6 grid max-w-[560px] grid-cols-2 gap-x-8">
                    <div className="py-3 pr-4">
                      <dt className="micro">Overall (L × W × H)</dt>
                      <dd className="mt-1">
                        <DimsView d={fp.spec.overall_dimensions} />
                      </dd>
                    </div>
                    <div className="py-3">
                      <dt className="micro">Weight</dt>
                      <dd className="mt-1">
                        <LV v={fp.spec.weight} />
                      </dd>
                    </div>
                  </dl>
                  <PartsTable parts={fp.spec.parts} />
                  {fp.spec.tolerances.length > 0 && (
                    <div className="mt-6">
                      <p className="micro">General tolerances</p>
                      <ul className="mt-2 flex flex-col gap-1">
                        {fp.spec.tolerances.map((t) => (
                          <li key={t} className="font-mono text-sm">
                            {t}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </Sec>
                <Sec n={3} aside={`${fp.cad_files.length} files`}>
                  <div className="flex flex-col">
                    {fp.cad_files.map((f) => (
                      <FileLink key={f.url} file={f} />
                    ))}
                    {fp.cad_files.length === 0 && <p className="text-base text-ink-3">No CAD files yet.</p>}
                  </div>
                </Sec>
                <Sec n={4} aside={`${fp.bom.length} lines`}>
                  <BOMTable items={fp.bom} />
                </Sec>
                <Sec n={5} aside={`${fp.dfm_alerts.length} alerts`}>
                  <IssuesTable issues={fp.dfm_alerts} />
                </Sec>
                <Sec n={6}>
                  <CertificationsByMarket certs={fp.certifications} />
                </Sec>
                <Sec n={7}>
                  <p className="mb-4 text-base">
                    <span className="text-ink-2">Target quantities:</span>{" "}
                    <span className="font-mono">{fp.target_quantities.map((q) => q.toLocaleString("en-US")).join(" / ")}</span>
                  </p>
                  <TiersTable tiers={fp.cost_estimate} />
                </Sec>
                <Sec n={8} aside={`${fp.questions.length} questions`}>
                  <ol className="border-t border-line">
                    {fp.questions.map((q, i) => (
                      <li key={q.id} className="grid gap-2 border-b border-line py-3 md:grid-cols-[32px_1fr_1fr] md:gap-6">
                        <span className="font-mono text-sm text-ink-3">{i + 1}</span>
                        <p className="text-base">{q.en}</p>
                        <p className="text-base">
                          {q.cn ?? <span className="text-ink-4">—</span>}
                          <span className="mt-1 block text-sm text-estimate-ink">{q.cn_review_note}</span>
                        </p>
                      </li>
                    ))}
                  </ol>
                </Sec>
                <Sec n={9} aside={`${fp.assumption_register.length} entries`}>
                  <ul className="border-t border-line">
                    {fp.assumption_register.map((a) => (
                      <li key={a.id} className="grid grid-cols-[150px_1fr] items-start gap-3 border-b border-line py-2.5 text-base sm:grid-cols-[150px_1fr_auto]">
                        <span>
                          <LabelBadge label={a.label} tip={a.source ?? undefined} small />
                        </span>
                        <span>
                          {a.text}
                          {a.source && <span className="block text-sm text-ink-3">{a.source}</span>}
                        </span>
                        {a.stage && <span className="font-mono text-2xs text-ink-3">Stage {a.stage}</span>}
                      </li>
                    ))}
                  </ul>
                </Sec>
              </div>
              <footer className="mt-16 flex flex-wrap items-center justify-between gap-2 border-t border-ink pt-3 text-sm text-ink-3">
                <span>
                  {fp.id} · v{fp.version}
                </span>
                <span>Every figure carries its trust label: Measured, Sourced, Estimate or Fictional.</span>
              </footer>
            </article>
            </ScrollArea>
          </div>
        </Boundary>
      )}
    </div>
  );
}
