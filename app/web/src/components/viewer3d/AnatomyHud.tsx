"use client";

import { useEffect, useLayoutEffect, useRef, type MutableRefObject } from "react";
import type { AnatomyStep } from "@/lib/parts";
import { animeNow, loadAnime, reducedMotion } from "@/lib/motion";

/** Log scale of the ruler: 10 m (top) → 1 mm (bottom). */
const TOP = 1;
const BOTTOM = -3;
const RULER_H = 280;
const yOf = (m: number) => ((TOP - Math.log10(Math.max(1e-4, Math.min(100, m)))) / (TOP - BOTTOM)) * RULER_H;

export function fmtWidth(m: number): string {
  if (m >= 1) return `${m.toFixed(m >= 10 ? 0 : 1)} m`;
  if (m >= 0.01) return `${(m * 100).toFixed(m >= 0.1 ? 0 : 1)} cm`;
  return `${(m * 1000).toFixed(1)} mm`;
}

/**
 * Anatomy mode chrome on the dark stage: the step caption (mono kicker, title, one line), ← Prev / Next →, step dots,
 * the live scale ruler (field-of-view width on a log scale) and the honesty line, always visible.
 */
export function AnatomyHud({
  steps,
  step,
  label,
  mock,
  onGo,
  onPrev,
  onNext,
  onExit,
  rulerRef,
  initialWidth,
}: {
  steps: AnatomyStep[];
  step: number;
  label: string;
  mock: boolean;
  onGo: (i: number) => void;
  onPrev: () => void;
  onNext: () => void;
  onExit: () => void;
  rulerRef: MutableRefObject<(w: number) => void>;
  initialWidth: number;
}) {
  const s = steps[step];
  const caption = useRef<HTMLDivElement>(null);
  const marker = useRef<HTMLDivElement>(null);
  const text = useRef<HTMLSpanElement>(null);

  // The ruler follows the camera frustum width (updated by the scene, no React re-render per frame).
  useEffect(() => {
    rulerRef.current = (w: number) => {
      if (marker.current) marker.current.style.transform = `translateY(${yOf(w)}px)`;
      if (text.current) text.current.textContent = `Field of view ≈ ${fmtWidth(w)}`;
    };
    if (initialWidth) rulerRef.current(initialWidth);
    return () => void (rulerRef.current = () => undefined);
  }, [rulerRef, initialWidth]);

  useLayoutEffect(() => {
    const el = caption.current;
    if (!el || reducedMotion()) return;
    const run = (a: NonNullable<ReturnType<typeof animeNow>>) => a.animate(el.children, { opacity: [0, 1], translateY: [6, 0], duration: 420, delay: a.stagger(60), ease: "outExpo" });
    const a = animeNow();
    if (a) run(a);
    else
      loadAnime().then((m) => {
        if (m) run(m);
      });
  }, [step]);

  const decades = [10, 1, 0.1, 0.01, 0.001];
  const names = ["10 m", "1 m", "10 cm", "1 cm", "1 mm"];
  return (
    <div className="pointer-events-none absolute inset-0 text-white" data-anatomy-hud>
      {/* Caption */}
      <div ref={caption} className="absolute left-10 top-9 max-w-[440px]" aria-live="polite">
        <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-white/55" data-kicker>
          {s?.kicker}
        </p>
        <h2 className="mt-2 text-[28px] font-semibold leading-[34px] tracking-[-0.022em]">{s?.title}</h2>
        <p className="mt-2 text-md leading-[26px] text-white/70">{s?.caption}</p>
      </div>

      {/* Exit */}
      <button
        onClick={onExit}
        className="press pointer-events-auto absolute right-6 top-6 inline-flex h-8 items-center gap-2 rounded px-3 text-sm text-white/80 transition-colors duration-150 hover:bg-white/10 hover:text-white"
        data-anatomy-exit
      >
        Exit anatomy <kbd className="rounded-sm bg-white/10 px-1.5 font-mono text-[10.5px] text-white/60">Esc</kbd>
      </button>

      {/* Scale ruler */}
      <div className="absolute right-9 top-1/2 -translate-y-1/2" style={{ height: RULER_H }} aria-hidden data-ruler>
        <div className="absolute right-0 top-0 h-full w-px bg-white/25" />
        {decades.map((d, i) => (
          <div key={d} className="absolute right-0 flex items-center gap-2" style={{ top: yOf(d), transform: "translateY(-50%)" }}>
            <span className="whitespace-nowrap font-mono text-[10.5px] text-white/40">{names[i]}</span>
            <span className="h-px w-3 bg-white/40" />
          </div>
        ))}
        {decades.slice(0, -1).flatMap((d) =>
          [2, 3, 4, 5, 6, 7, 8, 9].map((k) => <span key={`${d}-${k}`} className="absolute right-0 h-px w-1.5 bg-white/20" style={{ top: yOf((d / 10) * k) }} />),
        )}
        <div ref={marker} className="absolute right-0 top-0 flex items-center gap-2 transition-transform duration-150" style={{ marginTop: -1 }}>
          <span ref={text} className="whitespace-nowrap rounded-full bg-white px-2 py-0.5 font-mono text-[11px] text-ink" data-fov>
            Field of view
          </span>
          <span className="h-0.5 w-5 bg-white" />
        </div>
      </div>

      {/* Steps */}
      <div className="pointer-events-auto absolute bottom-6 left-1/2 flex -translate-x-1/2 items-center gap-3" role="group" aria-label="Anatomy steps">
        <button onClick={onPrev} disabled={step === 0} className="press inline-flex h-8 items-center rounded px-3 text-sm text-white/80 transition-colors duration-150 hover:bg-white/10 hover:text-white disabled:text-white/25 disabled:hover:bg-transparent" data-anatomy-prev>
          ← Prev
        </button>
        <div className="flex items-center gap-1.5">
          {steps.map((x, i) => (
            <button
              key={x.id}
              onClick={() => onGo(i)}
              aria-label={`Step ${i + 1}: ${x.title}`}
              aria-current={i === step ? "step" : undefined}
              className={`h-1.5 rounded-full transition-[width,background-color] duration-200 ${i === step ? "w-5 bg-white" : "w-1.5 bg-white/30 hover:bg-white/60"}`}
            />
          ))}
        </div>
        <span className="font-mono text-2xs text-white/50">
          {String(step + 1).padStart(2, "0")} / {String(steps.length).padStart(2, "0")}
        </span>
        <button onClick={onNext} disabled={step >= steps.length - 1} className="press inline-flex h-8 items-center rounded bg-white px-3 text-sm font-medium text-ink transition-colors duration-150 hover:bg-white/85 disabled:bg-white/15 disabled:text-white/40" data-anatomy-next>
          Next →
        </button>
      </div>
      <p className="absolute bottom-[70px] left-1/2 -translate-x-1/2 text-2xs text-white/35">Scroll inside the view, or use ← →</p>

      {/* Honesty, always visible */}
      <p className="absolute bottom-6 left-10 flex max-w-[34%] items-center gap-2 text-2xs text-white/60" data-anatomy-label>
        <span className="tdot bg-estimate" aria-hidden />
        {label}
        {mock ? " · internals estimated from the BOM" : ""}
      </p>
    </div>
  );
}
