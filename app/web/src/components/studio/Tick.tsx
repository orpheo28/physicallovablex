"use client";

import { useEffect, useRef, useState } from "react";
import { animeNow, loadAnime, reducedMotion } from "@/lib/motion";

/**
 * A number that ticks from its previous value to the new one (anime.js, 600 ms outExpo) and flashes the
 * accent-soft tint behind it. First render and reduced motion: the final value at once. Ends exactly on `value`.
 */
export function Tick({ value, format, className = "" }: { value: number; format: (n: number) => string; className?: string }) {
  const [shown, setShown] = useState<number | null>(null);
  const prev = useRef(value);
  const box = useRef<HTMLSpanElement>(null);
  useEffect(() => void loadAnime(), []);
  useEffect(() => {
    const from = prev.current;
    prev.current = value;
    if (from === value || reducedMotion()) return;
    const a = animeNow();
    if (!a) return;
    const o = { v: from };
    const anim = a.animate(o, {
      v: value,
      duration: 600,
      ease: "outExpo",
      onUpdate: () => setShown(o.v),
      onComplete: () => setShown(null),
    });
    if (box.current) a.animate(box.current, { backgroundColor: ["#FFF1EA", "rgba(255,241,234,0)"], duration: 1200, ease: "inOutQuad" });
    return () => {
      anim.pause();
      setShown(null);
    };
  }, [value]);
  return (
    <span ref={box} className={`-mx-1 rounded-sm px-1 font-mono tabular-nums ${className}`}>
      {format(shown ?? value)}
    </span>
  );
}

/** Flash the accent-soft tint on a block when `signal` changes (text values such as colour or material). */
export function useFlash<T extends HTMLElement>(signal: string) {
  const ref = useRef<T>(null);
  const prev = useRef(signal);
  useEffect(() => {
    if (prev.current === signal) return;
    prev.current = signal;
    if (reducedMotion() || !ref.current) return;
    animeNow()?.animate(ref.current, { backgroundColor: ["#FFF1EA", "rgba(255,241,234,0)"], duration: 1200, ease: "inOutQuad" });
  }, [signal]);
  return ref;
}
