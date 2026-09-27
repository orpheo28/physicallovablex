"use client";

/**
 * anime.js v4, loaded on demand in client components only. Three moments use it (autofill stepper,
 * overview entrance, progress draw). Calm easing, no bounce or loops; with prefers-reduced-motion
 * nothing animates and the final state is shown at once.
 */
type Anime = typeof import("animejs");

let mod: Anime | null = null;
let loading: Promise<Anime | null> | null = null;

export function loadAnime(): Promise<Anime | null> {
  if (mod) return Promise.resolve(mod);
  if (!loading)
    loading = import("animejs")
      .then((m) => (mod = m))
      .catch(() => null);
  return loading;
}

/** The module if it is already loaded (so an entrance can start before the first paint), else null. */
export function animeNow(): Anime | null {
  return mod;
}

export function reducedMotion(): boolean {
  if (typeof window === "undefined") return true;
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

/** Play `key` once per browser session (sessionStorage; if storage is blocked, play every time). */
export function firstTimeThisVisit(key: string): boolean {
  try {
    if (window.sessionStorage.getItem(key)) return false;
    window.sessionStorage.setItem(key, "1");
    return true;
  } catch {
    return true;
  }
}
