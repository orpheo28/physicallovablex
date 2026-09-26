"use client";

import dynamic from "next/dynamic";
import { fileUrl } from "@/lib/api";
import { useFileExists } from "@/lib/useApi";
import { Spinner } from "./ui";

const Inner = dynamic(() => import("./ModelViewerInner"), {
  ssr: false,
  loading: () => <Waiting text="Loading 3D viewer" />,
});

function Waiting({ text }: { text: string }) {
  return (
    <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
      <Spinner /> {text}
    </div>
  );
}

/**
 * <model-viewer> for a GLB served by the API, on a seamless studio backdrop (no box).
 * `tone`: "page" blends into the paper background; "surface" sits on a white card.
 */
export function ModelViewer({
  url,
  alt,
  height = 360,
  tone = "page",
  interactive = true,
}: {
  url: string | null | undefined;
  alt: string;
  height?: number;
  tone?: "page" | "surface" | "studio";
  interactive?: boolean;
}) {
  const src = fileUrl(url);
  const { checking, ok } = useFileExists(src);
  const bg = tone === "surface" ? "bg-surface" : tone === "studio" ? "bg-paper-2/60" : "bg-transparent";
  return (
    <div style={{ height }} className={`relative w-full overflow-hidden rounded-md ${bg}`}>
      {checking ? (
        <Waiting text="Checking 3D model" />
      ) : ok && src ? (
        <Inner src={src} alt={alt} interactive={interactive} />
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-ink-3">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" aria-hidden>
            <path d="M12 2.5 3.5 7.2v9.6L12 21.5l8.5-4.7V7.2L12 2.5Z" />
            <path d="m3.5 7.2 8.5 4.7 8.5-4.7M12 11.9v9.6" />
          </svg>
          <span className="font-medium text-ink-2">3D pending</span>
          <span>The GLB model is not generated yet{src ? "" : " (no file listed)"}.</span>
        </div>
      )}
    </div>
  );
}
