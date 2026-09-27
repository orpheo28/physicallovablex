import Link from "next/link";
import { docPages, docTitle, headings, readDoc, type NavPage } from "@/lib/docs";
import { Markdown } from "./Markdown";

/** One documentation page: the Markdown, "On this page" from its h2/h3, and prev / next in nav order. */
export function DocPage({ page }: { page: NavPage }) {
  const md = readDoc(page.file) ?? `# ${page.title}\n\nThis page is being written.`;
  const toc = headings(md);
  const pages = docPages();
  const i = pages.findIndex((p) => p.slug === page.slug);
  const prev = i > 0 ? pages[i - 1] : null;
  const next = i >= 0 && i < pages.length - 1 ? pages[i + 1] : null;
  return (
    <div className="flex gap-10 px-4 pb-20 pt-8 min-[900px]:px-10 min-[900px]:pt-10">
      <article className="min-w-0 max-w-[760px] flex-1">
        <Markdown source={md} />
        <nav aria-label="Previous and next" className="mt-16 grid grid-cols-2 gap-3 border-t border-line pt-6">
          {prev ? (
            <Link href={prev.href} className="group rounded-md bg-surface px-4 py-3 transition-colors hover:border-line-2">
              <span className="micro">← Previous</span>
              <span className="mt-1 block font-medium group-hover:text-accent-ink">{prev.title}</span>
            </Link>
          ) : (
            <span />
          )}
          {next ? (
            <Link href={next.href} className="group rounded-md bg-surface px-4 py-3 text-right transition-colors hover:border-line-2">
              <span className="micro">Next →</span>
              <span className="mt-1 block font-medium group-hover:text-accent-ink">{next.title}</span>
            </Link>
          ) : (
            <span />
          )}
        </nav>
      </article>
      {toc.length > 0 && (
        <aside aria-label="On this page" className="sticky top-14 hidden max-h-[calc(100dvh-56px)] w-[200px] shrink-0 self-start overflow-y-auto py-2 min-[1200px]:block">
          <p className="micro">On this page</p>
          <ul className="mt-2 border-l border-line">
            {toc.map((h) => (
              <li key={h.id}>
                <a href={`#${h.id}`} className={`-ml-px block border-l border-transparent py-1 text-[13px] text-ink-2 transition-colors hover:border-ink hover:text-ink ${h.depth === 3 ? "pl-6" : "pl-3"}`}>
                  {h.text}
                </a>
              </li>
            ))}
          </ul>
        </aside>
      )}
    </div>
  );
}

export function pageTitle(page: NavPage): string {
  const md = readDoc(page.file);
  return md ? docTitle(md, page.title) : page.title;
}
