"use client";

import { Fragment, type Ref, useEffect, useLayoutEffect, useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import { createPortal, useFrame, useThree, type ThreeEvent } from "@react-three/fiber";
import { CameraControls, CameraControlsImpl, Environment, Grid, Html, Line, Outlines, useGLTF } from "@react-three/drei";
import { DepthOfField, EffectComposer, N8AO, ToneMapping, Vignette } from "@react-three/postprocessing";
import { ToneMappingMode } from "postprocessing";
import type { AnatomyLayer, AnatomyStep, PartMeta } from "@/lib/parts";
import { addSynthetic, dampV, indexGltf, isShell, xrayMaterial, type Indexed, type PartNode } from "./model";

/** Plain-data view of the indexed parts, for the stage's render (no refs read during render). */
export type PartsSummary = { shells: string[]; synthetic: string[]; count: number };
const summarise = (ix: Indexed): PartsSummary => {
  const shells: string[] = [];
  const synthetic: string[] = [];
  ix.parts.forEach((p) => {
    if (p.synthetic) synthetic.push(p.id);
    else if (isShell(p)) shells.push(p.id);
  });
  return { shells, synthetic, count: ix.parts.size };
};

export const FOV = 28;
const DEG = Math.PI / 180;
const HDRI = "/env/studio_small_09_1k.hdr";
const ACTION = CameraControlsImpl.ACTION;

export type Preset = "3q" | "front" | "side" | "top";
const PRESETS: Record<Preset, [number, number]> = { "3q": [-28, 72], front: [0, 84], side: [90, 84], top: [0, 0.5] };

/** What the stage shows; every field is plain data so the scene re-renders only when it changes. */
export type Look = {
  dark: boolean;
  /** Exploded layer ids ("all" = every layer, plus a radial spread). */
  exploded: Set<string> | "all";
  xray: boolean;
  /** Parts ghosted like an X-ray shell (anatomy: the exterior once the product opens). */
  ghost: Set<string>;
  hovered: string | null;
  selected: string | null;
  focus: string[];
  hidden: Set<string>;
  preview: { id: string; colour: string } | null;
  labels: string[];
  capturing: boolean;
};

export type RigApi = {
  preset: (p: Preset, instant?: boolean) => void;
  focusPart: (id: string) => void;
  goTo: (c: AnatomyStep["camera"], instant?: boolean) => void;
  snapshot: () => { pos: THREE.Vector3; target: THREE.Vector3 };
  restore: (s: { pos: THREE.Vector3; target: THREE.Vector3 }) => void;
  stopSpin: () => void;
};

// ------------------------------------------------------------------ the product

export function Product({
  url,
  look,
  layers,
  meta,
  onIndexed,
  onHover,
  onSelect,
  onFocus,
  partsRef,
  reduced,
  internals,
  partsCount,
  onBounds,
}: {
  /** The exploded layout's bounding sphere (null when assembled), for the camera framing. */
  onBounds?: (b: { center: THREE.Vector3; radius: number } | null) => void;
  /** Parts indexed so far (grows when internals are synthesised) — re-derives the picking and explode maps. */
  partsCount: number;
  url: string;
  look: Look;
  layers: AnatomyLayer[] | null;
  meta: Map<string, PartMeta>;
  /** Anatomy parts to synthesise when the GLB lacks them (local illustrative internals). */
  internals: PartMeta[] | null;
  onIndexed: (ix: Indexed, summary: PartsSummary) => void;
  onHover: (id: string | null, x: number, y: number) => void;
  onSelect: (id: string | null) => void;
  onFocus: (id: string) => void;
  partsRef: MutableRefObject<Indexed | null>;
  reduced: boolean;
}) {
  const gltf = useGLTF(url, "/draco/");
  const ix = useMemo(() => indexGltf(gltf as unknown as Parameters<typeof indexGltf>[0]), [gltf]);
  const invalidate = useThree((s) => s.invalidate);
  useLayoutEffect(() => {
    partsRef.current = ix;
    onIndexed(ix, summarise(ix));
  }, [ix]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!internals) return;
    const before = ix.parts.size;
    addSynthetic(ix, internals);
    if (ix.parts.size !== before) onIndexed(ix, summarise(ix));
  }, [ix, internals]); // eslint-disable-line react-hooks/exhaustive-deps

  const meshToPart = useMemo(() => {
    const m = new Map<THREE.Object3D, string>();
    ix.parts.forEach((p) => p.meshes.forEach((mesh) => m.set(mesh, p.id)));
    return m;
  }, [ix, partsCount]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- explode targets (world metres) per part
  const targets = useMemo(() => {
    const out = new Map<string, THREE.Vector3>();
    const layerOf = new Map<string, AnatomyLayer>();
    layers?.forEach((l) => l.parts.forEach((id) => layerOf.set(id, l)));
    const all = look.exploded === "all";
    ix.parts.forEach((p) => {
      const v = new THREE.Vector3();
      const l = layerOf.get(p.id);
      if (l && (all || (look.exploded as Set<string>).has(l.id))) v.set(...l.explode_vector).multiplyScalar(l.explode_distance_mm / 1000);
      const m = meta.get(p.id);
      if (all && m?.explode_vector && m.explode_distance_mm) {
        // C2: the assembly's own explode direction (from the joint axis, cumulative along the tree).
        v.add(new THREE.Vector3(...m.explode_vector).multiplyScalar(m.explode_distance_mm / 1000));
      } else if (all) {
        // A calm radial spread on top of the layers (or alone when there is no layer data).
        const r = p.centroid.clone().sub(ix.center);
        if (l) r.y = 0;
        v.add(r.multiplyScalar(l ? 0.45 : 0.9));
      }
      out.set(p.id, v);
    });
    return out;
  }, [ix, partsCount, layers, look.exploded, meta]); // eslint-disable-line react-hooks/exhaustive-deps

  // Exploded / anatomy framing: the bounding sphere of every visible part at its target offset.
  useEffect(() => {
    if (!onBounds) return;
    if (look.exploded !== "all" && !(look.exploded as Set<string>).size) return onBounds(null);
    const box = new THREE.Box3();
    ix.parts.forEach((p) => {
      if (look.hidden.has(p.id) || !p.object.visible) return;
      const c = p.centroid.clone().add(targets.get(p.id) ?? new THREE.Vector3());
      box.expandByPoint(c.clone().addScalar(p.radius)).expandByPoint(c.clone().addScalar(-p.radius));
    });
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    onBounds(sphere.radius > 0 ? { center: sphere.center, radius: sphere.radius } : null);
  }, [targets, look.hidden, look.exploded]); // eslint-disable-line react-hooks/exhaustive-deps

  // Labels: projected every rendered frame; a label that would overlap a higher-priority one (or leave the view) hides.
  const labels = useMemo(() => new Map<string, LabelHandle>(), []);
  const proj = useMemo(() => new THREE.Vector3(), []);
  const collide = (state: { camera: THREE.Camera; size: { width: number; height: number } }) => {
    const kept: [number, number, number, number][] = [];
    let changed = false;
    for (const id of look.labels) {
      const h = labels.get(id);
      const el = h?.el.current;
      if (!h || !el) continue;
      if (!h.w) h.w = (el.firstElementChild as HTMLElement | null)?.offsetWidth ?? 0;
      h.p.object.localToWorld(proj.copy(h.b)).project(state.camera);
      const x = ((proj.x + 1) / 2) * state.size.width;
      const y = ((1 - proj.y) / 2) * state.size.height;
      const r: [number, number, number, number] = [x, y - 12, x + (h.w || 120) + 8, y + 12];
      const inside = proj.z < 1 && r[0] >= 0 && r[2] <= state.size.width && r[1] >= 0 && r[3] <= state.size.height;
      const show = inside && !kept.some((k) => r[0] < k[2] && r[2] > k[0] && r[1] < k[3] && r[3] > k[1]);
      if (show) kept.push(r);
      if (show !== h.shown) {
        h.shown = show;
        el.style.opacity = show ? "1" : "0";
        if (h.line.current) h.line.current.visible = show;
        changed = true;
      }
    }
    return changed;
  };

  const tmp = useMemo(() => new THREE.Vector3(), []);
  useFrame((state, dt) => {
    let moving = false;
    ix.parts.forEach((p) => {
      const to = targets.get(p.id);
      if (!to) return;
      if (reduced) p.offset.copy(to);
      else if (dampV(p.offset, to, 5.5, Math.min(dt, 0.05), ix.radius * 0.0005)) moving = true;
      tmp.copy(p.offset).applyQuaternion(p.toLocal);
      p.object.position.copy(p.base).add(tmp);
    });
    if (collide(state) || moving) invalidate();
  });

  // ---- materials: X-ray ghosts, live colour preview, visibility
  const xray = useMemo(() => xrayMaterial(look.dark), [look.dark]);
  useEffect(() => {
    ix.parts.forEach((p) => {
      const ghost = (look.xray && isShell(p)) || look.ghost.has(p.id);
      p.object.visible = !look.hidden.has(p.id);
      p.meshes.forEach((m) => {
        m.material = ghost ? xray : (p.orig.get(m) as THREE.Material);
        m.castShadow = m.receiveShadow = false;
        m.renderOrder = ghost ? 2 : 0;
      });
      const base = p.orig.get(p.meshes[0]);
      const mats = (Array.isArray(base) ? base : [base]).filter(Boolean) as THREE.MeshStandardMaterial[];
      mats.forEach((mat) => {
        if (!mat.userData.__colour && mat.color) mat.userData.__colour = mat.color.getHex();
        if (look.preview?.id === p.id && mat.color) mat.color.set(look.preview.colour);
        else if (mat.userData.__colour !== undefined && mat.color) mat.color.setHex(mat.userData.__colour);
      });
    });
    invalidate();
  }, [ix, partsCount, look.xray, look.ghost, look.hidden, look.preview, xray, invalidate]);

  // ---- picking: the first hit that is not a ghosted shell
  const pick = (e: ThreeEvent<PointerEvent | MouseEvent>) => {
    for (const hit of e.intersections) {
      const id = meshToPart.get(hit.object);
      if (!id) continue;
      const p = ix.parts.get(id);
      if (!p || !p.object.visible) continue;
      const ghost = (look.xray && isShell(p)) || look.ghost.has(id);
      if (ghost && e.intersections.some((h) => h !== hit && meshToPart.has(h.object) && !isGhost(meshToPart.get(h.object)!))) continue;
      return id;
    }
    return null;
  };
  const isGhost = (id: string) => {
    const p = ix.parts.get(id);
    return !!p && ((look.xray && isShell(p)) || look.ghost.has(id));
  };

  const outlined: [PartNode, string][] = [];
  if (!look.capturing) {
    const sel = look.selected ? ix.parts.get(look.selected) : null;
    const hov = look.hovered && look.hovered !== look.selected ? ix.parts.get(look.hovered) : null;
    if (sel) outlined.push([sel, look.dark ? "#FFFFFF" : "#FF4F00"]);
    if (hov) outlined.push([hov, look.dark ? "#C9CDD2" : "#111111"]);
    look.focus.forEach((id) => {
      const p = ix.parts.get(id);
      if (p && p !== sel && p !== hov) outlined.push([p, look.dark ? "#8A8F96" : "#5F5E5A"]);
    });
  }

  return (
    <>
      <primitive
        object={ix.root}
        onPointerMove={(e: ThreeEvent<PointerEvent>) => {
          e.stopPropagation();
          onHover(pick(e), e.nativeEvent.clientX, e.nativeEvent.clientY);
        }}
        onPointerLeave={() => onHover(null, 0, 0)}
        onClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation();
          if (e.delta > 4) return;
          onSelect(pick(e));
        }}
        onDoubleClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation();
          const id = pick(e);
          if (id) onFocus(id);
        }}
      />
      {outlined.flatMap(([p, colour]) =>
        p.meshes.map((m) => (
          <Fragment key={`${p.id}-${m.uuid}-${colour}`}>
            {createPortal(<Outlines thickness={look.dark ? 1.6 : 2} color={colour} transparent opacity={0.9} angle={Math.PI / 5} />, m)}
          </Fragment>
        )),
      )}
      {!look.capturing &&
        look.labels.map((id, i) => {
          const p = ix.parts.get(id);
          const m = meta.get(id) ?? p?.meta;
          return p && m && p.object.visible ? (
            <PartLabel key={id} p={p} name={m.name} dark={look.dark} radius={ix.radius} center={ix.center} index={i} count={look.labels.length} registry={labels} />
          ) : null;
        })}
    </>
  );
}

