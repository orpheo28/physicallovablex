"use client";

import { useEffect, useState } from "react";
import type { AutorunResult } from "@/types/contracts";
import { api } from "./api";

/**
 * Autofill = POST /projects/{id}/autorun?through=13 (stages 1-13, stage 8 auto-approved).
 * The API advertises `through` in its OpenAPI schema; an API without it runs stages 1-7 only,
 * so the UI falls back to "Autofill steps 1–7" and labels its buttons accordingly.
 */
export type Through = 7 | 13;

type OpenApi = { paths?: Record<string, { post?: { parameters?: { name?: string }[] } }> };
let schema: Promise<OpenApi | null> | null = null;

/** The API's own OpenAPI schema, fetched once: which routes and parameters this build has. */
export function apiSchema(): Promise<OpenApi | null> {
  if (!schema)
    schema = fetch("/backend/openapi.json", { cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<OpenApi>) : null))
      .catch(() => null);
  return schema;
}

function detect(): Promise<Through> {
  return apiSchema().then((j) => {
    const params = j?.paths?.["/projects/{project_id}/autorun"]?.post?.parameters ?? [];
    return (params.some((p) => p.name === "through") ? 13 : 7) as Through;
  });
}

/** API paths this build serves (null while loading). */
export function useApiPaths(): Set<string> | null {
  const [paths, setPaths] = useState<Set<string> | null>(null);
  useEffect(() => {
    let live = true;
    apiSchema().then((j) => live && setPaths(new Set(Object.keys(j?.paths ?? {}))));
    return () => {
      live = false;
    };
  }, []);
  return paths;
}

/** The furthest stage autofill can reach on this API: 13 when supported, else 7. */
export function useAutofillMax(): Through {
  // Assume 13 (every current API) until the schema says otherwise: the label must not flip on load (QA F24).
  const [max, setMax] = useState<Through>(13);
  useEffect(() => {
    let live = true;
    detect().then((t) => live && setMax(t));
    return () => {
      live = false;
    };
  }, []);
  return max;
}

export async function startAutorun(projectId: string, through: Through): Promise<AutorunResult> {
  return api.post<AutorunResult>(`/projects/${projectId}/autorun${through === 13 ? "?through=13" : ""}`);
}

export function autofillLabel(through: Through): string {
  return through === 13 ? "Autofill all 13 steps with AI" : "Autofill steps 1–7 with AI";
}
