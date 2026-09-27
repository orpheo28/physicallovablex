import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Public documentation, read at build time from web/content/docs (synced from ../docs/public by `npm run sync-docs`).
 * nav.json drives the sidebar; pages without a file are skipped, so a partial delivery still builds.
 */
const DIR = join(process.cwd(), "content", "docs");

export type NavPage = { slug: string; title: string; file: string; href: string; external: boolean };
export type NavGroup = { title: string; pages: NavPage[] };
export type Heading = { depth: 2 | 3; text: string; id: string };

const FALLBACK: { title: string; pages: { slug: string; title: string; file: string; path?: string }[] }[] = [
  { title: "Getting started", pages: [
    { slug: "overview", title: "Overview", file: "overview.md" },
    { slug: "quickstart", title: "Quickstart", file: "quickstart.md" },
    { slug: "concepts", title: "Concepts", file: "concepts.md" },
  ] },
];

export function readDoc(file: string): string | null {
  const p = join(DIR, file);
  return existsSync(p) ? readFileSync(p, "utf8") : null;
}

export function nav(): NavGroup[] {
  let groups = FALLBACK;
  const raw = readDoc("nav.json");
  if (raw) {
    try {
      const j = JSON.parse(raw);
      if (Array.isArray(j?.groups)) groups = j.groups;
    } catch {
      /* keep the fallback */
    }
  }
  return groups
    .map((g) => ({
      title: String(g.title ?? ""),
      pages: (g.pages ?? [])
        .filter((p) => p.path || existsSync(join(DIR, p.file)))
        .map((p) => ({ slug: p.slug, title: p.title, file: p.file, href: p.path ?? `/docs/${p.slug}`, external: !!p.path })),
    }))
    .filter((g) => g.pages.length > 0);
}

/** Pages rendered under /docs/[slug] (entries with an explicit path, like /agents.md, are served elsewhere). */
export function docPages(): NavPage[] {
  return nav().flatMap((g) => g.pages).filter((p) => !p.external);
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[`*_~[\]()]/g, "")
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-");
}

/** h2 / h3 outside code fences, for the "On this page" list (same ids as the rendered headings). */
export function headings(md: string): Heading[] {
  const out: Heading[] = [];
  let fence = false;
  for (const line of md.split("\n")) {
    if (/^\s*```/.test(line)) fence = !fence;
    if (fence) continue;
    const m = /^(##|###)\s+(.+?)\s*#*\s*$/.exec(line);
    if (m) {
      const text = m[2].replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").replace(/[`*_]/g, "");
      out.push({ depth: m[1].length as 2 | 3, text, id: slugify(text) });
    }
  }
  return out;
}

/** The first # heading, else the nav title. */
export function docTitle(md: string, fallback: string): string {
  return /^#\s+(.+)$/m.exec(md)?.[1].trim() ?? fallback;
}
