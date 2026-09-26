"use client";

import { useCallback, useState } from "react";

type Phase = "first" | "waiting" | "retry" | "failed";

/**
 * A media URL that retries once: on the first load error it waits `delayMs` (a file being rewritten
 * on the server has time to settle), then reloads with a cache-busting query; on a second error it
 * reports `failed` so the caller shows its fallback instead of hanging.
 */
export function useRetrySrc(src: string | null, delayMs = 2000) {
  const [st, setSt] = useState<{ key: string | null; phase: Phase }>({ key: src, phase: "first" });
  const phase: Phase = st.key === src ? st.phase : "first";

  const onError = useCallback(() => {
    if (phase === "first") {
      setSt({ key: src, phase: "waiting" });
      setTimeout(() => setSt((s) => (s.key === src && s.phase === "waiting" ? { key: src, phase: "retry" } : s)), delayMs);
    } else if (phase === "retry") {
      setSt({ key: src, phase: "failed" });
    }
  }, [phase, src, delayMs]);

  const url =
    !src || phase === "waiting" || phase === "failed" ? null : phase === "retry" ? `${src}${src.includes("?") ? "&" : "?"}retry=1` : src;
  return { src: url, failed: phase === "failed", retrying: phase === "waiting", onError };
}
