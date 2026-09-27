import type { Metadata } from "next";
import Link from "next/link";
import { Lockup } from "@/components/Lockup";
import { DocsNav } from "@/components/docs/DocsNav";
import { nav } from "@/lib/docs";

export const metadata: Metadata = {
  title: { default: "Docs", template: "%s · Docs · PhysicalLovableX" },
  description: "PhysicalLovableX documentation: the Studio, the Studio API, the production MCP, engineering checks and honest limits.",
  alternates: { types: { "text/markdown": "/agents.md" } },
};

/**
 * Public documentation (no password, no desktop gate: readable on phones). Unlike the app screens, a document
 * scrolls normally — `data-docs` lifts the app shell's no-scroll rule (globals.css).
 */
export default function DocsLayout({ children }: LayoutProps<"/docs">) {
  return (
    <div data-docs className="min-h-dvh bg-paper">
      <header className="sticky top-0 z-30 border-b border-line bg-paper/95 backdrop-blur-[6px]">
        <div className="mx-auto flex h-14 max-w-[1320px] items-center gap-4 px-4 min-[900px]:px-8">
          <Link href="/docs" aria-label="PhysicalLovableX docs" className="flex min-w-0 items-center gap-3 max-[520px]:[&>span>span:last-child]:hidden">
            <Lockup />
            <span className="hidden text-sm font-medium text-ink-2 min-[900px]:inline">Docs</span>
          </Link>
          <nav aria-label="Docs links" className="ml-auto flex shrink-0 items-center gap-1 text-sm">
            <a href="/agents.md" className="hidden rounded px-2.5 py-1 font-mono text-[13px] text-ink-2 min-[600px]:inline transition-colors hover:bg-paper-2 hover:text-ink">
              Agents.md
            </a>
            <Link href="/" className="inline-flex h-8 items-center rounded border border-accent bg-accent px-3 font-medium text-ink transition-colors hover:border-[#ff6a26] hover:bg-[#ff6a26]">
              Open the app
            </Link>
          </nav>
        </div>
      </header>
      <div className="mx-auto flex max-w-[1320px] flex-col px-0 min-[900px]:flex-row min-[900px]:px-8">
        <DocsNav nav={nav()} />
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
