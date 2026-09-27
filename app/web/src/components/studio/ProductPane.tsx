"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { CostsArtifact, ProductPhoto, Version, VersionPreview } from "@/types/contracts";
import { photoOf } from "@/lib/photos";
import { fileUrl } from "@/lib/api";
import { useFileExists } from "@/lib/useApi";
import { animeNow, reducedMotion } from "@/lib/motion";
import { ModelViewer } from "../ModelViewer";
import { RetryImg } from "../RetryImg";
import { Chevron, LabelBadge, Segmented, Spinner } from "../ui";
import { Tick, useFlash } from "./Tick";
import { BUILD_TEXT, buildKind } from "@/lib/showcase";
import { installFigures, partnerTitle, perInstallation, type Engineering } from "@/lib/studio";

const SYMBOL: Record<string, string> = { USD: "$", EUR: "€", GBP: "£", CNY: "¥" };
const money = (unit = "USD") => (n: number) => {
  const sym = SYMBOL[unit] ?? `${unit} `;
  return n >= 1000 ? `${sym}${Math.round(n).toLocaleString("en-US")}` : `${sym}${n.toFixed(2)}`;
};
const usd = money("USD");
const mm = (n: number) => (Math.abs(n - Math.round(n)) < 0.05 ? String(Math.round(n)) : n.toFixed(1));
const qty = (q: number) => (q >= 1000 ? `${q / 1000}k` : String(q));

/** Faint graph paper behind the product, fading out toward the edges. */
function GraphPaper() {
  return <div aria-hidden className="graph-paper absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,#000_35%,transparent_72%)]" />;
}

export type ViewMode = "3d" | "photo";

/**
 * Photo / 3D toggle state of a version (the toggle sits in the Studio header). The photo is the W27 hero_studio
 * photo of that version (styled from our CAD) when there is one, else the older AI concept render.
 */
export function useViewMode(v: Version | undefined, live?: ProductPhoto[] | null) {
  const photo = photoOf(v?.preview?.photos, "hero_studio") ?? (v?.is_current ? photoOf(live, "hero_studio") : null);
  const render = fileUrl(photo?.url ?? v?.preview?.render_url);
  const renderOk = useFileExists(render).ok;
  const [view, setView] = useState<ViewMode>("3d");
  const mode: ViewMode = view === "photo" && renderOk ? "photo" : "3d";
  const label = photo ? photo.label : "AI concept render, illustrative, not the CAD.";
  return { mode, setView, renderOk, render, label };
}

export function ViewToggle({ vm }: { vm: ReturnType<typeof useViewMode> }) {
  return (
    <Segmented
      label="Product view"
      value={vm.mode}
      onChange={vm.setView}
      options={[
        { value: "photo", label: "Photo", disabled: !vm.renderOk },
        { value: "3d", label: "3D" },
      ]}
    />
  );
}

/** The live product: the version's CAD (3D) or its AI concept render, cross-fading when the version changes. */
export function Viewer({ v, working, alt, vm, photoNote }: { v: Version | undefined; working: number | null; alt: string; vm: ReturnType<typeof useViewMode>; photoNote?: string | null }) {
  const p = v?.preview;
  const { mode, render } = vm;
  const stage = useRef<HTMLDivElement>(null);
  const key = `${v?.n}-${mode}-${mode === "photo" ? render : p?.glb_url}`;

  // Motion: cross-fade the product when the version (or its view) changes.
  const last = useRef(key);
  useLayoutEffect(() => {
    if (last.current === key) return;
    last.current = key;
    if (!stage.current || reducedMotion()) return;
    animeNow()?.animate(stage.current, { opacity: [0, 1], duration: 400, ease: "inOutQuad" });
  }, [key]);

  return (
    <div className="relative h-full min-h-0 overflow-hidden rounded-md" data-studio-viewer>
      <GraphPaper />
      <div ref={stage} className="relative h-full">
        {!p ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-ink-3">
            <Spinner /> Building the first version: CAD, BOM, costs, factories
          </div>
        ) : mode === "photo" && render ? (
          <div className="flex h-full items-center justify-center pb-6">
            <RetryImg key={render} src={render} alt={`${alt}: ${vm.label}`} className="img-outline h-full max-h-full w-auto max-w-full rounded-md object-contain" />
          </div>
        ) : (
          <ModelViewer key={p.glb_url ?? "none"} url={p.glb_url} alt={alt} height="100%" />
        )}
      </div>
      <div className="absolute left-0 top-0 flex items-center gap-2">
        {working !== null && (
          <span className="flex items-center gap-1.5 rounded-full bg-surface/90 px-2 py-0.5 text-2xs font-medium text-ink">
            <Spinner className="!h-2.5 !w-2.5 text-accent" /> Working on v{working}…
          </span>
        )}
        {v?.render_pending && (
          <span className="flex items-center gap-1.5 rounded-full bg-surface/90 px-2 py-0.5 text-2xs text-ink-3">
            <Spinner className="!h-2.5 !w-2.5" /> Rendering…
          </span>
        )}
        {photoNote && (
          <span className="flex max-w-[420px] items-center gap-1.5 rounded-full bg-surface/90 px-2.5 py-0.5 text-2xs text-ink-2" role="status">
            {photoNote}
          </span>
        )}
      </div>
      <p className="absolute bottom-0 left-0 max-w-full text-2xs text-ink-3">
        {mode === "photo" ? vm.label : p ? "Full product, generated from the CAD. Drag to rotate." : ""}
      </p>
    </div>
  );
}

