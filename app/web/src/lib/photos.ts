"use client";

import { useCallback, useEffect, useState } from "react";
import type { PhotoJob, ProductPhoto, ProjectPhotos } from "@/types/contracts";
import { api, API_BASE, ApiError, errorMessage } from "./api";

/**
 * W27 product photos (contracts/api.md "W27 — product photos", docs/PHOTOGRAPHY.md).
 * AI images styled from a reference image of our CAD; every photo carries a `label` shown under it.
 */

export type Shot = "hero_studio" | "packshot_white" | "lifestyle" | "in_hand_scale" | "detail_macro";

export const KIT_SHOTS: { shot: Shot; title: string }[] = [
  { shot: "packshot_white", title: "Packshot" },
  { shot: "lifestyle", title: "Lifestyle" },
  { shot: "in_hand_scale", title: "In hand" },
  { shot: "detail_macro", title: "Detail" },
];

export const photoOf = (list: ProductPhoto[] | null | undefined, shot: Shot) => list?.find((p) => p.shot === shot) ?? null;

/** Calm, plain-language wording for the photo routes' error statuses. */
export function photoErrorText(e: unknown): string {
  const s = e instanceof ApiError ? e.status : 0;
  if (s === 403) return "Photos are turned off in this read-only demo. The 3D model and the CAD render stay available.";
  if (s === 409) return "A photo is already being made for this project. It will appear here in a few seconds.";
  if (s === 429) return "Today's photo limit for this network is reached. Try again tomorrow; nothing was charged.";
  if (s === 503) return "No image model is configured here, so new photos can't be made. Existing photos and the 3D model stay available.";
  if (s === 413 || s === 415 || s === 422) return "The viewer capture could not be used. Try again; the CAD render is used as the reference instead.";
  if (s === 404) return "This version is no longer available.";
  return errorMessage(e);
}

/** GET /projects/{id}/photos, polled every 2 s while a photo job runs. `configured` = an image model is available. */
export function useProjectPhotos(projectId: string, enabled = true) {
  const [data, setData] = useState<ProjectPhotos | null>(null);
  const [nonce, setNonce] = useState(0);
  const running = data?.job.state === "running";
  useEffect(() => {
    if (!enabled) return;
    let live = true;
    const load = () =>
      api
        .poll<ProjectPhotos>(`/projects/${projectId}/photos`, 5000)
        .then((d) => live && setData(d))
        .catch(() => undefined);
    load();
    if (!running) return () => void (live = false);
    const t = setInterval(load, 2000);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, [projectId, enabled, running, nonce]);
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, running, reload, job: data?.job as PhotoJob | undefined, configured: !!data?.configured };
}

const MAX_BYTES = 2 * 1024 * 1024;

/**
 * Capture the product from a <model-viewer>: ¾ view (the viewer's default orbit), transparent background
 * (flattened onto paper server-side), long edge ~1200 px, PNG — JPEG 0.9 when the PNG is over 2 MB.
 */
export async function captureViewer(el: Element | null): Promise<Blob | null> {
  type MV = HTMLElement & {
    toBlob?: (o: { mimeType?: string; qualityArgument?: number }) => Promise<Blob>;
    cameraOrbit?: string;
    jumpCameraToGoal?: () => void;
    autoRotate?: boolean;
    loaded?: boolean;
  };
  const mv = el as MV | null;
  if (!mv?.toBlob || !mv.loaded) return null;
  const orbit = mv.cameraOrbit;
  const spin = mv.autoRotate;
  try {
    mv.autoRotate = false;
    mv.cameraOrbit = "-28deg 72deg auto";
    mv.jumpCameraToGoal?.();
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const raw = await mv.toBlob({ mimeType: "image/png" });
    const bmp = await createImageBitmap(raw);
    const k = Math.min(1, 1200 / Math.max(bmp.width, bmp.height));
    const c = document.createElement("canvas");
    c.width = Math.round(bmp.width * k);
    c.height = Math.round(bmp.height * k);
    c.getContext("2d")?.drawImage(bmp, 0, 0, c.width, c.height);
    const png = await new Promise<Blob | null>((r) => c.toBlob(r, "image/png"));
    if (png && png.size <= MAX_BYTES) return png;
    return await new Promise<Blob | null>((r) => c.toBlob(r, "image/jpeg", 0.9));
  } catch {
    return null;
  } finally {
    mv.cameraOrbit = orbit;
    mv.autoRotate = spin;
  }
}

async function postImage(path: string, image: Blob | null): Promise<void> {
  let res: Response;
  try {
    const body = new FormData();
    if (image) body.append("image", image, image.type === "image/jpeg" ? "viewer.jpg" : "viewer.png");
    res = await fetch(`${API_BASE}${path}`, { method: "POST", body, cache: "no-store" });
  } catch {
    throw new ApiError(0, "API unreachable. Is the API running?");
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      if (typeof j?.detail === "string") detail = j.detail;
    } catch {
      /* non-JSON body */
    }
    throw new ApiError(res.status, detail);
  }
}

/** POST one hero_studio photo of version n (202), with the viewer capture as the reference when we have one. */
export const postHeroPhoto = (projectId: string, n: number, image: Blob | null) => postImage(`/projects/${projectId}/versions/${n}/photo?shot=hero_studio`, image);

/** POST one shot of version n (202) — used for a single missing listing shot. */
export const postShot = (projectId: string, n: number, shot: Shot, image: Blob | null = null) => postImage(`/projects/${projectId}/versions/${n}/photo?shot=${shot}`, image);

/** POST the listing kit (packshot, lifestyle, in hand, + detail unless `detail` is false) of a version (default current) — 202, then poll. */
export const postListingKit = (projectId: string, version?: number, image?: Blob | null, detail = true) => {
  const q = new URLSearchParams();
  if (version) q.set("version", String(version));
  if (!detail) q.set("detail", "false");
  const qs = q.toString();
  return postImage(`/projects/${projectId}/photos/kit${qs ? `?${qs}` : ""}`, image ?? null);
};
