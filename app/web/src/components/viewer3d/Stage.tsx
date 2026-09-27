"use client";

import { Component, Suspense, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Canvas, type RootState } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import type { VersionPreview } from "@/types/contracts";
import { fileUrl } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { loadAnime, reducedMotion } from "@/lib/motion";
import { ANATOMY_LABEL, useAnatomyApi, usePartsApi, usePartsRoutes, type PartEdit, type PartMeta, type ProjectAnatomy } from "@/lib/parts";
import { mockAnatomy, mockParts, type BomLine } from "@/lib/partsMock";
import { Spinner } from "../ui";
import type { Indexed } from "./model";
import { Effects, FOV, Ground, Lighting, PerfProbe, Product, Rig, type Look, type PartsSummary, type Preset, type RigApi } from "./Scene";
import { PartPanel, PartTip } from "./PartPanel";
import { AnatomyHud } from "./AnatomyHud";
import { Toolbar } from "./Toolbar";

export type EditHandler = (part: PartMeta, edit: PartEdit) => Promise<string | null>;

export type StageProps = {
  url: string;
  alt: string;
  projectId?: string;
  /** Version shown (n) — parts / anatomy are asked for this version. */
  version?: number;
  preview?: VersionPreview | null;
  surface: "studio" | "overview";
  /** Studio only: apply a part edit; resolves to an error sentence or null. Absent = read-only part cards. */
  onEdit?: EditHandler;
  /** Why editing is off right now (previewing an old version, a job running…). */
  editNote?: string | null;
  /** Edits go through the edit route (else they are sent as a prompt). */
  editViaRoute?: boolean;
  onFail: (why: string) => void;
  /** Overview: where a part can be edited or read in full (the Studio, or the 3D-model step for examples without it). */
  editLink?: { href: string; label: string };
};

/** Hovered part, pointer position relative to the stage (and the stage size, for clamping the tooltip). */
type Hover = { id: string; x: number; y: number; w: number; h: number } | null;

