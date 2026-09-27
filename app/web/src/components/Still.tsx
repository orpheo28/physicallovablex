"use client";

import { fileUrl } from "@/lib/api";
import { useFileExists } from "@/lib/useApi";
import { RetryImg } from "./RetryImg";
import { Skeleton } from "./ui";

/** An image served by the API, shown only if it exists. Renders `fallback` otherwise. */
export function Still({
  url,
  alt,
  caption,
  fallback = null,
  className = "",
  height,
}: {
  url: string | null | undefined;
  alt: string;
  caption?: string;
  fallback?: React.ReactNode;
  className?: string;
  height?: number | string;
}) {
  const src = fileUrl(url);
  const { checking, ok } = useFileExists(src);
  if (checking) return <Skeleton className={`w-full ${className}`} />;
  if (!ok || !src) return <>{fallback}</>;
  return (
    <figure className={`relative overflow-hidden ${className}`} style={height ? { height } : undefined}>
      <RetryImg src={src} alt={alt} className="h-full w-full object-cover" fallback={fallback} />
      {caption && (
        <figcaption className="absolute bottom-0 left-0 p-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-sm bg-surface/90 px-1.5 py-0.5 text-[10.5px] font-medium text-ink-2">
            {caption}
          </span>
        </figcaption>
      )}
    </figure>
  );
}
