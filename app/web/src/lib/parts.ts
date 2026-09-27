"use client";

import { useEffect, useState } from "react";
import type { LabeledValue, StudioAccepted } from "@/types/contracts";
import { api, ApiError, errorMessage, isTransient, withRetry } from "./api";
import { useApiPaths } from "./autofill";

/**
 * 3D parts & anatomy (contracts/api.md "3D parts & anatomy (W29)"). Local shapes until the generated bundle has them.
 * Units: mm, GLB axes (x, y = up, z). The GLB itself is in metres.
 */

export type PartRole =
  | "shell_top"
  | "shell_bottom"
  | "strap"
  | "button"
  | "window"
  | "lens"
  | "diffuser"
  | "frame"
  | "arm"
  | "prop"
  | "motor"
  | "pcb"
  | "component"
  | "battery"
  | "antenna"
  | "connector"
  | "cable"
  | "fastener"
  | "other";

export type EditableParam = { param: string; label: string; min: number; max: number; step: number; unit: string; value: number };

export type PartMeta = {
  part_id: string;
  name: string;
  role: PartRole | string;
  layer_id: string;
  material: string;
  finish: string;
  colour_hex: string;
  measured_bbox_mm: [number, number, number];
  centroid_mm: [number, number, number];
  label: "measured" | "estimate";
  bom_item_id?: string | null;
  lcsc_pn?: string | null;
  package?: string | null;
  unit_price?: LabeledValue | null;
  editable: EditableParam[];
  colour_editable: boolean;
  material_options: string[];
};

export type ProjectParts = { version: number; glb_url: string; parts: PartMeta[] };

export type AnatomyLayer = {
  id: string;
  name: string;
  order: number;
  parts: string[];
  explode_vector: [number, number, number];
  explode_distance_mm: number;
  caption: string;
};

export type AnatomyStep = {
  id: string;
  title: string;
  kicker: string;
  caption: string;
  camera: { position_mm: [number, number, number]; target_mm: [number, number, number]; fov_deg: number };
  layers_exploded: string[];
  focus_parts: string[];
};

export type ProjectAnatomy = {
  version: number;
  glb_url: string;
  label: string;
  kind?: "electronics" | "construction";
  bbox_mm: [number, number, number];
  layers: AnatomyLayer[];
  steps: AnatomyStep[];
  parts: PartMeta[];
  /** Client-side only: built by partsMock.ts because this API has no /anatomy route yet. */
  mock?: boolean;
};

export type PartEdit = { colour_hex?: string; material?: string; finish?: string; param?: string; value?: number };

export const ANATOMY_LABEL = "Illustrative internal layout — not a routed PCB";

/** Does this API build serve the W29 routes? (null while the OpenAPI schema loads.) */
export function usePartsRoutes(): { parts: boolean; anatomy: boolean; edit: boolean } | null {
  const paths = useApiPaths();
  if (!paths) return null;
  return {
    parts: paths.has("/projects/{project_id}/parts"),
    anatomy: paths.has("/projects/{project_id}/anatomy"),
    edit: paths.has("/projects/{project_id}/parts/{part_id}/edit"),
  };
}

type Res<T> = { key: string | null; data: T | null; error: string | null };

function useGet<T>(path: string | null): { data: T | null; error: string | null; loading: boolean } {
  const [st, setSt] = useState<Res<T>>({ key: null, data: null, error: null });
  useEffect(() => {
    if (!path) return;
    let live = true;
    withRetry(() => api.get<T>(path), isTransient, () => live)
      .then((d) => live && setSt({ key: path, data: d, error: null }))
      .catch((e) => live && setSt({ key: path, data: null, error: errorMessage(e) }));
    return () => void (live = false);
  }, [path]);
  const fresh = st.key === path;
  return { data: fresh ? st.data : null, error: fresh ? st.error : null, loading: !!path && !fresh };
}

/** GET /projects/{id}/parts?version=n when served (else null: the viewer derives parts from the GLB). */
export function usePartsApi(projectId: string | undefined, version: number | undefined, on: boolean) {
  return useGet<ProjectParts>(on && projectId ? `/projects/${projectId}/parts${version ? `?version=${version}` : ""}` : null);
}

