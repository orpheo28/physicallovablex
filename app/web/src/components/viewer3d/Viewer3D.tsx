"use client";

import dynamic from "next/dynamic";
import { useState, useSyncExternalStore } from "react";
import type { VersionPreview } from "@/types/contracts";
import { fileUrl } from "@/lib/api";
import { useFileExists } from "@/lib/useApi";
import { ModelViewer } from "../ModelViewer";
import { Spinner } from "../ui";
import type { EditHandler } from "./Stage";

const Stage = dynamic(() => import("./Stage"), {
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

let probe: { key: string; basic: boolean } | null = null;

/** The basic viewer (model-viewer) is used with `?viewer=basic` or when the browser has no WebGL2. */
function basicMode(): boolean {
  const key = window.location.search;
  if (probe?.key === key) return probe.basic;
  const forced = new URLSearchParams(key).get("viewer") === "basic";
  let gl2 = false;
  if (!forced) {
    try {
      const c = document.createElement("canvas");
      const gl = c.getContext("webgl2");
      gl2 = !!gl;
      gl?.getExtension("WEBGL_lose_context")?.loseContext();
    } catch {
      gl2 = false;
    }
  }
  probe = { key, basic: forced || !gl2 };
  return probe.basic;
}
const noop = () => () => undefined;

/**
 * The product in 3D. Photoreal react-three-fiber stage (parts, exploded, X-ray, anatomy); falls back to the
 * model-viewer turntable automatically: no WebGL2, WebGL context lost, a load/render error, or `?viewer=basic`.
 */
export function Viewer3D({
  url,
  alt,
  height = "100%",
  projectId,
  version,
  preview,
  surface,
  onEdit,
  editNote,
  editViaRoute,
  editLink,
}: {
  editLink?: { href: string; label: string };
  url: string | null | undefined;
  alt: string;
  height?: number | string;
  projectId?: string;
  version?: number;
  preview?: VersionPreview | null;
  surface: "studio" | "overview";
  onEdit?: EditHandler;
  editNote?: string | null;
  editViaRoute?: boolean;
}) {
  const src = fileUrl(url);
  const { checking, ok } = useFileExists(src);
  const basic = useSyncExternalStore(noop, basicMode, () => null);
  const [failed, setFailed] = useState<string | null>(null);

  if (basic === null) return <div style={{ height }} />;
  if (basic || failed)
    return (
      <div style={{ height }} className="relative w-full" data-viewer-fallback={failed ? "error" : "basic"} title={failed ? `Basic 3D viewer (${failed})` : undefined}>
        <ModelViewer url={url} alt={alt} height="100%" />
      </div>
    );
  return (
    <div style={{ height }} className="relative w-full">
      {checking ? (
        <Waiting text="Checking 3D model" />
      ) : ok && src ? (
        <Stage
          url={src}
          alt={alt}
          projectId={projectId}
          version={version}
          preview={preview}
          surface={surface}
          onEdit={onEdit}
          editNote={editNote}
          editViaRoute={editViaRoute}
          editLink={editLink}
          onFail={(why) => {
            console.warn("3D stage fell back to the basic viewer:", why);
            setFailed(why);
          }}
        />
      ) : (
        <ModelViewer url={url} alt={alt} height="100%" />
      )}
    </div>
  );
}
