"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/projects", label: "Projects", match: (p: string) => p.startsWith("/projects") },
  { href: "/", label: "New project", match: (p: string) => p === "/" || p.startsWith("/new") },
  { href: "/factories", label: "Factory portal", match: (p: string) => p.startsWith("/factories") },
];

export function Nav() {
  const path = usePathname() ?? "/";
  if (path === "/login") return null; // the password screen shows the logo only
  return (
    <nav aria-label="Main" className="flex items-center gap-1">
      {ITEMS.map((i) => {
        const active = i.match(path);
        return (
          <Link
            key={i.href}
            href={i.href}
            aria-current={active ? "page" : undefined}
            className={`rounded px-2.5 py-1 text-sm transition-colors duration-150 ${active ? "text-ink" : "text-ink-2 hover:text-ink"}`}
          >
            <span className={active ? "border-b border-ink pb-[3px]" : ""}>{i.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
