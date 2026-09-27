"use client";

import { useCallback, useEffect, useState } from "react";
import type { EngineeringArtifact, LabeledValue, StudioAccepted, Version, VersionPreview } from "@/types/contracts";
import { api, ApiError, errorMessage, isTransient, withRetry } from "./api";
import { useApiPaths } from "./autofill";
import { useApi } from "./useApi";

/**
 * Studio (contracts/api.md "Studio"): every prompt = a new Version of the real product.
 * GET /projects/{id}/versions is polled every 1.5 s while a version is running, its render is pending,
 * or background stages are still updating — and for a few seconds after a POST, until the new version shows up.
 */
export function useVersions(projectId: string) {
  const [versions, setVersions] = useState<Version[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expectUntil, setExpectUntil] = useState(0); // poll after a POST even before the version is listed
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let live = true;
    withRetry(() => api.get<Version[]>(`/projects/${projectId}/versions`), isTransient, () => live)
      .then((v) => {
        if (!live) return;
        setVersions(v);
        setError(null);
      })
      .catch((e) => live && setError(errorMessage(e)));
    return () => {
      live = false;
    };
  }, [projectId, nonce]);

  const busy = !!versions?.some((v) => v.status === "running" || v.render_pending || v.background_pending);
  const [clock, setClock] = useState(0);
  const expecting = expectUntil > clock;
  useEffect(() => {
    if (!busy && !expecting) return;
    let live = true;
    let inflight = false;
    const t = setInterval(() => {
      setClock(Date.now());
      if (inflight) return;
      inflight = true;
      api
        .poll<Version[]>(`/projects/${projectId}/versions`, 5000)
        .then((v) => live && setVersions(v))
        .catch(() => undefined)
        .finally(() => (inflight = false));
    }, 1500);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, [busy, expecting, projectId]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const expect = useCallback(() => {
    const now = Date.now();
    setClock(now);
    setExpectUntil(now + 8000);
  }, []);

  return { versions, error, reload, expect, busy };
}

/**
 * m1 (W28b): recorded examples built step by step (demo_desk_lamp, demo_tracker_card) have no Studio versions — no Studio
 * for them, never "Start the Studio" (a live run). true / false, or null while an example's versions load.
 */
export function useStudioAvailable(projectId: string, example: boolean): boolean | null {
  const vs = useApi<Version[]>(example ? `/projects/${projectId}/versions` : null);
  if (!example) return true;
  if (vs.data) return vs.data.length > 0;
  return vs.error ? true : null;
}

export const isExampleProject = (id: string, tags?: string[] | null) => id.startsWith("demo_") || !!tags?.includes("Example");

export async function studioStart(projectId: string) {
  return api.post<StudioAccepted>(`/projects/${projectId}/studio/start`);
}

export async function refine(projectId: string, message: string) {
  return api.post<StudioAccepted>(`/projects/${projectId}/refine`, { message });
}

export async function restoreVersion(projectId: string, n: number) {
  return api.post<Version>(`/projects/${projectId}/versions/${n}/restore`);
}

export function studioErrorText(e: unknown): string {
  if (e instanceof ApiError && e.status === 409) return "Another job is running on this project (a version or Make it). Wait for it to finish, then try again.";
  if (e instanceof ApiError && e.status === 403) return "This public demo is read-only: prompts are disabled.";
  if (e instanceof ApiError && e.status === 429) return "Daily prompt limit reached for this demo.";
  return errorMessage(e);
}

// ------------------------------------------------------------------ contextual suggestions

const COLOURS = ["pink", "midnight blue", "sage green", "matte black"];

/** Category-specific first ideas (engineering category key); the generic ones below fill the rest. */
const CATEGORY_IDEAS: Record<string, string[]> = {
  solar_roof: ["Add a home battery", "Use all-black panels", "Add two more panels", "Budget $12,000 installed"],
  drone: ["Add obstacle avoidance", "Keep it under 250 g", "Longer flight time, 30 min"],
  surfboard: ["Make it 8'0\" for more volume", "Add a leash plug and fin boxes"],
  furniture_baby: ["Add a storage shelf", "Use solid beech", "Rounded corners everywhere"],
  vacuum: ["Add a bigger dust bin", "Add a wall dock"],
  home_robot: ["Add a bigger toy bin", "Add a docking station"],
  hair_dryer: ["Make it quieter", "Add a diffuser attachment"],
  camera: ["Add a flash", "Make it pocket-size"],
  smartphone: ["Add a headphone jack", "Bigger battery, 5,000 mAh"],
  irrigation: ["Add a soil-moisture sensor", "Add two more zones"],
};

/** Four one-click prompts derived from the current product and its category (never generic filler). */
export function suggestions(p: VersionPreview | null | undefined, context: string, category?: string | null): string[] {
  if (!p) return [];
  const out: string[] = [...(category ? (CATEGORY_IDEAS[category] ?? []) : [])];
  const text = `${context} ${p.shape_family ?? ""}`.toLowerCase();
  const wearable = category === "wearable" || (!category && /wearable|ring|whoop|band|watch|tracker|pod/.test(text));
  // Wearables: v1 usually carries a PPG sensor already, so "add heart-rate" would show no delta (QA F14).
  if (wearable) out.push(/skin[- ]temp/.test(text) ? "Make it waterproof to 10 m" : "Add skin-temperature sensing");
  else if (!category || !CATEGORY_IDEAS[category]) out.push("Add Bluetooth and an app");
  const h = p.dimensions?.height.value;
  const l = p.dimensions?.length.value;
  const handheld = !!l && l < 400;
  if (handheld && h && h > 5) out.push(`Make it thinner, ${Math.max(3, Math.round(h * 0.8))} mm`);
  else if (handheld && l) out.push(`Make it smaller, ${Math.round(l * 0.85)} mm long`);
  if (category !== "solar_roof") {
    const name = (p.color_name ?? "").toLowerCase();
    const colour = COLOURS.find((c) => !name.includes(c.split(" ").pop() as string)) ?? "pink";
    out.push(`Make it ${colour}`);
  }
  const mid = p.unit_costs.find((u) => u.quantity === 2000) ?? p.unit_costs[1] ?? p.unit_costs[0];
  if (mid && mid.value < 1000) out.push(`Target retail price $${Math.max(19, Math.round((mid.value * 4) / 10) * 10 - 1)}`);
  return Array.from(new Set(out)).slice(0, 4);
}

// ------------------------------------------------------------------ engineering layer (W20), GET /projects/{id}/engineering
// Local shape of contracts.artifacts.EngineeringArtifact (not in the generated TS bundle yet).

export type Verdict = "pass" | "warn" | "fail" | "info";
export type Engineering = EngineeringArtifact;

/** GET /projects/{id}/engineering when this API serves it (else null). `key` busts the cache when the product changed. */
export function useEngineering(projectId: string, key: string | number | null | undefined) {
  const paths = useApiPaths();
  const on = !!paths?.has("/projects/{project_id}/engineering");
  const res = useApi<Engineering>(on && key !== undefined ? `/projects/${projectId}/engineering?v=${key ?? 0}` : null);
  return { ...res, available: on, ready: paths !== null };
}

/** "factories" or "installers" (solar and other site-install products are fitted on site by installers). */
export function partnerTitle(e: Engineering | null | undefined, plural = true): string {
  const inst = e?.partner_word === "installers";
  return plural ? (inst ? "Installers" : "Factories") : inst ? "Installer" : "Factory";
}

/**
 * Site-installed products (rooftop solar) are costed per installation, not per unit: `unit_basis` (W21b) on the
 * engineering, costs or example payload; the engineering category as a fallback for older payloads.
 */
export function perInstallation(e: Engineering | null | undefined, ...withBasis: unknown[]): boolean {
  if ([e, ...withBasis].some((o) => !!o && typeof o === "object" && (o as { unit_basis?: string }).unit_basis === "per_installation")) return true;
  return e?.category === "solar_roof";
}

/**
 * Per-installation figures of the CURRENT version (N1): W21e `preview.installed_price` / `preview.installer_cost`
 * when the API sends them; else the version's own installer cost (its single unit-cost tier) and stage 5's
 * installed price (target retail) for that version; the engineering estimate only as a last resort.
 */
export function installFigures(
  preview: VersionPreview | null | undefined,
  costs?: { target_retail_price?: LabeledValue | null; tiers?: { unit_cost: LabeledValue }[] } | null,
  e?: Engineering | null,
): { installed: LabeledValue | null; installer: LabeledValue | null } {
  const pv = preview as (VersionPreview & { installed_price?: LabeledValue | null; installer_cost?: LabeledValue | null }) | null | undefined;
  const tier = pv?.unit_costs?.[0];
  const fromTier: LabeledValue | null = tier ? { value: tier.value, unit: "USD", label: tier.label, source_or_assumption: tier.source_or_assumption ?? "" } : null;
  const installer = pv?.installer_cost ?? fromTier ?? costs?.tiers?.[0]?.unit_cost ?? null;
  const installed = pv?.installed_price ?? costs?.target_retail_price ?? (installer ? null : (e?.installation_cost ?? null));
  return { installed, installer };
}
