"use client";

import { useState } from "react";
import type { ProductPhoto } from "@/types/contracts";
import { fileUrl } from "@/lib/api";
import { KIT_SHOTS, photoErrorText, photoOf, postListingKit, postShot, useProjectPhotos } from "@/lib/photos";
import { RetryImg } from "./RetryImg";
import { Btn, Spinner } from "./ui";

/** One kit photo: the image, its title, the honesty label (always visible) and a download link. */
function KitPhoto({ title, photo, pending }: { title: string; photo: ProductPhoto | null; pending: boolean }) {
  const url = fileUrl(photo?.url);
  const name = photo?.url.split("/").pop() ?? "";
  return (
    <figure className="flex min-w-0 flex-col gap-2">
      <div className={`img-outline relative overflow-hidden rounded-md bg-paper-2 ${photo?.aspect_ratio === "1:1" ? "aspect-square" : "aspect-[4/5]"}`}>
        {url ? (
          <RetryImg key={url} src={url} alt={`${title}: ${photo?.label}`} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center gap-2 text-sm text-ink-3">
            {pending ? (
              <>
                <Spinner /> Taking the photo…
              </>
            ) : (
              "Not generated yet"
            )}
          </div>
        )}
        {url && pending && (
          <span className="absolute left-2 top-2 flex items-center gap-1.5 rounded-full bg-surface/90 px-2 py-0.5 text-2xs text-ink-2">
            <Spinner className="!h-2.5 !w-2.5" /> Updating
          </span>
        )}
      </div>
      <figcaption className="flex flex-col gap-0.5">
        <span className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-medium text-ink">{title}</span>
          {url && (
            <a href={url} download={name} className="text-sm text-ink-2 underline decoration-line-2 underline-offset-4 transition-colors hover:text-ink hover:decoration-ink">
              Download
            </a>
          )}
        </span>
        {photo && <span className={`text-2xs leading-4 ${photo.staged ? "text-estimate-ink" : "text-ink-3"}`}>{photo.label}</span>}
      </figcaption>
    </figure>
  );
}

/**
 * Listing photos (W27 kit): packshot · lifestyle · in hand · detail, AI images styled from our CAD.
 * `fallback` = photos already attached to stage 13 (BrandArtifact.listing_photos) when the live list has none.
 */
export function ListingKit({ projectId, fallback = [], compact }: { projectId: string; fallback?: ProductPhoto[]; compact?: boolean }) {
  const { data, running, job, configured, reload } = useProjectPhotos(projectId);
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const pending = (shot: string) => running && !!job?.shots.includes(shot) && !job.done.includes(shot);
  // N5: only generated (or in-progress) shots are shown; one action makes the missing ones.
  const shots = KIT_SHOTS.map((k) => ({ ...k, photo: photoOf(data?.photos, k.shot) ?? photoOf(fallback, k.shot) }));
  const shown = shots.filter((k) => k.photo || pending(k.shot));
  const missing = shots.filter((k) => !k.photo);
  // One missing shot → just that shot; several → the kit (it also refreshes the shots that exist).
  const refreshesOthers = missing.length > 1 && missing.length < KIT_SHOTS.length;

  async function generate() {
    setSending(true);
    setErr(null);
    try {
      if (missing.length === 1 && data?.version) await postShot(projectId, data.version, missing[0].shot);
      else await postListingKit(projectId, undefined, null, missing.some((m) => m.shot === "detail_macro") || missing.length === 0);
      reload();
    } catch (e) {
      setErr(photoErrorText(e));
    } finally {
      setSending(false);
    }
  }

  const failed = job?.state === "failed" || (job?.failed.length ?? 0) > 0;
  return (
    <section aria-labelledby="kit-h" className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 id="kit-h" className="text-md font-semibold tracking-[-0.01em] text-ink">
            Listing photos
          </h3>
          <p className="text-sm text-ink-3">AI images styled from our CAD, for a marketplace listing. Staged scenes are illustrative.</p>
        </div>
        <span className="flex items-center gap-3">
          {running && (
            <span className="flex items-center gap-1.5 text-sm text-ink-2" role="status" aria-live="polite">
              <Spinner className="text-accent" /> Making {job?.shots.length ?? 4} photos, about 15 s
            </span>
          )}
          <Btn
            variant={compact ? "primary" : "secondary"}
            onClick={generate}
            disabled={!configured || sending || running}
            title={refreshesOthers ? "Makes the listing kit: the missing shots, and fresh versions of the ones you have" : undefined}
          >
            {sending && <Spinner />}
            {missing.length === 0 ? "Regenerate listing photos" : missing.length === KIT_SHOTS.length ? "Generate listing photos" : `Generate the missing ${missing.length} ${missing.length === 1 ? "photo" : "photos"}`}
          </Btn>
        </span>
      </header>
      {data && !configured && (
        <p className="rounded-sm bg-paper px-3 py-2 text-sm text-ink-2" role="status">
          No image model is configured here, so new photos can&rsquo;t be made. The photos below were recorded with the example.
        </p>
      )}
      {err && (
        <p className="rounded-sm bg-estimate-soft px-3 py-2 text-sm text-estimate-ink" role="status">
          {err}
        </p>
      )}
      {failed && job?.error && !running && (
        <p className="rounded-sm bg-estimate-soft px-3 py-2 text-sm text-estimate-ink" role="status">
          {job.error}
        </p>
      )}
      {shown.length > 0 ? (
        <div className={`grid gap-4 ${compact ? "grid-cols-4" : "grid-cols-2 xl:grid-cols-4"}`}>
          {shown.map((k) => (
            <KitPhoto key={k.shot} title={k.title} photo={k.photo} pending={pending(k.shot)} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-ink-3">No listing photos yet: packshot, lifestyle, in hand and detail are made together in about 15 s.</p>
      )}
      {shown.length > 0 && missing.length > 0 && !running && (
        <p className="text-2xs text-ink-3">Not made yet: {missing.map((m) => m.title.toLowerCase()).join(", ")}.</p>
      )}
    </section>
  );
}
