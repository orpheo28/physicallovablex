"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";
import { Btn, Spinner } from "./ui";

export function ExportButton({ projectId, variant = "primary", label = "Export Launch Dossier" }: { projectId: string; variant?: "primary" | "secondary" | "ink" | "ghost"; label?: string }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  async function download() {
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/export`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `launch-dossier-${projectId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <span className="inline-flex items-center gap-2">
      <Btn variant={variant} onClick={download} disabled={busy}>
        {busy ? (
          <Spinner />
        ) : (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
            <path d="M8 2v8.5M4.5 7 8 10.5 11.5 7M3 13.5h10" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
        {busy ? "Preparing PDF…" : label}
      </Btn>
      {err && <span className="text-sm text-danger">Export failed: {err}</span>}
    </span>
  );
}
