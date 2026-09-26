"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError, errorMessage } from "./api";

type State<T> = { key: string | null; data?: T; error?: string; status?: number };

/** GET `path` (null = skip). `loading` is derived, so no synchronous setState in the effect. */
export function useApi<T>(path: string | null) {
  const [nonce, setNonce] = useState(0);
  const [state, setState] = useState<State<T>>({ key: null });
  const key = path === null ? null : `${path}#${nonce}`;

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;
    const k = `${path}#${nonce}`;
    api
      .get<T>(path)
      .then((data) => {
        if (!cancelled) setState({ key: k, data });
      })
      .catch((e) => {
        if (!cancelled)
          setState({ key: k, error: errorMessage(e), status: e instanceof ApiError ? e.status : undefined });
      });
    return () => {
      cancelled = true;
    };
  }, [path, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const fresh = state.key === key;
  return {
    // keep showing the previous data while reloading (no flicker)
    data: state.data,
    error: fresh ? state.error : undefined,
    status: fresh ? state.status : undefined,
    loading: path !== null && !fresh,
    reload,
  };
}

/** HEAD-check a file served by the API (GLB, STEP…). */
export function useFileExists(url: string | null) {
  const [res, setRes] = useState<{ url: string | null; ok: boolean }>({ url: null, ok: false });
  useEffect(() => {
    if (!url) return;
    let cancelled = false;
    const apiPath = url.startsWith("/backend/") ? url.slice("/backend".length) : null;
    const check = apiPath
      ? fetch(`/file-status?path=${encodeURIComponent(apiPath)}`, { cache: "no-store" })
          .then((r) => r.json())
          .then((j: { exists?: boolean }) => !!j.exists)
      : fetch(url, { cache: "no-store" }).then((r) => r.ok);
    check
      .then((ok) => {
        if (!cancelled) setRes({ url, ok });
      })
      .catch(() => {
        if (!cancelled) setRes({ url, ok: false });
      });
    return () => {
      cancelled = true;
    };
  }, [url]);
  if (!url) return { checking: false, ok: false };
  return { checking: res.url !== url, ok: res.url === url && res.ok };
}
