"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavGroup } from "@/lib/docs";

function Groups({ nav, path }: { nav: NavGroup[]; path: string }) {
  return (
    <>
      {nav.map((g) => (
        <div key={g.title} className="mb-5">
          <p className="micro px-2 pb-1.5">{g.title}</p>
          <ul>
            {g.pages.map((p) => {
              const active = !p.external && (path === p.href || (path === "/docs" && p.slug === "overview"));
              const cls = `relative flex items-center rounded-sm px-2 py-1.5 text-[14px] transition-colors duration-150 ${
                active ? "bg-surface font-medium text-ink" : "text-ink-2 hover:bg-paper-2 hover:text-ink"
              }`;
              return (
                <li key={p.href}>
                  {p.external ? (
                    // A raw file (text/markdown), not an app page: a plain link.
                    <a href={p.href} className={`${cls} font-mono text-[13px]`}>
                      {p.title}
                    </a>
                  ) : (
                    <Link href={p.href} aria-current={active ? "page" : undefined} className={cls}>
                      {active && <span className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-accent" aria-hidden />}
                      {p.title}
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </>
  );
}

/** Docs sidebar: groups from nav.json with the active page; under 900 px a collapsible menu above the page. */
export function DocsNav({ nav }: { nav: NavGroup[] }) {
  const path = usePathname() ?? "/docs";
  return (
    <>
      <nav aria-label="Documentation" className="sticky top-14 hidden max-h-[calc(100dvh-56px)] w-[232px] shrink-0 self-start overflow-y-auto py-8 pr-4 min-[900px]:block">
        <Groups nav={nav} path={path} />
      </nav>
      <details className="group border-b border-line px-4 py-3 min-[900px]:hidden">
        <summary className="flex cursor-pointer items-center justify-between text-sm font-medium">
          Documentation menu <span className="text-ink-3 transition-transform group-open:rotate-180">▾</span>
        </summary>
        <div className="mt-3">
          <Groups nav={nav} path={path} />
        </div>
      </details>
    </>
  );
}
