"use client";

import "@google/model-viewer";
import { useEffect, useRef, useState } from "react";
import { useRetrySrc } from "@/lib/useRetrySrc";
import { Spinner } from "./ui";

const LOAD_TIMEOUT_MS = 20_000; // a GLB that neither loads nor errors counts as failed

/** Studio presentation: neutral environment light, soft contact shadow, slow turntable. Retries a failed GLB once. */
export default function ModelViewerInner({ src, alt, interactive = true }: { src: string; alt: string; interactive?: boolean }) {
  const ref = useRef<HTMLElement | null>(null);
  const r = useRetrySrc(src);
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const url = r.src;
  const loaded = !!url && loadedSrc === url;
  const { onError } = r;

  useEffect(() => {
    const el = ref.current;
    if (!el || !url) return;
    const onErr = () => onError();
    const onLoad = () => setLoadedSrc(url);
    el.addEventListener("error", onErr);
    el.addEventListener("load", onLoad);
    const t = setTimeout(() => {
      if ((el as HTMLElement & { loaded?: boolean }).loaded !== true) onError();
    }, LOAD_TIMEOUT_MS);
    return () => {
      clearTimeout(t);
      el.removeEventListener("error", onErr);
      el.removeEventListener("load", onLoad);
    };
  }, [url, onError]);

  if (r.failed)
    return <div className="flex h-full items-center justify-center text-sm text-ink-3">3D unavailable — the model could not be loaded</div>;
  if (!url)
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
        <Spinner /> Retrying 3D model
      </div>
    );
  return (
    <model-viewer
      ref={ref}
      src={url}
      alt={alt}
      camera-controls={interactive ? "" : undefined}
      disable-zoom=""
      auto-rotate=""
      auto-rotate-delay="0"
      rotation-per-second="12deg"
      interaction-prompt="none"
      environment-image="neutral"
      tone-mapping="neutral"
      exposure="1.05"
      shadow-intensity="1"
      shadow-softness="0.75"
      camera-orbit="-28deg 72deg auto"
      field-of-view="26deg"
      interpolation-decay="120"
      style={{
        width: "100%",
        height: "100%",
        background: "transparent",
        opacity: loaded ? 1 : 0,
        transition: "opacity 400ms cubic-bezier(0.2,0.7,0.2,1)",
        outline: "none",
      }}
    />
  );
}
