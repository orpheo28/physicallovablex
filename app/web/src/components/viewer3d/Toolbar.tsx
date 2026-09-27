"use client";

import type { Preset } from "./Scene";

const PRESETS: { id: Preset; label: string }[] = [
  { id: "3q", label: "¾" },
  { id: "front", label: "Front" },
  { id: "side", label: "Side" },
  { id: "top", label: "Top" },
];

const chip = "press inline-flex h-7 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-sm transition-[color,background-color] duration-150";
const quiet = `${chip} bg-paper-2/80 text-ink-2 hover:bg-paper-2 hover:text-ink`;
const on = `${chip} bg-ink text-white`;

/** Camera chips (¾ · Front · Side · Top · Reset) and the view toggles (Exploded, X-ray, Anatomy), bottom of the stage. */
export function Toolbar({
  surface,
  exploded,
  xray,
  onPreset,
  onReset,
  onExploded,
  onXray,
  onAnatomy,
}: {
  surface: "studio" | "overview";
  exploded: boolean;
  xray: boolean;
  onPreset: (p: Preset) => void;
  onReset: () => void;
  onExploded: () => void;
  onXray: () => void;
  onAnatomy: () => void;
}) {
  return (
    <div
      className={`pointer-events-none absolute inset-x-0 flex items-end justify-between gap-3 ${surface === "overview" ? "bottom-6" : "bottom-5"}`}
      data-viewer-toolbar
    >
      <div role="group" aria-label="Camera" className="pointer-events-auto flex items-center gap-1">
        {PRESETS.map((p) => (
          <button key={p.id} onClick={() => onPreset(p.id)} className={quiet} data-preset={p.id} title={`${p.label === "¾" ? "Three-quarter" : p.label} view`}>
            {p.label}
          </button>
        ))}
        <button onClick={onReset} className={`${chip} text-ink-3 hover:text-ink`} title="Back to the assembled ¾ view">
          Reset
        </button>
      </div>
      <div role="group" aria-label="View" className="pointer-events-auto flex items-center gap-1">
        <button onClick={onExploded} aria-pressed={exploded} className={exploded ? on : quiet} data-toggle="exploded">
          <Icon d="M3 6.5h4v-3M13 6.5H9v-3M3 9.5h4v3M13 9.5H9v3" /> Exploded
        </button>
        <button onClick={onXray} aria-pressed={xray} className={xray ? on : quiet} data-toggle="xray">
          <Icon d="M8 2.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM8 5.5v5M5.5 8h5" /> X-ray
        </button>
        <button onClick={onAnatomy} className={`${chip} bg-ink text-white hover:bg-[#2a2a2a]`} data-toggle="anatomy" title="Walk inside the product, layer by layer">
          <Icon d="M2.5 8h11M8 2.5v11M4.5 4.5l7 7M11.5 4.5l-7 7" /> Anatomy
        </button>
      </div>
    </div>
  );
}

function Icon({ d }: { d: string }) {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={d} />
    </svg>
  );
}
