"use client";

import { useState, useSyncExternalStore, type ReactNode } from "react";
import { Lockup } from "./Lockup";

// Below 1024 px, or a touch-first device on a small screen: the desktop app is not rendered at all.
const QUERY = "(max-width: 1023.98px), (pointer: coarse) and (max-width: 1279.98px)";

function subscribe(cb: () => void) {
  const mq = window.matchMedia(QUERY);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}
const getSnapshot = () => (window.matchMedia(QUERY).matches ? "mobile" : "desktop");
// Server: unknown. Nothing of the app renders (no fetch starts) until the client knows the screen.
const getServerSnapshot = () => "unknown";

function MobileGate() {
  const url = typeof window !== "undefined" ? window.location.href : "";
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }
  return (
    <div className="flex h-dvh flex-col justify-between bg-paper px-6 py-8" data-mobile-gate>
      <Lockup />
      <div className="max-w-[440px]">
        <p className="micro">Desktop only, for now</p>
        <h1 className="title mt-3 text-[34px] leading-[40px]">Built for desktop</h1>
        <p className="mt-4 text-md text-ink-2">PhysicalLovableX is designed for a laptop or desktop screen. The mobile version is coming soon.</p>
        <div className="mt-8">
          <p className="micro">Open this link on a computer</p>
          <div className="mt-2 flex items-stretch overflow-hidden rounded border border-line-2 bg-surface">
            <span className="min-w-0 flex-1 truncate px-3 py-2.5 font-mono text-sm text-ink" title={url}>
              {url}
            </span>
            <button onClick={copy} className="shrink-0 border-l border-line-2 px-3 text-sm font-medium text-ink transition-colors duration-150 hover:bg-sunken">
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      </div>
      <p className="text-sm text-ink-3">Case-study demo. All factories, quotes and freight rates are fictional demo data.</p>
    </div>
  );
}

/** Renders the app only on a desktop-sized screen; otherwise a full-screen "Built for desktop" message and nothing else. */
export function DesktopGate({ children }: { children: ReactNode }) {
  const screen = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  if (screen === "unknown") return <div className="h-dvh bg-paper" aria-busy="true" />;
  if (screen === "mobile") return <MobileGate />;
  return <>{children}</>;
}