function Row({ k, children, className = "" }: { k: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`grid grid-cols-[72px_minmax(0,1fr)] items-baseline gap-x-2 min-[1440px]:grid-cols-[80px_minmax(0,1fr)] min-[1440px]:gap-x-3 ${className}`}>
      <dt className="text-sm text-ink-3">{k}</dt>
      <dd className="min-w-0 text-sm text-ink">{children}</dd>
    </div>
  );
}

/** "4 certifications": the list opens on click (W26 — collapsed by default). */
function Certifications({ list }: { list: string[] }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);
  if (!list.length) return <span className="text-ink-3">None required</span>;
  return (
    <div ref={box} className="relative inline-block">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 rounded-sm text-ink underline decoration-line-2 underline-offset-4 transition-colors hover:decoration-ink"
      >
        <span className="font-mono">{list.length}</span> certification{list.length === 1 ? "" : "s"}
        <Chevron open={open} />
      </button>
      {open && (
        <ul className="absolute bottom-7 left-0 z-40 w-[300px] rounded-lg bg-surface p-3 text-sm shadow-float">
          {list.map((c) => (
            <li key={c} className="py-1 text-ink-2">
              {c}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The product facts under the viewer as a clean key-value grid (W26). Changed numbers tick from the old value and flash. */
export function Strip({ p, eng, costs }: { p: VersionPreview | null | undefined; eng?: Engineering; costs?: CostsArtifact }) {
  const kind = buildKind(eng?.build_strategy);
  const perInst = perInstallation(eng, p);
  const inst = installFigures(p, costs, eng);
  const look = useFlash<HTMLDivElement>(`${p?.color_hex}|${p?.material}|${p?.finish}`);
  const certs = useFlash<HTMLDivElement>((p?.certifications ?? []).join("|"));
  const bars = useRef<HTMLDivElement>(null);
  const scores = (p?.top_factories ?? []).map((f) => f.score).join(",");
  const firstScores = useRef(true);
  useEffect(() => {
    if (firstScores.current) {
      firstScores.current = false;
      return;
    }
    if (!bars.current || reducedMotion()) return;
    animeNow()?.animate(bars.current.querySelectorAll("[data-bar]"), { scaleX: [0, 1], duration: 600, delay: animeNow()!.stagger(60), ease: "outExpo" });
  }, [scores]);
  if (!p) return <div className="h-[132px]" />;
  const d = p.dimensions;
  // Site-scale products (a roof array, a surfboard) read better in metres.
  const metres = !!d && Math.max(d.length.value, d.width.value, d.height.value) >= 1000;
  const fmt = metres ? (n: number) => (n / 1000).toFixed(2) : mm;
  const explanation = typeof eng?.build_strategy === "object" ? (eng?.build_strategy?.explanation ?? undefined) : undefined;
  return (
    <div className="grid grid-cols-[minmax(0,1.25fr)_minmax(0,0.8fr)_minmax(0,1.1fr)] gap-x-5 min-[1440px]:gap-x-8 pt-1">
      {/* The object */}
      <dl className="flex min-w-0 flex-col gap-2">
        <Row k={metres ? "Size, m" : "Size, mm"}>
          {d ? (
            <span className="inline-flex items-center gap-x-1.5 whitespace-nowrap" data-tip={d.length.source_or_assumption} data-tip-label={d.length.label}>
              <span className="font-mono">
                <Tick value={d.length.value} format={fmt} /> <span className="text-ink-4">×</span> <Tick value={d.width.value} format={fmt} />{" "}
                <span className="text-ink-4">×</span> <Tick value={d.height.value} format={fmt} />
              </span>
              <LabelBadge label={d.length.label} tip={d.length.source_or_assumption} small />
            </span>
          ) : (
            <span className="text-ink-4">—</span>
          )}
        </Row>
        <div ref={look}>
          <Row k="Look">
            <span className="flex items-start gap-2">
              <span className="mt-[3px] h-3.5 w-3.5 shrink-0 rounded-full shadow-[inset_0_0_0_1px_rgb(0_0_0/0.12)]" style={{ background: p.color_hex ?? "transparent" }} aria-hidden />
              <span className="min-w-0">
                {p.color_name ?? p.color_hex ?? "—"}
                <span className="block text-2xs text-ink-3">{[p.material, p.finish].filter(Boolean).join(" · ")}</span>
              </span>
            </span>
          </Row>
        </div>
        <Row k="Build path">
          {kind ? (
            <span title={explanation} className="cursor-help">
              {BUILD_TEXT[kind]}
            </span>
          ) : (
            <span className="text-ink-4">—</span>
          )}
        </Row>
        <div ref={certs}>
          <Row k="Compliance">
            <Certifications list={p.certifications} />
          </Row>
        </div>
      </dl>

      {/* The cost */}
      <div className="min-w-0">
        <p className="text-sm text-ink-3">{perInst ? "Per installation" : "Unit cost"}</p>
        {perInst && (inst.installed || inst.installer) ? (
          // One site = one sale, figures of the current version: what the customer pays vs what the install costs.
          <dl className="mt-1 flex flex-col gap-1">
            {(
              [
                ["Installed price", inst.installed],
                ["Installer cost", inst.installer],
              ] as const
            ).map(([k, v]) =>
              v ? (
                <div key={k} className="flex items-baseline justify-between gap-2 text-sm" data-tip={v.source_or_assumption} data-tip-label={v.label}>
                  <dt className="text-2xs text-ink-3">{k}</dt>
                  <dd className="flex items-center gap-1.5">
                    <Tick value={v.value} format={money(v.unit)} className="text-ink" />
                    <LabelBadge label={v.label} tip={v.source_or_assumption} small />
                  </dd>
                </div>
              ) : null,
            )}
          </dl>
        ) : (
          <ul className="mt-1 flex flex-col gap-0.5">
            {p.unit_costs.map((u) => (
              <li key={u.quantity} className="grid grid-cols-[36px_auto_1fr] items-center gap-x-2 text-sm" data-tip={u.source_or_assumption ?? undefined} data-tip-label={u.label}>
                <span className="font-mono text-2xs text-ink-3">{qty(u.quantity)}</span>
                <Tick value={u.value} format={usd} className="text-ink" />
                <LabelBadge label={u.label} tip={u.source_or_assumption} small />
              </li>
            ))}
          </ul>
        )}
        {costs && !perInst && (
          // A target price was set: what it means at the first-order volume (stage 5 of the current version).
          <div className="mt-1.5 flex flex-col gap-0.5 text-2xs text-ink-2">
            {(() => {
              const t = costs.tiers.find((x) => x.quantity === costs.reference_quantity) ?? costs.tiers[Math.min(1, costs.tiers.length - 1)];
              return t ? (
                <span className="flex items-center gap-1.5" data-tip={t.margin_pct.source_or_assumption} data-tip-label={t.margin_pct.label}>
                  Margin @{qty(t.quantity)} <span className="font-mono text-ink">{t.margin_pct.value.toFixed(1)}%</span> <LabelBadge label={t.margin_pct.label} small />
                </span>
              ) : null;
            })()}
            {costs.breakeven_units.source_or_assumption.trim().toUpperCase().startsWith("NOT REACHABLE") ? (
              <span className="text-danger" title={costs.breakeven_units.source_or_assumption}>
                Break-even not reachable at this retail price
              </span>
            ) : (
              <span className="flex items-center gap-1.5" data-tip={costs.breakeven_units.source_or_assumption} data-tip-label={costs.breakeven_units.label}>
                Break-even <span className="font-mono text-ink">{Math.round(costs.breakeven_units.value).toLocaleString("en-US")}</span> units{" "}
                <LabelBadge label={costs.breakeven_units.label} small />
              </span>
            )}
          </div>
        )}
        <p className="mt-1.5 text-2xs text-ink-3">
          <Tick value={p.bom_count} format={(n) => String(Math.round(n))} /> BOM lines
        </p>
      </div>

      {/* The makers */}
      <div ref={bars} className="min-w-0">
        <p className="flex items-center justify-between gap-2 text-sm text-ink-3">
          Top {partnerTitle(eng).toLowerCase()}
          <LabelBadge label="fictional" tip={`Simulated ${partnerTitle(eng, false).toLowerCase()} network — demo data`} small text />
        </p>
        <ul className="mt-1 flex flex-col gap-1.5">
          {p.top_factories.slice(0, 3).map((f) => (
            <li key={f.name} className="grid grid-cols-[minmax(0,1fr)_40px_24px] items-center gap-x-2.5 text-sm">
              <span className="min-w-0 leading-5 text-ink">{f.name.replace(/\s*\(fictional\)\s*$/i, "")}</span>
              <span className="h-[3px] overflow-hidden rounded-full bg-paper-2" aria-hidden>
                <span data-bar className="block h-full origin-left rounded-full bg-ink-3" style={{ width: `${Math.min(100, f.score)}%` }} />
              </span>
              <span className="text-right font-mono text-ink-2">{Math.round(f.score)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
