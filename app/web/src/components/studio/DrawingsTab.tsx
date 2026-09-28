"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage, fileUrl, isTransient, withRetry } from "@/lib/api";
import { useApiPaths } from "@/lib/autofill";
import type { DrawingSheet, Version } from "@/types/contracts";
import { LabelBadge, Spinner } from "../ui";

/** GET /projects/{id}/drawings (C3, behind CAD_DRAWINGS=1): present in the OpenAPI schema only when enabled. */
export const DRAWINGS_ROUTE = "/projects/{project_id}/drawings";
const NOTE = "Generated from CAD — verify before release";
const MEASURED_TIP = "Dimensions measured on the CAD (STEP bounding box and B-rep features); tolerances ISO 2768-m";

export function useDrawingsRoute(): boolean {
  return !!useApiPaths()?.has(DRAWINGS_ROUTE);
}

/** Stage 3: a link to the Studio's Drawings tab, only when this API serves drawings. */
export function DrawingsLink({ projectId }: { projectId: string }) {
  if (!useDrawingsRoute()) return null;
  return (
    <Link
      href={`/projects/${projectId}/studio?tab=drawings`}
      className="mt-1 inline-flex items-center gap-1.5 text-sm text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink"
    >
      Technical drawings (SVG + PDF)
      <span className="text-2xs text-ink-3">{NOTE}</span>
    </Link>
  );
}

function useDrawings(projectId: string, version: number | undefined, on: boolean) {
  const path = on ? `/projects/${projectId}/drawings${version ? `?version=${version}` : ""}` : null;
  const [st, setSt] = useState<{ key: string | null; data: DrawingSheet[] | null; error: string | null }>({ key: null, data: null, error: null });
  const [nonce, setNonce] = useState(0);
  useEffect(() => {
    if (!path) return;
    let live = true;
    withRetry(() => api.get<DrawingSheet[]>(path), isTransient, () => live)
      .then((d) => live && setSt({ key: path, data: d, error: null }))
      .catch((e) => live && setSt({ key: path, data: null, error: errorMessage(e) }));
    return () => void (live = false);
  }, [path, nonce]);
  const fresh = st.key === path;
  return { data: fresh ? st.data : null, error: fresh ? st.error : null, loading: !!path && !fresh, retry: () => setNonce((n) => n + 1) };
}

const dl = "press inline-flex h-7 shrink-0 items-center gap-1.5 whitespace-nowrap rounded px-2.5 text-sm font-medium";

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
      <path d="M8 2v8.5M4.5 7 8 10.5 11.5 7M3 13.5h10" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** Zoomable, pannable sheet: wheel zooms around the cursor, drag pans, double-click toggles 1× / 2.5×. */
function SheetViewer({ sheet }: { sheet: DrawingSheet }) {
  const box = useRef<HTMLDivElement>(null);
  const [t, setT] = useState({ z: 1, x: 0, y: 0 });
  const drag = useRef<{ px: number; py: number; x: number; y: number } | null>(null);
  const fit = useCallback(() => setT({ z: 1, x: 0, y: 0 }), []);
  const zoomAt = useCallback((factor: number, cx?: number, cy?: number) => {
    const el = box.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const px = cx ?? r.width / 2;
    const py = cy ?? r.height / 2;
    setT((o) => {
      const z = Math.min(12, Math.max(1, o.z * factor));
      const k = z / o.z;
      if (z === 1) return { z: 1, x: 0, y: 0 };
      return { z, x: px - (px - o.x) * k, y: py - (py - o.y) * k };
    });
  }, []);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      zoomAt(Math.exp(-e.deltaY * 0.0022), e.clientX - r.left, e.clientY - r.top);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [zoomAt]);
  const src = fileUrl(sheet.svg_url) ?? "";
  return (
    <div className="relative min-h-0 flex-1 overflow-hidden rounded-md bg-surface">
      <div
        ref={box}
        data-testid="drawing-viewer"
        className={`absolute inset-0 ${t.z > 1 ? "cursor-grab active:cursor-grabbing" : "cursor-zoom-in"}`}
        onPointerDown={(e) => {
          if (t.z === 1) return;
          (e.target as Element).setPointerCapture?.(e.pointerId);
          drag.current = { px: e.clientX, py: e.clientY, x: t.x, y: t.y };
        }}
        onPointerMove={(e) => {
          const d = drag.current;
          if (d) setT((o) => ({ ...o, x: d.x + e.clientX - d.px, y: d.y + e.clientY - d.py }));
        }}
        onPointerUp={() => (drag.current = null)}
        onPointerCancel={() => (drag.current = null)}
        onDoubleClick={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          if (t.z > 1) fit();
          else zoomAt(2.5, e.clientX - r.left, e.clientY - r.top);
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- vector sheet served by the API */}
        <img
          src={src}
          alt={`${sheet.sheet} · ${sheet.title}`}
          draggable={false}
          className="absolute inset-0 h-full w-full select-none object-contain p-3"
          style={{ transform: `translate(${t.x}px, ${t.y}px) scale(${t.z})`, transformOrigin: "0 0" }}
        />
      </div>
      <div className="absolute bottom-3 right-3 flex items-center gap-0.5 rounded-full bg-surface/95 p-0.5 text-sm shadow-[0_1px_3px_rgba(17,17,17,0.12)]">
        <button className="press h-7 w-7 rounded-full text-ink-2 hover:bg-paper-2 hover:text-ink" aria-label="Zoom out" onClick={() => zoomAt(1 / 1.5)}>
          −
        </button>
        <button className="press h-7 min-w-12 rounded-full px-2 font-mono text-2xs text-ink-2 hover:bg-paper-2 hover:text-ink" aria-label="Fit sheet" onClick={fit}>
          {Math.round(t.z * 100)}%
        </button>
        <button className="press h-7 w-7 rounded-full text-ink-2 hover:bg-paper-2 hover:text-ink" aria-label="Zoom in" onClick={() => zoomAt(1.5)}>
          +
        </button>
      </div>
    </div>
  );
}

