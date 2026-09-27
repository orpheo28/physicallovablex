"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { AutorunStatus, BriefArtifact, ProjectDetail, StageResult, StageSummary } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { api, ApiError, errorMessage, isTransient, withRetry } from "@/lib/api";

type State = { data?: ProjectDetail; error?: string; status?: number; fresh: boolean };

export type ProjectCtx = {
  id: string;
  detail?: ProjectDetail;
  error?: string;
  status?: number;
  loading: boolean;
  reload: () => void;
  /** An autofill run is in progress on the server (drives polling, the rail and the stepper). */
  running: boolean;
  autorun: (AutorunStatus & { through?: number }) | null;
  summary: (n: number) => StageSummary | undefined;
  /** Display name: the brief's product name (live, not a cached example), else the prompt, cleaned. Full text in `fullTitle`. */
  title: string;
  fullTitle: string;
};

const SMALL = new Set(["a", "an", "and", "as", "at", "for", "from", "in", "of", "on", "or", "the", "to", "with", "by", "vs"]);

/** "a whoop competitor for kitesurfers, screenless" → "A Whoop Competitor for Kitesurfers, Screenless". */
export function cleanTitle(s: string): string {
  const t = s.trim().replace(/\s+/g, " ").replace(/[.…]+$/, "");
  return t
    .split(" ")
    .map((w, i) => (i > 0 && SMALL.has(w.toLowerCase()) ? w.toLowerCase() : /^[a-z]/.test(w) ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

const Ctx = createContext<ProjectCtx | null>(null);

export function useProject(): ProjectCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useProject outside ProjectProvider");
  return c;
}

/**
 * One GET /projects/{id} for the whole project shell (rail, top progress, stage page, overview).
 * While an autorun is running on the server it polls every 2 s — one request at a time, each capped at 5 s.
 */
export function ProjectProvider({ id, children }: { id: string; children: ReactNode }) {
  const [state, setState] = useState<State>({ fresh: false });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    withRetry(() => api.get<ProjectDetail>(`/projects/${id}`), isTransient, () => !cancelled)
      .then((data) => !cancelled && setState({ data, fresh: true }))
      .catch((e) => !cancelled && setState((s) => ({ data: s.data, error: errorMessage(e), status: e instanceof ApiError ? e.status : undefined, fresh: true })));
    return () => {
      cancelled = true;
    };
  }, [id, nonce]);

  const running = state.data?.autorun?.state === "running";

  useEffect(() => {
    if (!running) return;
    let cancelled = false;
    let inflight = false;
    const tick = () => {
      if (inflight) return;
      inflight = true;
      api
        .poll<ProjectDetail>(`/projects/${id}`, 5000)
        .then((data) => !cancelled && setState({ data, fresh: true }))
        .catch(() => undefined)
        .finally(() => (inflight = false));
    };
    const t = setInterval(tick, 2000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [running, id]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const detail = state.data?.project.id === id ? state.data : undefined;
  const summary = useCallback((n: number) => detail?.stages.find((s) => s.stage === n), [detail]);
  const briefKey = detail?.stages.find((s) => s.stage === 1 && s.status !== "not_started")?.updated_at ?? null;
  const brief = useApi<StageResult>(briefKey ? `/projects/${id}/stages/1?v=${encodeURIComponent(briefKey)}` : null);
  const b = brief.data?.artifact as BriefArtifact | undefined;
  const p = detail?.project;
  // The API may cut long names mid-word (a prompt used as the name): prefer the live brief, else the full prompt.
  const truncatedName = !!p && p.prompt.length > p.name.length && p.prompt.startsWith(p.name.replace(/[.…]+$/, ""));
  const fullTitle = b && !b.fallback && b.product_name ? b.product_name : p ? (truncatedName ? p.prompt : p.name) : "";
  const title = b && !b.fallback && b.product_name ? b.product_name : cleanTitle(fullTitle);

  return (
    <Ctx.Provider
      value={{
        id,
        detail,
        error: state.error,
        status: state.status,
        loading: !detail && !state.error,
        reload,
        running,
        autorun: (detail?.autorun as ProjectCtx["autorun"]) ?? null,
        summary,
        title,
        fullTitle,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}
