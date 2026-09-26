"use client";

import type { ReactNode } from "react";
import { useRetrySrc } from "@/lib/useRetrySrc";
import { Spinner } from "./ui";

/** <img> that retries a failed load once after 2 s, then renders `fallback`. */
export function RetryImg({ src, alt, className = "", fallback = null }: { src: string; alt: string; className?: string; fallback?: ReactNode }) {
  const r = useRetrySrc(src);
  if (r.failed) return <>{fallback}</>;
  if (!r.src)
    return (
      <span className="flex h-full w-full items-center justify-center gap-2 text-sm text-ink-3">
        <Spinner /> Retrying image
      </span>
    );
  // eslint-disable-next-line @next/next/no-img-element -- API-served file, size unknown
  return <img src={r.src} alt={alt} className={className} onError={r.onError} />;
}