/** Drawings (C3): the version's 2D sheets from the CAD — thumbnails, zoomable SVG, PDF / SVG downloads. */
export function DrawingsTab({ projectId, version, available }: { projectId: string; version: Version | undefined; available: boolean }) {
  const pending = !!version && (version.status === "running" || !!version.cad_pending);
  const { data, error, loading, retry } = useDrawings(projectId, version?.n, available && !pending);
  const [sel, setSel] = useState<string | null>(null);
  if (!available) return <div className="flex h-full items-center justify-center text-sm text-ink-3">Drawings are not enabled on this server.</div>;
  if (pending)
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
        <Spinner /> v{version?.n} is being built. Drawings follow its CAD.
      </div>
    );
  if (loading)
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
        <Spinner /> Drawing the sheets from the CAD…
      </div>
    );
  if (!data || data.length === 0)
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-ink-3">
        <span>{error ? `No drawings for this version: ${error}` : "No drawings for this version."}</span>
        {error && (
          <button className="press text-ink underline decoration-line-2 underline-offset-4" onClick={retry}>
            Try again
          </button>
        )}
      </div>
    );
  const cur = data.find((s) => s.sheet === sel) ?? data[0];
  return (
    <div className="flex h-full min-h-0 flex-col gap-3" data-testid="drawings-tab">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="text-sm font-medium text-ink">
          Drawings <span className="font-mono text-ink-3">v{cur.version} · {data.length} sheets</span>
        </span>
        <span className="rounded-full bg-estimate-soft px-2.5 py-0.5 text-2xs font-medium text-estimate-ink">{NOTE}</span>
        <LabelBadge label="measured" tip={MEASURED_TIP} text small />
        <span className="ml-auto flex items-center gap-1.5">
          <a href={fileUrl(cur.pdf_url) ?? undefined} download className={`${dl} bg-ink text-white hover:bg-[#2a2a2a]`}>
            <DownloadIcon /> PDF
          </a>
          <a href={fileUrl(cur.svg_url) ?? undefined} download className={`${dl} bg-surface text-ink shadow-[inset_0_0_0_1px_var(--color-line-2)] hover:bg-sunken`}>
            <DownloadIcon /> SVG
          </a>
          <a href={fileUrl(cur.set_pdf_url) ?? undefined} download className={`${dl} text-ink-2 hover:bg-paper-2 hover:text-ink`}>
            <DownloadIcon /> All sheets
          </a>
        </span>
      </div>
      <div className="flex min-h-0 flex-1 gap-3">
        <ul className="flex w-44 shrink-0 flex-col gap-2 overflow-y-auto pr-1" aria-label="Sheets">
          {data.map((s) => {
            const on = s.sheet === cur.sheet;
            return (
              <li key={s.sheet}>
                <button
                  onClick={() => setSel(s.sheet)}
                  aria-pressed={on}
                  title={s.title}
                  className={`press flex w-full flex-col gap-1 rounded-md p-1.5 text-left ${on ? "bg-surface shadow-[inset_0_0_0_1px_var(--color-ink)]" : "hover:bg-surface"}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- vector thumbnail */}
                  <img src={fileUrl(s.svg_url) ?? ""} alt="" loading="lazy" className="aspect-[1.414] w-full rounded-sm bg-white object-contain" />
                  <span className="flex items-center gap-1.5 px-0.5 text-2xs">
                    {on && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />}
                    <span className="font-mono text-ink">{s.sheet}</span>
                    <span className="min-w-0 truncate text-ink-2">{s.title}</span>
                  </span>
                  <span className="px-0.5 font-mono text-2xs text-ink-3">
                    {s.size} · {s.scale}
                    {s.qty > 1 ? ` · ×${s.qty}` : ""}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2">
          <SheetViewer key={cur.svg_url} sheet={cur} />
          <p className="flex flex-wrap items-center gap-x-3 text-2xs text-ink-3">
            <span className="text-ink-2">{cur.title}</span>
            <span className="font-mono">
              {cur.bbox_mm.map((v) => Math.round(v * 10) / 10).join(" × ")} mm
            </span>
            {cur.bom_item_id && <span className="font-mono">BOM {cur.bom_item_id}</span>}
            <span className="ml-auto">Scroll to zoom · drag to pan · double-click to zoom</span>
          </p>
        </div>
      </div>
    </div>
  );
}
