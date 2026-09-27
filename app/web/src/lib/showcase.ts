"use client";

import { useEffect, useState } from "react";
import type { LabeledValue, Project } from "@/types/contracts";
import { api } from "./api";
import { useApiPaths } from "./autofill";

/**
 * Showcase gallery. GET /examples (W21) when the API lists it; until then the pre-computed demo projects.
 * The /examples shape is read defensively (field names normalised below) so the gallery never breaks on it.
 */
export type ShowcaseCard = {
  projectId: string;
  name: string;
  category: string | null;
  strategy: BuildKind | null;
  hero: string | null;
  line: string | null;
  studio: boolean;
  /** true for a pre-computed demo project served before /examples existed */
  demo: boolean;
  /** The key figure (W26 card line): unit cost at the first-order volume, or per installation. */
  unitCost?: LabeledValue | null;
  perInstallation?: boolean;
  versions?: number | null;
  /** W27: the hero photo's honesty label, and the lifestyle photo (shown on hover) with its label. */
  heroLabel?: string | null;
  lifestyle?: { url: string; label: string } | null;
};

export type BuildKind = "full_design" | "module_assembly" | "odm_customization";
export const BUILD_TEXT: Record<BuildKind, string> = {
  full_design: "Full design",
  module_assembly: "Module assembly",
  odm_customization: "ODM customisation",
};

export function buildKind(v: unknown): BuildKind | null {
  const k = typeof v === "string" ? v : v && typeof v === "object" ? ((v as Record<string, unknown>).kind ?? (v as Record<string, unknown>).strategy) : null;
  return k === "full_design" || k === "module_assembly" || k === "odm_customization" ? k : null;
}

const CATEGORY: Record<string, string> = {
  solar_roof: "Rooftop solar",
  furniture_baby: "Baby furniture",
  home_robot: "Home robot",
  hair_dryer: "Hair dryer",
  vacuum: "Stick vacuum",
};
/** Engineering category key → words ("furniture_baby" → "Baby furniture"). */
export function categoryText(c: string | null): string | null {
  if (!c) return null;
  return CATEGORY[c] ?? c.charAt(0).toUpperCase() + c.slice(1).replace(/_/g, " ");
}

function str(o: Record<string, unknown>, ...keys: string[]): string | null {
  for (const k of keys) if (typeof o[k] === "string" && (o[k] as string).trim()) return o[k] as string;
  return null;
}

function tidyResult(s: string | null): string | null {
  if (!s) return s;
  const parts = s.split(" · ").filter((x) => !/^(Full design|Module assembly|ODM customisation)$/i.test(x.trim()) && !/^\d+\/13 stages?/.test(x.trim()));
  return parts.join(" · ");
}

/** Solar and other site installs (unit_basis "per_installation"): "$10,146.17/unit @ 2,000" → "$10,146 per installation". */
function perInstallationLine(o: Record<string, unknown>, line: string | null): string | null {
  const uc = o.unit_cost as { value?: number; unit?: string; label?: string } | null | undefined;
  if (o.unit_basis !== "per_installation" || !line || typeof uc?.value !== "number" || /per installation/i.test(line)) return line;
  const sym = ({ USD: "$", EUR: "€", GBP: "£" } as Record<string, string>)[uc.unit ?? "USD"] ?? `${uc.unit} `;
  const cost = `${sym}${Math.round(uc.value).toLocaleString("en-US")} per installation${uc.label ? ` (${uc.label.charAt(0).toUpperCase()}${uc.label.slice(1)})` : ""}`;
  return /\$[\d,.]+\/unit @ [\d,]+( \([^)]*\))?/.test(line) ? line.replace(/\$[\d,.]+\/unit @ [\d,]+( \([^)]*\))?/, cost) : `${line} · ${cost}`;
}

function isLV(v: unknown): boolean {
  return !!v && typeof v === "object" && typeof (v as { value?: unknown }).value === "number" && typeof (v as { label?: unknown }).label === "string";
}

export function normaliseExample(raw: unknown): ShowcaseCard | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const projectId = str(o, "project_id", "id");
  if (!projectId) return null;
  const versions = typeof o.versions === "number" ? o.versions : typeof o.versions_count === "number" ? o.versions_count : null;
  return {
    projectId,
    name: str(o, "product_name", "name", "title") ?? projectId,
    category: str(o, "category_title") ?? categoryText(str(o, "category")),
    strategy: buildKind(o.build_strategy ?? o.strategy),
    hero: str(o, "hero_image_url", "hero_url", "image_url", "render_url"),
    // ExampleSummary.one_line_result repeats the strategy (already a chip) and the stage count: keep the substance.
    line: perInstallationLine(o, tidyResult(str(o, "one_line_result", "result", "one_liner", "summary", "prompt"))),
    studio: o.has_versions === true || o.studio === true || (versions ?? 0) > 0,
    demo: false,
    unitCost: isLV(o.unit_cost) ? (o.unit_cost as LabeledValue) : null,
    heroLabel: str(o, "hero_image_label"),
    lifestyle: (() => {
      const ph = Array.isArray(o.photos) ? (o.photos as Record<string, unknown>[]).find((x) => x?.shot === "lifestyle") : null;
      return ph && typeof ph.url === "string" && typeof ph.label === "string" ? { url: ph.url, label: ph.label } : null;
    })(),
    perInstallation: o.unit_basis === "per_installation",
    versions,
  };
}

export function useShowcase(limit?: number) {
  const paths = useApiPaths();
  const [cards, setCards] = useState<ShowcaseCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!paths) return;
    let live = true;
    const load = paths.has("/examples")
      ? api.get<unknown>("/examples").then((r) => {
          const list = Array.isArray(r) ? r : Array.isArray((r as { examples?: unknown[] })?.examples) ? (r as { examples: unknown[] }).examples : [];
          return list.map(normaliseExample).filter((c): c is ShowcaseCard => !!c);
        })
      : api.get<Project[]>("/projects").then((ps) =>
          ps
            .filter((p) => p.id.startsWith("demo_"))
            .map((p) => ({ projectId: p.id, name: p.name, category: null, strategy: null, hero: null, line: `“${p.prompt}”`, studio: false, demo: true })),
        );
    load.then((c) => live && setCards(limit ? c.slice(0, limit) : c)).catch((e) => live && setError(String(e?.message ?? e)));
    return () => {
      live = false;
    };
  }, [paths, limit]);
  return { cards, error, fromApi: !!paths?.has("/examples") };
}
