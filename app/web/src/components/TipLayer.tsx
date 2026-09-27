"use client";

import { useEffect, useRef, useState } from "react";
import type { Label } from "@/types/contracts";
import { LABEL_DOT, LABEL_TEXT } from "@/lib/meta";

type Tip = { label: Label | null; text: string; x: number; y: number; below: boolean };

/**
 * One tooltip for every trust label (W26): hovering or focusing an element with `data-tip` shows its label
 * (coloured dot + name) and its source or assumption. Fixed-position, so scroll regions never clip it.
 */
export function TipLayer() {
  const [tip, setTip] = useState<Tip | null>(null);
  const [on, setOn] = useState(false);
  const cur = useRef<Element | null>(null);

  useEffect(() => {
    const show = (el: Element) => {
      const text = el.getAttribute("data-tip") ?? "";
      const raw = el.getAttribute("data-tip-label");
      const label = raw && raw in LABEL_TEXT ? (raw as Label) : null;
      if (!text && !label) return;
      cur.current = el;
      const r = el.getBoundingClientRect();
      const below = r.top < 120;
      setTip({ label, text, x: Math.min(Math.max(r.left + r.width / 2, 170), window.innerWidth - 170), y: below ? r.bottom + 8 : r.top - 8, below });
      requestAnimationFrame(() => setOn(true));
    };
    const hide = () => {
      cur.current = null;
      setOn(false);
    };
    const over = (e: Event) => {
      const el = (e.target as Element | null)?.closest?.("[data-tip]");
      if (el === cur.current) return;
      if (el) show(el);
      else hide();
    };
    document.addEventListener("pointerover", over);
    document.addEventListener("focusin", over);
    document.addEventListener("focusout", hide);
    window.addEventListener("scroll", hide, true);
    return () => {
      document.removeEventListener("pointerover", over);
      document.removeEventListener("focusin", over);
      document.removeEventListener("focusout", hide);
      window.removeEventListener("scroll", hide, true);
    };
  }, []);

  if (!tip) return null;
  return (
    <div
      role="tooltip"
      className="tip"
      data-on={on ? "" : undefined}
      style={{ left: tip.x, top: tip.y, transform: `translate(-50%, ${tip.below ? "0" : "-100%"})` }}
    >
      {tip.label && (
        <span className="mb-0.5 flex items-center gap-1.5 font-medium">
          <span className={`tdot ${LABEL_DOT[tip.label]}`} aria-hidden />
          {LABEL_TEXT[tip.label]}
        </span>
      )}
      {tip.text && tip.text !== LABEL_TEXT[tip.label ?? "estimate"] && <span className="block text-white/75">{tip.text}</span>}
    </div>
  );
}
