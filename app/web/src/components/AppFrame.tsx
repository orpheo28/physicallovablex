"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { DesktopGate } from "./DesktopGate";
import { ScrollArea } from "./ScrollArea";
import { StatusBar } from "./StatusBar";
import { TipLayer } from "./TipLayer";
import { TopBar } from "./TopBar";

/** Public documentation renders on its own (any screen size, normal scrolling); everything else is the desktop app. */
export function isPublicDoc(path: string) {
  return path === "/docs" || path.startsWith("/docs/");
}

export function AppFrame({ children }: { children: ReactNode }) {
  const path = usePathname() ?? "/";
  if (isPublicDoc(path)) return <>{children}</>;
  return (
    <DesktopGate>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded focus:bg-ink focus:px-3 focus:py-1.5 focus:text-white">
        Skip to content
      </a>
      <div data-shell className="grid h-dvh grid-rows-[52px_minmax(0,1fr)_28px]">
        <TopBar />
        <ScrollArea as="main" id="main" className="h-full">
          {children}
        </ScrollArea>
        <StatusBar />
      </div>
      <TipLayer />
    </DesktopGate>
  );
}
