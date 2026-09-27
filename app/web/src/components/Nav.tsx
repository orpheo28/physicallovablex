"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// W26: three items. The lockup is "new project" (home); projects are reached from each project's rail.
const ITEMS = [
  { href: "/examples", label: "Examples", match: (p: string) => p.startsWith("/examples") },
  { href: "/factories", label: "Factory portal", match: (p: string) => p.startsWith("/factories") },
  { href: "/docs", label: "Docs", match: (p: string) => p.startsWith("/docs") },
];

export function Nav() {
  const path = usePathname() ?? "/";
  if (path === "/login") return null; // the password screen shows the logo only
  return (
    <nav aria-label="Main" className="flex shrink-0 items-center gap-0.5">
      {ITEMS.map((i) => {
        const active = i.match(path);
        return (
          <Link
            key={i.href}
            href={i.href}
            aria-current={active ? "page" : undefined}
            className={`rounded px-3 py-1.5 text-sm transition-colors duration-150 ${active ? "bg-paper-2 font-medium text-ink" : "text-ink-2 hover:bg-paper-2 hover:text-ink"}`}
          >
            {i.label}
          </Link>
        );
      })}
    </nav>
  );
}