class CanvasBoundary extends Component<{ onError: (e: unknown) => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(e: unknown) {
    this.props.onError(e);
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

/**
 * The photoreal product stage (react-three-fiber): studio HDRI + soft key on the paper, grounded shadow, calm orbit,
 * parts you can hover / click / edit, exploded and X-ray views, and the dark anatomy mode that walks inside the product.
 */
export default function Stage({ url, alt, projectId, version, preview, surface, onEdit, editNote, editViaRoute, onFail, editLink }: StageProps) {
  const host = useRef<HTMLDivElement>(null);
  const three = useRef<RootState | null>(null);
  const rig = useRef<RigApi | null>(null);
  const partsRef = useRef<Indexed | null>(null);
  const [reduced] = useState(reducedMotion);
  const [dbg] = useState(() => (typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("debug3d")));

  // ---- model swap: keep showing the current product until the next GLB is ready, then cross-fade.
  const [shownUrl, setShownUrl] = useState(url);
  const nextUrl = url !== shownUrl ? url : null;
  const [ix, setIx] = useState<{ url: string; info: Indexed["info"]; radius: number; size: THREE.Vector3; center: THREE.Vector3; legacy: boolean } | null>(null);
  const t0 = useRef(0);
  useEffect(() => {
    t0.current = performance.now();
  }, [url]);

  const [mode, setMode] = useState<"normal" | "anatomy">("normal");
  const [exploded, setExploded] = useState(false);
  const [xray, setXray] = useState(false);
  const [hover, setHover] = useState<Hover>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [colourPreview, setColourPreview] = useState<{ id: string; colour: string } | null>(null);
  const [capturing, setCapturing] = useState(false);
  const [active, setActive] = useState(true);
  const anatomy = mode === "anatomy";
  const wantInternals = anatomy || exploded || xray;

  // ---- data: W29 routes when served, else the local mock built from the loaded GLB (+ the BOM for internals).
  const routes = usePartsRoutes();
  const partsApi = usePartsApi(projectId, version, !!routes?.parts);
  const anatomyApi = useAnatomyApi(projectId, version, !!routes?.anatomy && wantInternals);
  const needBom = wantInternals && !!routes && !routes.anatomy && !!projectId;
  const spec = useApi<{ artifact: { bom?: BomLine[]; product_name?: string } }>(needBom ? `/projects/${projectId}/stages/3` : null);
  const bomReady = !needBom || !!spec.data || !!spec.error;

  // API parts only when they describe the GLB on screen (same part ids); else parts measured on the loaded GLB.
  const apiMatches = !!partsApi.data?.parts?.length && !!ix && partsApi.data.parts.some((p) => ix.info.nodes.some((n) => n.id === p.part_id));
  const parts: PartMeta[] = useMemo(() => {
    if (apiMatches && partsApi.data) return partsApi.data.parts;
    return ix ? mockParts(ix.info, preview) : [];
  }, [apiMatches, partsApi.data, ix, preview]);
  const source = apiMatches ? "api" : "mock";

  const anat: ProjectAnatomy | null = useMemo(() => {
    if (anatomyApi.data) return anatomyApi.data;
    if (!wantInternals || !ix || !bomReady || (routes?.anatomy && anatomyApi.loading)) return null;
    return mockAnatomy(parts, ix.info, spec.data?.artifact.bom ?? [], spec.data?.artifact.product_name ?? alt, version ?? 0, url);
  }, [anatomyApi.data, anatomyApi.loading, wantInternals, ix, bomReady, routes?.anatomy, parts, spec.data, alt, version, url]);

  const meta = useMemo(() => {
    const m = new Map<string, PartMeta>();
    parts.forEach((p) => m.set(p.part_id, p));
    anat?.parts.forEach((p) => !m.has(p.part_id) && m.set(p.part_id, p));
    return m;
  }, [parts, anat]);

  const sceneUrl = wantInternals && anat && !anat.mock && anat.glb_url ? (fileUrl(anat.glb_url) ?? shownUrl) : shownUrl;
  const steps = anat?.steps ?? [];
  const cur = anatomy ? steps[Math.min(step, Math.max(0, steps.length - 1))] : undefined;

  // ---- the look handed to the scene
  const [summary, setSummary] = useState<PartsSummary>({ shells: [], synthetic: [], count: 0 });
  const look: Look = useMemo(() => {
    const focus = cur?.focus_parts ?? [];
    const ghost = new Set<string>();
    if (anatomy && cur && cur.layers_exploded.length) summary.shells.forEach((id) => !focus.includes(id) && ghost.add(id));
    const hidden = new Set<string>(wantInternals ? [] : summary.synthetic);
    let labels: string[] = [];
    if (anatomy && cur) labels = focus.slice(0, 4);
    if (anatomy && cur && !labels.length && anat) labels = anat.layers.filter((l) => cur.layers_exploded.includes(l.id)).map((l) => biggest(l.parts, meta)).filter(Boolean) as string[];
    else if (!anatomy && exploded)
      // One candidate per layer, biggest parts first (the collision pass hides whatever would overlap them).
      labels = anat
        ? (anat.layers.map((l) => biggest(l.parts, meta)).filter(Boolean) as string[])
            .sort((x, y) => volume(meta.get(y)) - volume(meta.get(x)))
            .slice(0, 7)
        : [];
    return {
      dark: anatomy,
      exploded: anatomy ? new Set(cur?.layers_exploded ?? []) : exploded ? "all" : new Set<string>(),
      xray: !anatomy && xray,
      ghost,
      hovered: hover?.id ?? null,
      selected,
      focus: anatomy ? focus : [],
      hidden,
      preview: colourPreview,
      labels,
      capturing,
    };
  }, [anatomy, cur, exploded, xray, hover?.id, selected, colourPreview, capturing, wantInternals, summary, anat, meta]);

  // ---- camera: anatomy steps drive it; leaving anatomy returns to the ¾ view.
  useEffect(() => {
    if (anatomy && cur) rig.current?.goTo(cur.camera);
  }, [anatomy, cur]);
  const wasAnatomy = useRef(false);
  useEffect(() => {
    if (wasAnatomy.current && !anatomy) rig.current?.preset("3q");
    wasAnatomy.current = anatomy;
  }, [anatomy]);

  // ---- pause when the tab is hidden or the stage is off screen.
  useEffect(() => {
    const el = host.current;
    let visible = true;
    let onScreen = true;
    const apply = () => setActive(visible && onScreen);
    const onVis = () => {
      visible = !document.hidden;
      apply();
    };
    document.addEventListener("visibilitychange", onVis);
    const io = el ? new IntersectionObserver(([e]) => ((onScreen = e.isIntersecting), apply())) : null;
    if (el) io?.observe(el);
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      io?.disconnect();
    };
  }, []);

