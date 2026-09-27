"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Lockup } from "./Lockup";
import { Nav } from "./Nav";

/** App bar (W26): lockup, three nav items, and a slot the project shell fills with its progress. No rule, just space. */
export function TopBar() {
  const path = usePathname() ?? "/";
  const login = path === "/login";
  return (
    <header data-chrome className="relative z-30 flex h-[52px] items-center gap-8 bg-paper px-5">
      <Link href="/" aria-label="PhysicalLovableX — home" className="shrink-0 rounded">
        <Lockup />
      </Link>
      <div id="topbar-slot" className="flex min-w-0 flex-1 items-center justify-center" />
      {!login && <Nav />}
    </header>
  );
}
