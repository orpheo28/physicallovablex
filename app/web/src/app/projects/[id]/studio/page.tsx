"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useProject } from "@/components/project/ProjectContext";
import { Conversation } from "@/components/studio/Conversation";
import { Strip, useViewMode, Viewer, ViewToggle } from "@/components/studio/ProductPane";
import { CadCodeTab, EngineeringTab, FirmwareTab, type TabId } from "@/components/studio/Tabs";
import { Arrow, Btn, BtnLink, CachedBanner, CouldntLoad, ErrorBox, Skeleton, Spinner } from "@/components/ui";
import { MoreMenu } from "@/components/MoreMenu";
import { ListingKit } from "@/components/ListingKit";
import { captureViewer, photoErrorText, photoOf, postHeroPhoto, useProjectPhotos } from "@/lib/photos";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useApi } from "@/lib/useApi";
import type { BriefArtifact, CostsArtifact, StageResult } from "@/types/contracts";
import { startAutorun, useApiPaths } from "@/lib/autofill";
import { refine, restoreVersion, studioErrorText, studioStart, suggestions, useEngineering, useVersions, perInstallation } from "@/lib/studio";

const TABS: { id: TabId; label: string; route: string | null }[] = [
  { id: "product", label: "Product", route: null },
  { id: "engineering", label: "Engineering", route: "/projects/{project_id}/engineering" },
  { id: "code", label: "CAD code", route: "/projects/{project_id}/cad/code/{n}" },
  { id: "firmware", label: "Firmware", route: "/projects/{project_id}/engineering" },
];

/**
 * Studio: the product is designed by conversation. Left, the prompts and the versions they produced;
 * right, the live product of the current (or previewed) version, its facts, and the engineering layer.
 */