  // ---- anatomy navigation: scroll inside the viewer, ← → keys, buttons.
  const go = useCallback((d: number) => setStep((s) => Math.max(0, Math.min(steps.length - 1, s + d))), [steps.length]);
  useEffect(() => {
    if (!anatomy) return;
    const el = host.current;
    let acc = 0;
    let lock = 0;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const now = performance.now();
      if (now < lock) return;
      acc += e.deltaY;
      if (Math.abs(acc) > 60) {
        go(acc > 0 ? 1 : -1);
        acc = 0;
        lock = now + (reduced ? 150 : 650);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest?.("input,textarea,select")) return;
      if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(e.key)) {
        e.preventDefault();
        go(1);
      } else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(e.key)) {
        e.preventDefault();
        go(-1);
      } else if (e.key === "Escape") {
        setMode("normal");
      }
    };
    el?.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("keydown", onKey);
    return () => {
      el?.removeEventListener("wheel", onWheel);
      window.removeEventListener("keydown", onKey);
    };
  }, [anatomy, go, reduced]);

  const onIndexed = useCallback((x: Indexed, s: PartsSummary, forUrl: string) => {
    if (t0.current) window.__plxPerf = { ...(window.__plxPerf ?? { fps: 0, frames: 0, dpr: 1, calls: 0, triangles: 0 }), glbMs: Math.round(performance.now() - t0.current) };
    setIx({ url: forUrl, info: x.info, radius: x.radius, size: x.size, center: x.center, legacy: x.legacy });
    setSummary(s);
  }, []);

  // ---- W27 capture: a clean ¾ PNG of the assembled product (null in exploded / X-ray / anatomy).
  useEffect(() => {
    const el = host.current as (HTMLDivElement & { __plxCapture?: () => Promise<Blob | null> }) | null;
    if (!el) return;
    el.__plxCapture = async () => {
      const s = three.current;
      if (!s || !ix || anatomy || exploded || xray) return null;
      setCapturing(true);
      const snap = rig.current?.snapshot();
      rig.current?.preset("3q", true);
      rig.current?.stopSpin();
      const frame = () => new Promise((r) => requestAnimationFrame(() => r(null)));
      for (let i = 0; i < 4; i++) {
        s.invalidate();
        await frame();
      }
      const blob = await new Promise<Blob | null>((r) => s.gl.domElement.toBlob(r, "image/png"));
      if (snap) rig.current?.restore(snap);
      setCapturing(false);
      return blob;
    };
    return () => void delete el.__plxCapture;
  }, [ix, anatomy, exploded, xray]);

  const sel = selected ? meta.get(selected) : null;
  const hov = hover ? meta.get(hover.id) : null;
  const radius = ix?.radius ?? 0.05;
  const size = useMemo(() => ix?.size ?? new THREE.Vector3(0.1, 0.1, 0.1), [ix]);
  const center = useMemo(() => ix?.center ?? new THREE.Vector3(), [ix]);
  const drop = useMemo(() => {
    if (!anat || (!exploded && !anatomy)) return 0;
    const down = anat.layers.filter((l) => l.explode_vector[1] < 0).map((l) => (-l.explode_vector[1] * l.explode_distance_mm) / 1000);
    return Math.max(0, ...down) + (exploded ? radius * 0.3 : 0);
  }, [anat, exploded, anatomy, radius]);
  const focusPoint = useMemo(() => {
    if (!anatomy || !cur) return null;
    return new THREE.Vector3(...cur.camera.target_mm.map((v) => v / 1000));
  }, [anatomy, cur]);
  // Exploded framing: the exploded layout's real bounds, reported by the scene.
  const [explodedFrame, setExplodedFrame] = useState<{ center: THREE.Vector3; radius: number } | null>(null);
  const [viewW, setViewW] = useState(0);
  const ruler = useRef<(w: number) => void>(() => undefined);
  const onView = useCallback((w: number) => ruler.current(w), []);

  const ready = !!ix && (ix.url === shownUrl || ix.url === sceneUrl);
  const spin = !anatomy && !exploded && !xray && !hover && !selected && active && !capturing;

  return (
    <div
      ref={host}
      data-viewer3d=""
      data-ready={ready ? "1" : "0"}
      data-mode={mode}
      data-exploded={exploded ? "1" : "0"}
      data-xray={xray ? "1" : "0"}
      data-step={anatomy ? String(step) : ""}
      data-parts={String(meta.size)}
      data-source={source}
      data-anatomy-source={anat ? (anat.mock ? "mock" : "api") : ""}
      className={
        anatomy
          ? "fixed inset-x-0 bottom-[28px] top-[52px] z-40 overflow-hidden bg-[#0B0B0C]"
          : "relative h-full w-full overflow-hidden"
      }
      onPointerLeave={() => setHover(null)}
    >
      <CanvasBoundary onError={(e) => onFail(e instanceof Error ? e.message : "3D stage failed")}>
        <Canvas
          dpr={anatomy ? [1, 1.25] : [1, 1.5]}
          frameloop={active ? "demand" : "never"}
          gl={{ antialias: false, alpha: true, preserveDrawingBuffer: true, powerPreference: "high-performance" }}
          camera={{ fov: FOV, position: [0, 0.1, 0.3], near: 0.001, far: 100 }}
          onCreated={(s) => {
            three.current = s;
            s.gl.outputColorSpace = THREE.SRGBColorSpace;
            s.gl.domElement.addEventListener("webglcontextlost", (e) => {
              e.preventDefault();
              onFail("WebGL context lost");
            });
          }}
          onPointerMissed={() => setSelected(null)}
          style={{ cursor: hover ? "pointer" : anatomy ? "grab" : undefined, touchAction: "none" }}
          aria-label={`${alt}: interactive 3D model`}
          role="img"
        >
          <Suspense fallback={null}>
            <Lighting dark={anatomy} radius={radius} />
            <Product
              key={sceneUrl}
              url={sceneUrl}
              look={look}
              layers={anat?.layers ?? null}
              meta={meta}
              partsRef={partsRef}
              partsCount={summary.count}
              onBounds={anatomy ? undefined : setExplodedFrame}
              reduced={reduced}
              internals={anat?.mock && wantInternals ? anat.parts : null}
              onIndexed={(x, s) => onIndexed(x, s, sceneUrl)}
              onHover={(id, x, y) => {
                const r = host.current?.getBoundingClientRect();
                setHover(id && r ? { id, x: x - r.left, y: y - r.top, w: r.width, h: r.height } : null);
              }}
              onSelect={(id) => setSelected(id)}
              onFocus={(id) => rig.current?.focusPart(id)}
            />
            {ix && dbg !== "noground" && <Ground dark={anatomy} size={size} center={center} drop={drop} />}
            {dbg !== "nofx" && <Effects dark={anatomy} radius={radius} focus={focusPoint} capturing={capturing} xray={look.xray} />}
          </Suspense>
          {nextUrl && nextUrl !== sceneUrl && (
            <Suspense fallback={null}>
              <Preloader url={nextUrl} onReady={() => onIndexedNext(nextUrl)} />
            </Suspense>
          )}
          {ix && <Rig apiRef={rig} center={center} radius={radius} reduced={reduced} dark={anatomy} spin={spin} frame={exploded ? explodedFrame : null} onView={anatomy ? onView : undefined} partsRef={partsRef} />}
          <PerfProbe />
        </Canvas>
      </CanvasBoundary>

      {!ready && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center gap-2 text-sm text-ink-3" data-viewer-loading>
          <Spinner /> Loading 3D model
        </div>
      )}

      {hov && hover && !sel && !capturing && <PartTip part={hov} x={hover.x} y={hover.y} w={hover.w} h={hover.h} dark={anatomy} />}

      {sel && (
        <PartPanel
          key={sel.part_id}
          part={sel}
          dark={anatomy}
          top={anatomy ? 64 : surface === "overview" ? 44 : 12}
          projectId={projectId}
          onEdit={surface === "studio" && !anatomy ? onEdit : undefined}
          editNote={editNote}
          viaRoute={!!editViaRoute}
          onPreview={(c) => setColourPreview(c ? { id: sel.part_id, colour: c } : null)}
          onApplied={() => setSelected(null)}
          editLink={surface === "overview" && !anatomy ? editLink : undefined}
          onClose={() => {
            setSelected(null);
            setColourPreview(null);
          }}
        />
      )}

      {anatomy && anat && (
        <AnatomyHud
          steps={steps}
          step={Math.min(step, steps.length - 1)}
          label={anat.label || ANATOMY_LABEL}
          mock={!!anat.mock}
          onGo={(i) => setStep(i)}
          onPrev={() => go(-1)}
          onNext={() => go(1)}
          onExit={() => {
            setMode("normal");
          }}
          rulerRef={ruler}
          initialWidth={viewW}
        />
      )}
      {anatomy && !anat && (
        <div className="absolute inset-0 flex items-center justify-center gap-2 text-sm text-white/60">
          <Spinner /> Opening the product
        </div>
      )}

      {!anatomy && ready && (
        <Toolbar
          surface={surface}
          exploded={exploded}
          xray={xray}
          onPreset={(p: Preset) => rig.current?.preset(p)}
          onReset={() => {
            setExploded(false);
            setXray(false);
            setSelected(null);
            rig.current?.preset("3q");
          }}
          onExploded={() => {
            setExploded((v) => !v);
          }}
          onXray={() => {
            setXray((v) => !v);
          }}
          onAnatomy={() => {
            setSelected(null);
            setHover(null);
            setExploded(false);
            setXray(false);
            setStep(0);
            setViewW(0);
            setMode("anatomy");
          }}
        />
      )}
    </div>
  );

  function onIndexedNext(u: string) {
    // The next version's GLB is cached: swap the scene to it (the Product remounts on the cached asset), cross-fading.
    // A new version: forget the part selection and its live preview.
    setShownUrl(u);
    setSelected(null);
    setColourPreview(null);
    setHover(null);
    const el = host.current?.querySelector("canvas");
    if (el && !reduced)
      loadAnime().then((a) => {
        a?.animate(el, { opacity: [0.25, 1], duration: 400, ease: "inOutQuad" });
      });
  }
}

/** Loads a GLB into the cache without showing it (the next version, while the current one stays on screen). */
function Preloader({ url, onReady }: { url: string; onReady: () => void }) {
  useGltfPreload(url);
  useEffect(() => onReady(), []); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

function useGltfPreload(url: string) {
  useGLTF(url, "/draco/");
}

const volume = (m?: PartMeta) => (m ? m.measured_bbox_mm[0] * m.measured_bbox_mm[1] * m.measured_bbox_mm[2] : 0);

function biggest(ids: string[], meta: Map<string, PartMeta>): string | null {
  let best: string | null = null;
  let v = -1;
  for (const id of ids) {
    const m = meta.get(id);
    if (!m) continue;
    // Generic numbered names ("Painted part 20") make poor labels: only when nothing better exists.
    const generic = / \d+$/.test(m.name) ? 1e-6 : 1;
    const s = m.measured_bbox_mm[0] * m.measured_bbox_mm[1] * m.measured_bbox_mm[2] * generic;
    if (s > v) {
      v = s;
      best = id;
    }
  }
  return best;
}
