"use client";

import { useState } from "react";
import type { ResetResult } from "@/types/contracts";
import { api, errorMessage } from "@/lib/api";
import { Btn, Spinner } from "./ui";

export function ResetDemo({ onDone }: { onDone?: () => void }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  async function reset() {
    if (!window.confirm("Reset the demo? This wipes all projects and restores the cached examples.")) return;
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.post<ResetResult>("/demo/reset");
      setMsg(`Demo reset — ${r.projects.length} cached project${r.projects.length === 1 ? "" : "s"} restored`);
      onDone?.();
    } catch (e) {
      setMsg(`Reset failed: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  }
  return (
    <span className="inline-flex items-center gap-2">
      <Btn variant="ghost" onClick={reset} disabled={busy}>
        {busy && <Spinner />} Reset demo
      </Btn>
      {msg && <span className="text-sm text-ink-2" role="status">{msg}</span>}
    </span>
  );
}