/** GET /projects/{id}/anatomy?version=n when served and wanted (it is built on first request). */
export function useAnatomyApi(projectId: string | undefined, version: number | undefined, on: boolean) {
  return useGet<ProjectAnatomy>(on && projectId ? `/projects/${projectId}/anatomy${version ? `?version=${version}` : ""}` : null);
}

/** POST /projects/{id}/parts/{part_id}/edit → 202 {version}; the version then shows up in /versions like a refine. */
export function postPartEdit(projectId: string, partId: string, edit: PartEdit) {
  return api.post<StudioAccepted>(`/projects/${projectId}/parts/${encodeURIComponent(partId)}/edit`, edit);
}

/** Calm, plain-language wording for the edit route's error statuses. */
export function partEditErrorText(e: unknown): string {
  const s = e instanceof ApiError ? e.status : 0;
  if (s === 422) return `That value is outside what this part allows. ${e instanceof ApiError && e.message && !e.message.startsWith("HTTP") ? e.message : "Pick a value within the slider range."}`;
  if (s === 409) return "Another change is being built on this product. Wait for it to finish, then apply again.";
  if (s === 403) return "This public demo is read-only: part edits are disabled. The 3D view still works.";
  if (s === 429) return "Today's change limit for this demo is reached. Nothing was charged.";
  if (s === 404) return "This part is not in the current version any more.";
  return errorMessage(e);
}

/** The refine sentence equivalent to a part edit (used until the API serves the edit route). */
export function editAsMessage(part: PartMeta, edit: PartEdit, colourName?: string): string {
  const what = part.name.toLowerCase();
  if (edit.colour_hex) return `Make the ${what} ${colourName ? `${colourName.toLowerCase()} (${edit.colour_hex})` : edit.colour_hex}`;
  if (edit.param && edit.value !== undefined) {
    const p = part.editable.find((x) => x.param === edit.param);
    return `Set the ${(p?.label ?? edit.param).toLowerCase()} to ${fmtNum(edit.value)} ${p?.unit ?? "mm"}`;
  }
  const look = [edit.material ? materialName(edit.material) : null, edit.finish].filter(Boolean).join(", ");
  return `Make the ${what} in ${look}`;
}

export const fmtNum = (n: number) => (Math.abs(n - Math.round(n)) < 0.05 ? String(Math.round(n)) : n.toFixed(1));

/** "44 × 30 × 8 mm" (metres from 1 m up). */
export function fmtSize(mm: [number, number, number]): string {
  const big = Math.max(...mm) >= 1000;
  const f = big ? (n: number) => (n / 1000).toFixed(2) : fmtNum;
  return `${mm.map(f).join(" × ")} ${big ? "m" : "mm"}`;
}

/** Brand-safe swatches for a part colour (the product palette, not UI colours). */
export const SWATCHES: { name: string; hex: string }[] = [
  { name: "Warm white", hex: "#EDEBE6" },
  { name: "Graphite", hex: "#2B2B2D" },
  { name: "Matte black", hex: "#111111" },
  { name: "Sage", hex: "#9DB09A" },
  { name: "Midnight blue", hex: "#23324A" },
  { name: "Sand", hex: "#D8C8AE" },
  { name: "Pink", hex: "#FFC0CB" },
  { name: "Signal orange", hex: "#FF4F00" },
];

/** W29 material keys (PartMeta.material_options, PartEditRequest.material) → the names the API prints. */
export const MATERIAL_NAMES: Record<string, string> = {
  pc_abs: "PC/ABS (UL94 V-0)",
  aluminium: "Aluminium 6063-T5 (anodised)",
  stainless_steel: "Stainless steel 316L (brushed)",
  tpu: "TPU (soft-touch, Shore 85A)",
  lsr_silicone: "Liquid silicone rubber (LSR)",
  fabric: "Woven nylon webbing",
  glass: "Chemically strengthened glass",
  clear_pc: "Clear polycarbonate",
};
export const materialName = (k: string) => MATERIAL_NAMES[k] ?? k;