/** A floating label on a thin leader line, hung from the part (it travels with the part when exploded). */
/** A floating label's handles for the collision pass (screen-space, priority order). */
type LabelHandle = { p: PartNode; b: THREE.Vector3; el: { current: HTMLDivElement | null }; line: { current: THREE.Object3D | null }; w: number; shown: boolean };

function PartLabel({
  p,
  name,
  dark,
  radius,
  center,
  index,
  count,
  registry,
}: {
  p: PartNode;
  name: string;
  dark: boolean;
  radius: number;
  center: THREE.Vector3;
  index: number;
  count: number;
  registry: Map<string, LabelHandle>;
}) {
  const { a, b } = useMemo(() => {
    // Outward from the product centre; parts near the centre (and several labels at once) fan out by index.
    const out = p.centroid.clone().sub(center).setY(0);
    if (count > 1 || out.lengthSq() < (radius * 0.15) ** 2) {
      const ang = Math.PI * 0.25 + (index / Math.max(1, count)) * Math.PI * 2;
      out.set(Math.cos(ang), 0, Math.sin(ang));
    }
    out.normalize().multiplyScalar(radius * (count > 1 ? 0.42 : 0.32)).add(new THREE.Vector3(0, radius * (0.1 + 0.07 * index), 0));
    const inv = p.toLocal.clone();
    return { a: p.local.clone(), b: p.local.clone().add(out.applyQuaternion(inv)) };
  }, [p, radius, center, index, count]);
  const el = useRef<HTMLDivElement | null>(null);
  const line = useRef<THREE.Object3D | null>(null);
  const handle = useMemo<LabelHandle>(() => ({ p, b, el, line, w: 0, shown: true }), [p, b]);
  useEffect(() => {
    registry.set(p.id, handle);
    return () => void registry.delete(p.id);
  }, [registry, p.id, handle]);
  return createPortal(
    <group>
      <Line
        ref={line as unknown as Ref<never>}
        points={[a, b]} color={dark ? "#E8E8E8" : "#111111"} lineWidth={1} transparent opacity={dark ? 0.55 : 0.45} depthTest={false} renderOrder={5} />
      <Html ref={el} position={b} center={false} zIndexRange={[20, 10]} style={{ pointerEvents: "none", transition: "opacity 150ms cubic-bezier(.2,.7,.2,1)" }}>
        <span
          className={`-translate-y-1/2 whitespace-nowrap rounded-full px-2 py-0.5 text-2xs font-medium ${dark ? "bg-white/10 text-white/90" : "bg-surface/90 text-ink"}`}
          style={{ display: "inline-block", marginLeft: 4 }}
        >
          {name}
        </span>
      </Html>
    </group>,
    p.object,
  );
}