export default function StudioPage() {
  const { id, detail, summary, reload: reloadProject, running: autorunning, title, fullTitle } = useProject();
  const router = useRouter();
  const paths = useApiPaths();
  const { versions, error, reload, expect } = useVersions(id);
  const [selected, setSelected] = useState<number | null>(null);
  const [tab, setTab] = useState<TabId>("product");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [making, setMaking] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [ask, setAsk] = useState<null | { kind: "restore"; n: number } | { kind: "make" }>(null);

  const current = versions?.find((v) => v.is_current);
  const working = versions?.find((v) => v.status === "running") ?? null;
  const shown = (selected !== null ? versions?.find((v) => v.n === selected && v.status === "done") : undefined) ?? current ?? versions?.filter((v) => v.status === "done").at(-1);
  const previewing = !!shown && !!current && shown.n !== current.n;
  const prompt = detail?.project.prompt ?? "";
  const made = (summary(13)?.status ?? "not_started") !== "not_started";
  // Engineering of the current product (build path, partner word, tabs): refetched when the current version changes.
  const eng = useEngineering(id, current ? `${current.n}-${current.background_pending ? 1 : 0}` : undefined);
  // Showcases are recorded projects: opening them is instant; "Make it" there starts a live, paid run.
  const showcase = !!detail && (detail.project.tags?.includes("Example") || id.startsWith("demo_"));
  // F6: the brief (and so v1) came from a pre-computed example (no key, 402, timeout): say so in the Studio too.
  const cached = !!detail && (!!summary(1)?.fallback || !!detail.fallback_stages?.includes(1));
  const brief = useApi<StageResult>(cached ? `/projects/${id}/stages/1` : null);
  // Margin and break-even of the current product (stage 5 follows the current version) when a target price was set.
  const priceSet = !!versions?.some((v) => v.status === "done" && current && v.n <= current.n && v.changes.some((c) => c.area === "price"));
  const perInstNow = perInstallation(eng.data, current?.preview);
  const s5 = useApi<StageResult>((priceSet || perInstNow) && current ? `/projects/${id}/stages/5?v=${current.n}` : null);
  const costs = s5.data?.artifact as CostsArtifact | undefined;

  // The current version changed (new version, restore): stages 8-13 were cleared server-side — refresh the rail and Make it.
  const currentKey = `${current?.n}-${versions?.filter((v) => v.status === "done").length}`;
  const lastKey = useRef(currentKey);
  useEffect(() => {
    if (lastKey.current === currentKey) return;
    lastKey.current = currentKey;
    reloadProject();
  }, [currentKey, reloadProject]);

  const context = useMemo(
    () => [prompt, ...(versions ?? []).flatMap((v) => [v.message, ...v.changes.map((c) => `${c.label} ${c.after ?? ""}`)])].join(" "),
    [prompt, versions],
  );
  const chips = suggestions(current?.preview, context, eng.data?.category);

  async function onSend(message: string) {
    setSending(true);
    setSendError(null);
    try {
      await refine(id, message);
      expect();
      reload();
      setSelected(null);
      return true;
    } catch (e) {
      setSendError(studioErrorText(e));
      return false;
    } finally {
      setSending(false);
    }
  }

  async function onStart() {
    setActionError(null);
    try {
      await studioStart(id);
      expect();
      reload();
    } catch (e) {
      setActionError(studioErrorText(e));
    }
  }

  async function onRestore(n: number) {
    setAsk(null);
    setActionError(null);
    try {
      await restoreVersion(id, n);
      setSelected(null);
      reload();
      reloadProject();
    } catch (e) {
      setActionError(studioErrorText(e));
    }
  }

  async function makeIt() {
    setMaking(true);
    setActionError(null);
    try {
      await startAutorun(id, 13);
      reloadProject();
      router.push(`/projects/${id}?autorun=13`);
    } catch (e) {
      setActionError(studioErrorText(e));
      setMaking(false);
    }
  }

  const available = (t: (typeof TABS)[number]) => !t.route || !!paths?.has(t.route);
  const photos = useProjectPhotos(id, !!paths?.has("/projects/{project_id}/photos"));
  const vm = useViewMode(shown, photos.data?.photos);
  const [kitOpen, setKitOpen] = useState(false);
  const [photoNote, setPhotoNote] = useState<string | null>(null);

  // W27: after a version finishes in this session, photograph it — the viewer capture (¾ view) is the reference.
  // Only with an image model configured, never on recorded showcases, once per version, skipped if it has a photo.
  // "Just finished" = done within the last 2 minutes (covers a version that completes before the first poll).
  const attempted = useRef<Set<number>>(new Set());
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => void (mounted.current = false);
  }, []);
  useEffect(() => {
    if (!versions || showcase || !photos.configured) return;
    const fresh = versions.find(
      (v) =>
        v.status === "done" &&
        v.is_current &&
        !attempted.current.has(v.n) &&
        !!v.finished_at &&
        Date.now() - new Date(v.finished_at).getTime() < 120_000 &&
        !photoOf(v.preview?.photos, "hero_studio"),
    );
    if (!fresh) return;
    attempted.current.add(fresh.n);
    // Not cancelled by the next versions poll (that re-runs this effect); only by leaving the page.
    (async () => {
      // Give the viewer time to load the new GLB (up to ~12 s), then capture it.
      let blob: Blob | null = null;
      for (let i = 0; i < 24 && mounted.current && !blob; i++) {
        await new Promise((r) => setTimeout(r, 500));
        blob = await captureViewer(document.querySelector("[data-studio-viewer] model-viewer"));
      }
      if (!mounted.current) return;
      try {
        await postHeroPhoto(id, fresh.n, blob);
        setPhotoNote(null);
        photos.reload();
      } catch (e) {
        setPhotoNote(photoErrorText(e));
      }
    })();
  }, [versions, showcase, photos.configured, id]); // eslint-disable-line react-hooks/exhaustive-deps
  const photoRunning = photos.running && photos.job?.version === shown?.n && photos.job?.shots.includes("hero_studio");
  const makeDisabled = making || !current || !!working || autorunning;
  // One primary action (W26): "Open overview" once made (showcases, W15g), else "Make it". The rest lives in ⋯.
  const menu = [
    { label: "Listing photos", hint: "Packshot, lifestyle, in hand, detail", onClick: () => setKitOpen(true) },
    { label: "Open all 13 steps", href: `/projects/${id}?stage=1` },
    { label: "Factory Pack", href: `/projects/${id}/factory-pack` },
    ...(made
      ? [
          {
            label: "Make it again",
            hint: showcase ? "Starts a live AI run (~1 min, ~$0.30)" : `Made for v${current?.n ?? ""}`,
            onClick: () => (showcase ? setAsk({ kind: "make" }) : makeIt()),
            disabled: makeDisabled,
          },
        ]
      : []),
  ];

  return (
    <div className="grid h-full min-h-0 grid-cols-[minmax(380px,430px)_minmax(0,1fr)] min-[1440px]:grid-cols-[minmax(380px,460px)_minmax(0,1fr)]">
      {ask?.kind === "restore" && (
        <ConfirmDialog
          title={`Restore v${ask.n}?`}
          body={
            made ? (
              <>v{ask.n} becomes the current product. Quotes, samples, QC, shipping, cash plan and brand were made for another version: run “Make it” again afterwards.</>
            ) : (
              <>v{ask.n} becomes the current product. Later versions stay in the list, so you can come back.</>
            )
          }
          confirm={`Restore v${ask.n}`}
          onConfirm={() => onRestore(ask.n)}
          onCancel={() => setAsk(null)}
        />
      )}
      {kitOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-6" onMouseDown={(e) => e.target === e.currentTarget && setKitOpen(false)} onKeyDown={(e) => e.key === "Escape" && setKitOpen(false)}>
          <div role="dialog" aria-modal="true" aria-label="Listing photos" className="relative max-h-full w-full max-w-[1040px] overflow-y-auto overscroll-contain rounded-lg bg-surface px-6 pb-6 pt-12 shadow-float">
            <button
              onClick={() => setKitOpen(false)}
              aria-label="Close"
              autoFocus
              className="press absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded text-ink-2 hover:bg-paper-2 hover:text-ink"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden>
                <path d="m4 4 8 8M12 4l-8 8" />
              </svg>
            </button>
            <ListingKit projectId={id} compact />
          </div>
        </div>
      )}
      {ask?.kind === "make" && (
        <ConfirmDialog
          title="Start a live AI run?"
          body="This is a recorded example: its overview is ready now. Make it starts a live AI run (~1 min, ~$0.30). Continue?"
          confirm="Start live run"
          tone="primary"
          onConfirm={() => {
            setAsk(null);
            makeIt();
          }}
          onCancel={() => setAsk(null)}
        />
      )}
      {/* ---- conversation */}
      <div className="flex min-h-0 flex-col gap-2 pt-3">
        {(cached || actionError || (error && !versions)) && (
          <div className="flex flex-col gap-2 pl-6 pr-5">
            {cached && <CachedBanner reason={(brief.data?.artifact as BriefArtifact | undefined)?.fallback_reason} example={detail?.project.example} />}
            {actionError && <ErrorBox message={actionError} onRetry={() => setActionError(null)} />}
            {error && !versions && <CouldntLoad what="the versions" onRetry={reload} />}
          </div>
        )}
        {!versions && !error && <Skeleton className="mx-6 h-full" />}
        {versions && versions.length === 0 && (
          <div className="flex h-full flex-col items-start justify-center gap-3 px-6">
            <p className="text-md font-medium">Design this product by conversation</p>
            <p className="text-base text-ink-2">The first version builds the CAD, BOM, costs and a factory shortlist from your prompt. Then ask for any change.</p>
            <Btn variant="primary" onClick={onStart} disabled={autorunning}>
              Start the Studio
            </Btn>
            {autorunning && <p className="text-sm text-ink-3">An autofill run is in progress on this project. The Studio opens when it ends.</p>}
          </div>
        )}
        {versions && versions.length > 0 && (
          <div className="min-h-0 flex-1">
            <Conversation
              versions={versions}
              prompt={prompt}
              selected={previewing ? (shown?.n ?? null) : null}
              busy={!!working || autorunning}
              onSelect={setSelected}
              onRestore={(n) => setAsk({ kind: "restore", n })}
              cached={cached}
              onSend={onSend}
              sending={sending}
              sendError={sendError}
              suggestions={chips}
            />
          </div>
        )}
      </div>

      {/* ---- live product */}
      <div className="flex min-h-0 min-w-0 flex-col gap-3 pb-4 pl-4 pr-6">
        <header className="flex min-h-[52px] items-center gap-4">
          <h1 className="title min-w-0 truncate text-lg" title={fullTitle}>
            {detail ? title : ""}
          </h1>
          {versions && versions.length > 0 && (
            <nav aria-label="Versions" className="flex min-w-0 items-center gap-0.5 overflow-x-auto rounded bg-paper-2 p-0.5">
              {versions.map((v) => (
                <button
                  key={v.n}
                  onClick={() => v.status === "done" && setSelected(v.is_current ? null : selected === v.n ? null : v.n)}
                  disabled={v.status !== "done"}
                  aria-current={shown?.n === v.n ? "true" : undefined}
                  title={v.status === "done" ? `${v.summary}${v.is_current ? " (current)" : ""}` : v.status === "running" ? "Working…" : (v.error ?? "Failed")}
                  className={`relative flex h-6 shrink-0 items-center gap-1 rounded-sm px-2 font-mono text-[11.5px] transition-[color,background-color,box-shadow] duration-150 ${
                    shown?.n === v.n
                      ? "bg-surface text-ink shadow-[0_1px_2px_rgb(17_17_17/0.08),0_0_0_1px_rgb(17_17_17/0.04)]"
                      : v.status === "failed"
                        ? "text-ink-4 line-through"
                        : v.status === "running"
                          ? "text-ink"
                          : "text-ink-2 hover:text-ink"
                  }`}
                >
                  {v.status === "running" && <Spinner className="!h-2.5 !w-2.5 text-accent" />}v{v.n}
                  {v.is_current && <span className="h-1 w-1 rounded-full bg-accent" aria-label="current" />}
                </button>
              ))}
            </nav>
          )}
          <span className="ml-auto" />
          {tab === "product" && shown?.preview && <ViewToggle vm={vm} />}
          <MoreMenu items={menu} />
          {made ? (
            <BtnLink href={`/projects/${id}/wow`} variant="primary">
              Open overview <Arrow />
            </BtnLink>
          ) : (
            <Btn variant="primary" onClick={() => (showcase ? setAsk({ kind: "make" }) : makeIt())} disabled={makeDisabled}>
              {making && <Spinner />} Make it <Arrow />
            </Btn>
          )}
        </header>

        {previewing && shown && current && (
          <div className="flex items-center gap-3 rounded-md bg-surface px-4 py-2 text-sm">
            <span className="font-medium">Previewing v{shown.n}</span>
            <span className="min-w-0 flex-1 truncate text-ink-2" title={shown.summary}>
              {shown.summary}
            </span>
            <Btn size="sm" variant="ghost" onClick={() => setSelected(null)}>
              Back to v{current.n}
            </Btn>
            <Btn size="sm" variant="ink" onClick={() => setAsk({ kind: "restore", n: shown.n })} disabled={!!working || autorunning}>
              Restore v{shown.n}
            </Btn>
          </div>
        )}
        <div className="relative min-h-0 flex-1">
          {tab === "product" && (
            <Viewer v={shown} working={working?.n ?? null} alt={title || "Product"} vm={vm} photoNote={photoRunning ? "Taking the photo, about 12 s…" : photoNote} />
          )}
          {tab === "engineering" && <EngineeringTab eng={{ ...eng, available: available(TABS[1]) }} />}
          {tab === "code" && <CadCodeTab projectId={id} version={shown} versions={versions ?? []} available={available(TABS[2])} />}
          {tab === "firmware" && <FirmwareTab eng={{ ...eng, available: available(TABS[3]) }} />}
        </div>
        <div role="tablist" aria-label="Product views" className="flex items-center gap-5">
          {TABS.map((t) => {
            const on = available(t);
            return (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                title={on ? undefined : "Coming with the engineering layer"}
                className={`flex h-7 items-center gap-1.5 text-sm transition-colors duration-150 ${
                  tab === t.id ? "font-medium text-ink" : on ? "text-ink-3 hover:text-ink" : "text-ink-4"
                }`}
              >
                {t.label}
                {!on && paths && <span className="text-2xs">soon</span>}
              </button>
            );
          })}
          {shown?.background_pending && (
            <span className="ml-auto flex items-center gap-1.5 text-2xs text-ink-3">
              <Spinner className="!h-2.5 !w-2.5" /> DFM review and production plan updating
            </span>
          )}
        </div>
        <Strip p={shown?.preview} eng={eng.data} costs={shown?.n === current?.n ? costs : undefined} />
      </div>
    </div>
  );
}
