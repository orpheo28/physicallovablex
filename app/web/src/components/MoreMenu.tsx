"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

export type MenuItem = { label: string; href?: string; onClick?: () => void; hint?: string; disabled?: boolean };

/** "⋯" menu for secondary actions (W26: one primary action per screen, the rest in here). */
export function MoreMenu({ items, label = "More actions" }: { items: MenuItem[]; label?: string }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);
  const cls = "flex w-full flex-col items-start gap-0.5 rounded-sm px-3 py-2 text-left text-sm text-ink transition-colors hover:bg-paper disabled:cursor-not-allowed disabled:text-ink-4 disabled:hover:bg-transparent";
  return (
    <div ref={box} className="relative">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={`press flex h-8 w-8 items-center justify-center rounded text-ink-2 hover:bg-paper-2 hover:text-ink ${open ? "bg-paper-2 text-ink" : ""}`}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
          <circle cx="3.5" cy="8" r="1.25" />
          <circle cx="8" cy="8" r="1.25" />
          <circle cx="12.5" cy="8" r="1.25" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-40 w-[260px] rounded-lg bg-surface p-1.5 shadow-float">
          {items.map((i) =>
            i.href ? (
              <Link key={i.label} href={i.href} className={cls} onClick={() => setOpen(false)}>
                <span className="font-medium">{i.label}</span>
                {i.hint && <span className="text-2xs text-ink-3">{i.hint}</span>}
              </Link>
            ) : (
              <button
                key={i.label}
               
                type="button"
                disabled={i.disabled}
                className={cls}
                onClick={() => {
                  setOpen(false);
                  i.onClick?.();
                }}
              >
                <span className="font-medium">{i.label}</span>
                {i.hint && <span className="text-2xs text-ink-3">{i.hint}</span>}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