// ------------------------------------------------------------------ camera

export function Rig({
  apiRef,
  radius,
  reduced,
  dark,
  spin,
  frame,
  onView,
  partsRef,
  center,
}: {
  /** Exploded framing: the sphere to fit (null = the assembled product). */
  frame: { center: THREE.Vector3; radius: number } | null;
  /** Bbox centre of the product (world): presets orbit around it. */
  center: THREE.Vector3;
  apiRef: MutableRefObject<RigApi | null>;
  radius: number;
  reduced: boolean;
  dark: boolean;
  /** Idle auto-rotate allowed (normal scene, nothing hovered or selected). */
  spin: boolean;
  onView?: (widthM: number) => void;
  partsRef: MutableRefObject<Indexed | null>;
}) {
  const cc = useRef<CameraControlsImpl>(null);
  const get = useThree((s) => s.get);
  const invalidate = useThree((s) => s.invalidate);
  const lastTouch = useRef(-1e9);
  const fovGoal = useRef(FOV);
  const fit = (r: number, fov = FOV) => (r / Math.sin((fov / 2) * DEG)) * 1.06;

  useEffect(() => {
    const c = cc.current;
    if (!c) return;
    c.minDistance = radius * 1.05;
    c.maxDistance = radius * 14;
    c.smoothTime = reduced ? 0 : 0.42;
    c.draggingSmoothTime = reduced ? 0 : 0.12;
    c.mouseButtons.right = ACTION.NONE;
    c.mouseButtons.middle = ACTION.NONE;
    c.mouseButtons.wheel = dark ? ACTION.NONE : ACTION.DOLLY;
    c.touches.two = ACTION.TOUCH_DOLLY;
    c.touches.three = ACTION.NONE;
    const camera = get().camera as THREE.PerspectiveCamera;
    camera.near = radius / 60;
    camera.far = radius * 400;
    camera.updateProjectionMatrix();
  }, [radius, reduced, dark, get]);

  const place = (az: number, polar: number, dist: number, instant: boolean) => {
    const c = cc.current;
    if (!c) return;
    const t = (frame?.center ?? center).clone();
    const pos = new THREE.Vector3().setFromSphericalCoords(dist, polar * DEG, az * DEG).add(t);
    fovGoal.current = FOV;
    c.setLookAt(pos.x, pos.y, pos.z, t.x, t.y, t.z, !instant && !reduced);
    invalidate();
  };

  useEffect(() => {
    apiRef.current = {
      preset: (p, instant = false) => place(PRESETS[p][0], PRESETS[p][1], fit(frame?.radius ?? radius), instant),
      focusPart: (id) => {
        const c = cc.current;
        const p = partsRef.current?.parts.get(id);
        if (!c || !p) return;
        const at = p.centroid.clone().add(p.offset);
        const dir = new THREE.Vector3();
        c.getPosition(dir).sub(c.getTarget(new THREE.Vector3())).normalize();
        const d = Math.max(fit(p.radius) * 1.4, radius * 1.1);
        const pos = at.clone().add(dir.multiplyScalar(d));
        lastTouch.current = performance.now();
        c.setLookAt(pos.x, pos.y, pos.z, at.x, at.y, at.z, !reduced);
      },
      goTo: (cam, instant = false) => {
        const c = cc.current;
        if (!c) return;
        const [px, py, pz] = cam.position_mm.map((v) => v / 1000);
        const [tx, ty, tz] = cam.target_mm.map((v) => v / 1000);
        fovGoal.current = cam.fov_deg || FOV;
        if (instant || reduced) {
          const camera = get().camera as THREE.PerspectiveCamera;
          camera.fov = fovGoal.current;
          camera.updateProjectionMatrix();
        }
        c.setLookAt(px, py, pz, tx, ty, tz, !instant && !reduced);
        invalidate();
      },
      snapshot: () => ({ pos: cc.current!.getPosition(new THREE.Vector3()), target: cc.current!.getTarget(new THREE.Vector3()) }),
      restore: (s) => cc.current?.setLookAt(s.pos.x, s.pos.y, s.pos.z, s.target.x, s.target.y, s.target.z, false),
      stopSpin: () => void (lastTouch.current = performance.now()),
    };
  }); // refreshed every render: closures see the current radius / flags

  // First framing: the ¾ view, instantly.
  useEffect(() => {
    place(PRESETS["3q"][0], PRESETS["3q"][1], fit(radius), true);
  }, [radius, center]); // eslint-disable-line react-hooks/exhaustive-deps

  // Exploded views: re-frame on the exploded bounds (or back on the product), keeping the viewing direction.
  const firstFit = useRef(true);
  const frameKey = frame ? `${frame.center.toArray().map((v) => v.toFixed(4)).join(",")}|${frame.radius.toFixed(4)}` : "none";
  useEffect(() => {
    if (firstFit.current) {
      firstFit.current = false;
      return;
    }
    const c = cc.current;
    if (dark || !c) return;
    const dir = c.getPosition(new THREE.Vector3()).sub(c.getTarget(new THREE.Vector3())).normalize();
    const t = (frame?.center ?? center).clone();
    const pos = t.clone().add(dir.multiplyScalar(fit((frame?.radius ?? radius) * (frame ? 1.08 : 1))));
    c.setLookAt(pos.x, pos.y, pos.z, t.x, t.y, t.z, !reduced);
    invalidate();
  }, [frameKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Demand frameloop: while the turntable waits out its 6 s idle delay, nothing renders — wake it up.
  useEffect(() => {
    if (!spin || reduced) return;
    invalidate();
    const t = setInterval(() => performance.now() - lastTouch.current > 6000 && invalidate(), 500);
    return () => clearInterval(t);
  }, [spin, reduced, invalidate]);

  const lastW = useRef(0);
  useFrame((state, dt) => {
    const c = cc.current;
    if (!c) return;
    const camera = state.camera as THREE.PerspectiveCamera;
    // FOV eases toward the step's lens.
    if (Math.abs(camera.fov - fovGoal.current) > 0.01) {
      camera.fov += (fovGoal.current - camera.fov) * (1 - Math.exp(-4 * Math.min(dt, 0.05)));
      camera.updateProjectionMatrix();
      invalidate();
    }
    // Idle turntable: 12°/s, stops on interaction, resumes 6 s after the last one.
    if (spin && !reduced && performance.now() - lastTouch.current > 6000) {
      c.azimuthAngle += 12 * DEG * Math.min(dt, 0.05);
      invalidate();
    }
    if (onView) {
      const w = 2 * c.distance * Math.tan((camera.fov / 2) * DEG) * (state.size.width / Math.max(1, state.size.height));
      if (Math.abs(w - lastW.current) / Math.max(w, 1e-6) > 0.004) {
        lastW.current = w;
        onView(w);
      }
    }
  });

  return (
    <CameraControls
      ref={cc}
      makeDefault
      onStart={() => void (lastTouch.current = performance.now())}
      onEnd={() => void (lastTouch.current = performance.now())}
    />
  );
}

// ------------------------------------------------------------------ light, ground, effects

export function Lighting({ dark, radius }: { dark: boolean; radius: number }) {
  const r = radius;
  return (
    <>
      <Environment files={HDRI} environmentIntensity={dark ? 0.55 : 0.95} environmentRotation={[0, Math.PI / 5, 0]} />
      {/* Soft key from the upper left, a touch warm. */}
      <directionalLight position={[-r * 4, r * 6, r * 3]} intensity={dark ? 2.2 : 1.1} color={dark ? "#F4F1EA" : "#FFF7EE"} />
      {dark ? (
        <>
          {/* Rim from behind, cool: separates the parts from the black. */}
          <directionalLight position={[r * 3, r * 2.5, -r * 5]} intensity={2.4} color="#DDE6F0" />
          <color attach="background" args={["#0B0B0C"]} />
        </>
      ) : (
        <hemisphereLight args={["#FFFFFF", "#E9E4DA", 0.35]} />
      )}
    </>
  );
}

export function Ground({ dark, size, center, drop }: { dark: boolean; size: THREE.Vector3; center: THREE.Vector3; drop: number }) {
  const r = size.length() / 2;
  const y = center.y - size.y / 2 - drop;
  if (dark)
    return (
      <Grid
        position={[center.x, y - r * 0.02, center.z]}
        args={[r * 30, r * 30]}
        cellSize={r / 8}
        cellThickness={0.6}
        cellColor="#26272A"
        sectionSize={r / 2}
        sectionThickness={0.9}
        sectionColor="#34363A"
        fadeDistance={r * 9}
        fadeStrength={1.6}
        infiniteGrid
        followCamera={false}
      />
    );
  return <SoftShadow size={size} center={center} y={y} />;
}

let shadowTex: THREE.CanvasTexture | null = null;
/** A soft radial falloff with a darker contact core, drawn once (shared by every stage). */
function shadowTexture() {
  if (shadowTex) return shadowTex;
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d")!;
  const wide = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  wide.addColorStop(0, "rgba(42,38,34,0.55)");
  wide.addColorStop(0.45, "rgba(42,38,34,0.28)");
  wide.addColorStop(1, "rgba(42,38,34,0)");
  g.fillStyle = wide;
  g.fillRect(0, 0, 256, 256);
  const core = g.createRadialGradient(128, 128, 0, 128, 128, 70);
  core.addColorStop(0, "rgba(30,27,24,0.45)");
  core.addColorStop(1, "rgba(30,27,24,0)");
  g.fillStyle = core;
  g.fillRect(0, 0, 256, 256);
  shadowTex = new THREE.CanvasTexture(c);
  shadowTex.colorSpace = THREE.SRGBColorSpace;
  return shadowTex;
}

/** Grounded soft shadow under the product's footprint (static: no per-frame cost, follows the layout on re-render). */
function SoftShadow({ size, center, y }: { size: THREE.Vector3; center: THREE.Vector3; y: number }) {
  const map = useMemo(() => shadowTexture(), []);
  return (
    <mesh position={[center.x, y + size.y * 0.002, center.z]} rotation={[-Math.PI / 2, 0, 0]} renderOrder={-1}>
      <planeGeometry args={[size.x * 1.45, size.z * 1.45]} />
      <meshBasicMaterial map={map} transparent depthWrite={false} opacity={0.5} toneMapped={false} />
    </mesh>
  );
}

export function Effects({ dark, radius, focus, capturing, xray }: { dark: boolean; radius: number; focus: THREE.Vector3 | null; capturing: boolean; xray: boolean }) {
  if (dark)
    return (
      <EffectComposer multisampling={4} key="dark">
        <N8AO aoRadius={radius * 0.25} distanceFalloff={1} intensity={1.4} quality="low" halfRes />
        <DepthOfField target={focus ?? new THREE.Vector3()} worldFocusRange={radius * 0.9} bokehScale={focus ? 2.2 : 0} resolutionScale={0.5} />
        <Vignette offset={0.28} darkness={0.62} />
        <ToneMapping mode={ToneMappingMode.AGX} />
      </EffectComposer>
    );
  return (
    // N8AO writes an opaque frame when transparent (X-ray) materials are on screen: off in X-ray, where AO adds nothing.
    <EffectComposer multisampling={4} key={xray ? "light-xray" : "light"}>
      <N8AO enabled={!xray} aoRadius={radius * 0.22} distanceFalloff={1} intensity={1.6} quality="medium" halfRes />
      <Vignette offset={0.42} darkness={capturing ? 0 : 0.16} />
      <ToneMapping mode={ToneMappingMode.AGX} />
    </EffectComposer>
  );
}

// ------------------------------------------------------------------ dev performance probe

declare global {
  interface Window {
    __plxPerf?: { fps: number; frames: number; dpr: number; calls: number; triangles: number; glbMs?: number };
  }
}

/** Counts rendered frames (dev + Playwright): window.__plxPerf = {fps, calls, triangles}. Never logs errors. */
export function PerfProbe() {
  const acc = useRef({ n: 0, t: 0, total: 0 });
  const gl = useThree((s) => s.gl);
  useFrame(() => {
    const a = acc.current;
    a.n++;
    a.total++;
    const now = performance.now();
    if (!a.t) a.t = now;
    if (now - a.t >= 1000) {
      const fps = Math.round((a.n * 1000) / (now - a.t));
      window.__plxPerf = { ...(window.__plxPerf ?? { glbMs: undefined }), fps, frames: a.total, dpr: gl.getPixelRatio(), calls: gl.info.render.calls, triangles: gl.info.render.triangles };
      if (process.env.NODE_ENV === "development" && fps > 0) console.debug(`[viewer3d] ${fps} fps · ${gl.info.render.calls} calls · ${gl.info.render.triangles} tris · dpr ${gl.getPixelRatio()}`);
      a.n = 0;
      a.t = now;
    }
  });
  return null;
}
