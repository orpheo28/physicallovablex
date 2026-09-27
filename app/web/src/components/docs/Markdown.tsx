import Link from "next/link";
import { Children, isValidElement, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { slugify } from "@/lib/docs";
import { CopyButton } from "./CopyButton";

function text(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(text).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return text(node.props.children);
  return "";
}

function Anchor({ level, children }: { level: 2 | 3; children: ReactNode }) {
  const id = slugify(text(children));
  const Tag = level === 2 ? "h2" : "h3";
  return (
    <Tag id={id} className={`group scroll-mt-20 ${level === 2 ? "mt-12 border-t border-line pt-6 text-xl font-semibold tracking-[-0.02em]" : "mt-8 text-lg font-semibold tracking-[-0.015em]"}`}>
      {children}
      <a href={`#${id}`} aria-label="Link to this section" className="ml-2 text-ink-4 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100">
        #
      </a>
    </Tag>
  );
}

const CALLOUT = /^(note|warning|important|tip|caution)\b[:.]?\s*/i;

const components: Components = {
  h1: ({ children }) => <h1 className="title text-[36px] leading-[42px] max-md:text-[30px] max-md:leading-[36px]">{children}</h1>,
  h2: ({ children }) => <Anchor level={2}>{children}</Anchor>,
  h3: ({ children }) => <Anchor level={3}>{children}</Anchor>,
  p: ({ children }) => <p className="mt-4 text-[15px] leading-[26px] text-ink">{children}</p>,
  a: ({ href = "", children }) =>
    href.startsWith("/") || href.startsWith("#") ? (
      <Link href={href} className="text-ink underline decoration-accent/50 underline-offset-4 hover:decoration-accent">
        {children}
      </Link>
    ) : (
      <a href={href} target="_blank" rel="noreferrer" className="text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink">
        {children}
      </a>
    ),
  ul: ({ children }) => <ul className="mt-4 flex list-disc flex-col gap-1.5 pl-5 text-[15px] leading-[26px] marker:text-ink-4">{children}</ul>,
  ol: ({ children }) => <ol className="mt-4 flex list-decimal flex-col gap-1.5 pl-5 text-[15px] leading-[26px] marker:font-mono marker:text-ink-3">{children}</ol>,
  li: ({ children }) => <li className="pl-1 [&>p]:mt-1">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  hr: () => <hr className="my-10 border-line" />,
  code: ({ className, children }) => {
    // Block code is rendered by `pre` below; this is inline code.
    if (/language-/.test(className ?? "")) return <code className={className}>{children}</code>;
    return <code className="rounded-sm bg-paper-2/70 px-1 py-px font-mono text-[13px]">{children}</code>;
  },
  pre: ({ children }) => {
    const child = Children.toArray(children)[0];
    const cls = isValidElement<{ className?: string }>(child) ? (child.props.className ?? "") : "";
    const lang = /language-(\S+)/.exec(cls)?.[1] ?? "";
    const code = text(children).replace(/\n$/, "");
    return (
      <div className="mt-5 overflow-hidden rounded-md bg-surface">
        <div className="flex items-center justify-between border-b border-line bg-sunken px-3 py-1.5">
          <span className="font-mono text-2xs text-ink-3">{lang || "text"}</span>
          <CopyButton text={code} />
        </div>
        <pre className="overflow-x-auto px-4 py-3 font-mono text-[13px] leading-[21px] text-ink">
          <code>{code}</code>
        </pre>
      </div>
    );
  },
  table: ({ children }) => (
    <div className="mt-5 overflow-x-auto rounded-md bg-surface">
      <table className="w-full border-collapse text-[14px] leading-[22px]">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="whitespace-nowrap border-b border-line px-3 py-2 text-left text-[12.5px] font-medium text-ink-3">{children}</th>
  ),
  td: ({ children }) => <td className="border-b border-line px-3 py-2 align-top [tr:last-child_&]:border-b-0">{children}</td>,
  blockquote: ({ children }) => {
    const t = text(children).trim();
    const m = CALLOUT.exec(t);
    const warn = !!m && /warning|caution|important/i.test(m[1]);
    // Brand: blue and green are trust-label colours only. Note = ink rule on paper; Warning = amber (a severity).
    return (
      <aside
        className={`mt-5 rounded-r-md border-l-2 px-4 pb-4 pt-1 text-[15px] [&>p:first-child]:mt-3 ${
          warn ? "border-estimate bg-estimate-soft" : m ? "border-ink bg-paper-2/70" : "border-line-2 bg-transparent text-ink-2"
        }`}
        role={m ? "note" : undefined}
      >
        {children}
      </aside>
    );
  },
};

export function Markdown({ source }: { source: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {source}
    </ReactMarkdown>
  );
}
