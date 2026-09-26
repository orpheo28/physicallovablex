"use client";

import Link from "next/link";
import { Component, useState, type ReactNode } from "react";
import type { Assumption, Label, LabeledValue } from "@/types/contracts";
import { fmtValue, LABEL_CLASS, LABEL_DOT, LABEL_TEXT, LAYER_CLASS, type Layer } from "@/lib/meta";

// ------------------------------------------------------------------ trust labels

export function LabelBadge({ label, tip, small }: { label: Label | string; tip?: string | null; small?: boolean }) {
  const l = (label in LABEL_TEXT ? label : "estimate") as Label;
  return (
    <span
      title={tip ?? LABEL_TEXT[l]}
      className={`inline-flex shrink-0 cursor-help items-center gap-1.5 whitespace-nowrap rounded-full font-sans font-medium normal-case tracking-normal ${
        small ? "h-[18px] px-1.5 text-[10.5px]" : "h-5 px-2 text-2xs"
      } ${LABEL_CLASS[l]}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${LABEL_DOT[l]}`} aria-hidden />
      {LABEL_TEXT[l]}
    </span>
  );
}

/** A LabeledValue: value + unit + badge, tooltip = source_or_assumption. */
export function LV({ v, big, noBadge, className = "" }: { v: LabeledValue | null | undefined; big?: boolean; noBadge?: boolean; className?: string }) {
  if (!v) return <span className="text-ink-4">—</span>;
  return (
    <span className={`inline-flex flex-wrap items-center gap-x-2 gap-y-1 ${className}`} title={v.source_or_assumption}>
      <span className={`font-mono tabular-nums ${big ? "text-xl font-medium tracking-tight" : ""}`}>{fmtValue(v)}</span>
      {!noBadge && <LabelBadge label={v.label} tip={v.source_or_assumption} small={!big} />}
    </span>
  );
}

export function LayerTag({ layer }: { layer: Layer }) {
  return (
    <span className={`inline-flex h-[18px] items-center rounded-sm border px-1.5 text-[10px] font-medium uppercase tracking-[0.08em] ${LAYER_CLASS[layer]}`}>
      {layer}
    </span>
  );
}

// ------------------------------------------------------------------ structure

/** Uppercase micro-label header with a hairline; optional right-side content. */
export function SectionHeader({ title, right, className = "" }: { title: ReactNode; right?: ReactNode; className?: string }) {
  return (
    <div className={`flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-line pb-2 ${className}`}>
      <h3 className="micro">{title}</h3>
      {right && <div className="flex flex-wrap items-center gap-2 text-sm text-ink-2">{right}</div>}
    </div>
  );
}

/**
 * A titled section. White surface with a hairline border (no shadow).
 * `fictional` marks simulated network records: a violet rule + the label, never hidden.
 */
export function Card({
  title,
  children,
  fictional,
  right,
  className = "",
  flush,
}: {
  title?: ReactNode;
  children: ReactNode;
  fictional?: boolean;
  right?: ReactNode;
  className?: string;
  flush?: boolean;
}) {
  return (
    <section className={`relative rounded-md border border-line bg-surface ${className}`}>
      {fictional && <span className="absolute inset-y-0 left-0 w-[2px] rounded-l-md bg-fictional/50" aria-hidden />}
      {(title || fictional || right) && (
        <header className="flex min-h-11 flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-line px-5 py-2.5">
          <h3 className="text-base font-medium text-ink">{title}</h3>
          <div className="flex flex-wrap items-center gap-2 text-sm text-ink-2">
            {right}
            {fictional && <LabelBadge label="fictional" tip="Simulated network record — demo data" small />}
          </div>
        </header>
      )}
      <div className={flush ? "" : "p-5"}>{children}</div>
    </section>
  );
}

/** A key number with its label. */
export function Stat({ label, children, sub, accent }: { label: ReactNode; children: ReactNode; sub?: ReactNode; accent?: boolean }) {
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <span className="micro">{label}</span>
      <div className={accent ? "[&_.font-mono]:text-accent-ink" : ""}>{children}</div>
      {sub && <span className="text-sm text-ink-2">{sub}</span>}
    </div>
  );
}

export function KV({ k, children }: { k: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="micro">{k}</span>
      <span className="text-base text-ink">{children}</span>
    </div>
  );
}

// ------------------------------------------------------------------ feedback

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-[1.5px] border-current border-r-transparent opacity-70 ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <span className={`block animate-shimmer rounded-sm bg-paper-2 ${className}`} aria-hidden />;
}

/** Loading state: a quiet line of text over skeleton bars. */
export function Loading({ text = "Loading…", rows = 3 }: { text?: string; rows?: number }) {
  return (
    <div className="flex flex-col gap-3 py-6" role="status" aria-live="polite">
      <span className="flex items-center gap-2 text-sm text-ink-2">
        <Spinner /> {text}
      </span>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className={`h-3 ${i % 3 === 0 ? "w-3/4" : i % 3 === 1 ? "w-1/2" : "w-2/3"}`} />
      ))}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-md border border-danger/25 bg-danger-soft px-4 py-3 text-sm text-danger">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
        <circle cx="8" cy="8" r="6.5" />
        <path d="M8 4.5v4M8 10.8v.2" strokeLinecap="round" />
      </svg>
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="rounded border border-danger/30 px-2 py-0.5 text-xs font-medium transition-colors hover:bg-white/60">
          Retry
        </button>
      )}
    </div>
  );
}

/** Plain-language cause of a fallback; the raw exception text stays in the collapsed Details. */
export function fallbackWording(reason?: string | null): string {
  const r = (reason ?? "").toLowerCase();
  if (/timeout|timed out/.test(r)) return "Timed out";
  if (/not ?configured|api[_ ]?key|env var missing|credit|402|payment|insufficient|unauthori[sz]ed|401/.test(r)) return "AI unavailable (no API key / credits)";
  return "Service error";
}

export function CachedBanner({ reason, example, scope = "stage" }: { reason?: string | null; example?: string | null; scope?: "stage" | "project" }) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-estimate/30 bg-estimate-soft px-4 py-2.5 text-sm text-estimate-ink" role="status">
      <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-estimate" aria-hidden />
      <div className="min-w-0">
        <p>
          <strong className="mr-2 font-semibold">Cached example</strong>
          {scope === "project" ? (
            <span>AI was unavailable for part of this run — some figures come from a pre-computed example.</span>
          ) : (
            <span>
              {fallbackWording(reason)}. This is a pre-computed example{example ? ` (${example.replace(/_/g, " ")})` : ""}, not a live result for your
              product — it may show another product such as the desk lamp.
            </span>
          )}
          {scope === "project" && reason ? <span className="ml-1">{fallbackWording(reason)}.</span> : null}
        </p>
        {reason ? (
          <details className="mt-1 text-xs text-ink-3">
            <summary className="cursor-pointer hover:text-ink">Details</summary>
            <p className="mt-1 break-words font-mono">{reason}</p>
          </details>
        ) : null}
      </div>
    </div>
  );
}

/** Empty state: one sentence, one action. */
export function Empty({ title, body, action }: { title: ReactNode; body?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-md border border-line bg-surface px-6 py-8">
      <p className="text-md font-medium text-ink">{title}</p>
      {body && <p className="max-w-prose text-base text-ink-2">{body}</p>}
      {action && <div className="mt-3 flex flex-wrap gap-2">{action}</div>}
    </div>
  );
}

export function Assumptions({ items }: { items: Assumption[] | undefined }) {
  const [open, setOpen] = useState(false);
  if (!items || items.length === 0) return <p className="text-sm text-ink-3">No assumptions recorded for this stage.</p>;
  return (
    <div className="rounded-md border border-line bg-surface">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-5 py-3 text-left transition-colors hover:bg-sunken"
      >
        <span className="text-base font-medium">
          Assumptions <span className="font-mono text-ink-3">{items.length}</span>
        </span>
        <Chevron open={open} />
      </button>
      {open && (
        <ul className="divide-y divide-line border-t border-line">
          {items.map((a) => (
            <li key={a.id} className="grid grid-cols-[150px_1fr] items-start gap-3 px-5 py-2.5 text-base">
              <span>
                <LabelBadge label={a.label} tip={a.source ?? undefined} small />
              </span>
              <span>
                {a.text}
                {a.source && <span className="block text-sm text-ink-3">{a.source}</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Chevron({ open, className = "" }: { open?: boolean; className?: string }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={`text-ink-3 transition-transform duration-150 ${open ? "rotate-180" : ""} ${className}`}
      aria-hidden
    >
      <path d="m4 6 4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Arrow({ className = "" }: { className?: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className={className} aria-hidden>
      <path d="M3 8h10M9 4l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ------------------------------------------------------------------ actions

type Variant = "primary" | "secondary" | "ghost" | "ink";
type Size = "sm" | "md" | "lg";

function btnClass(variant: Variant, size: Size, className: string) {
  const v = {
    primary: "bg-accent text-ink border-accent hover:bg-[#ff6a26] hover:border-[#ff6a26] font-medium",
    ink: "bg-ink text-white border-ink hover:bg-[#2a2a2a] hover:border-[#2a2a2a]",
    secondary: "bg-surface text-ink border-line-2 hover:border-ink-4 hover:bg-sunken",
    ghost: "border-transparent text-ink-2 hover:text-ink hover:bg-paper-2",
  }[variant];
  const s = { sm: "h-7 px-2.5 text-sm gap-1.5", md: "h-8 px-3 text-sm gap-2", lg: "h-10 px-4 text-base gap-2" }[size];
  return `inline-flex shrink-0 select-none items-center justify-center whitespace-nowrap rounded border font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-45 ${s} ${v} ${className}`;
}

export function Btn({
  children,
  onClick,
  disabled,
  variant = "secondary",
  size = "md",
  type = "button",
  className = "",
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: Variant;
  size?: Size;
  type?: "button" | "submit";
  className?: string;
  title?: string;
}) {
  return (
    <button type={type} onClick={onClick} disabled={disabled} title={title} className={btnClass(variant, size, className)}>
      {children}
    </button>
  );
}

export function BtnLink({
  href,
  children,
  variant = "secondary",
  size = "md",
  className = "",
}: {
  href: string;
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  className?: string;
}) {
  return (
    <Link href={href} className={btnClass(variant, size, className)}>
      {children}
    </Link>
  );
}

/** Segmented control (EN / 中文, 3D / render…). */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: ReactNode; disabled?: boolean }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded border border-line-2 bg-surface p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={value === o.value}
          disabled={o.disabled}
          onClick={() => onChange(o.value)}
          className={`h-6 rounded-sm px-2.5 text-xs font-medium transition-colors duration-150 disabled:opacity-40 ${
            value === o.value ? "bg-ink text-white" : "text-ink-2 hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------ pills

type Tone = "zinc" | "red" | "amber" | "green" | "blue" | "violet" | "accent";

export function Pill({ children, tone = "zinc", dot }: { children: ReactNode; tone?: Tone; dot?: boolean }) {
  const t = {
    zinc: "bg-paper-2 text-ink-2",
    red: "bg-danger-soft text-danger",
    amber: "bg-estimate-soft text-estimate-ink",
    green: "bg-measured-soft text-measured-ink",
    blue: "bg-sourced-soft text-sourced-ink",
    violet: "bg-fictional-soft text-fictional-ink",
    accent: "bg-accent-soft text-accent-ink",
  }[tone];
  const d = {
    zinc: "bg-ink-4",
    red: "bg-danger",
    amber: "bg-estimate",
    green: "bg-measured",
    blue: "bg-sourced",
    violet: "bg-fictional",
    accent: "bg-accent",
  }[tone];
  return (
    <span className={`inline-flex h-5 items-center gap-1.5 self-start whitespace-nowrap rounded-full px-2 text-2xs font-medium normal-case tracking-normal ${t}`}>
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${d}`} aria-hidden />}
      {children}
    </span>
  );
}

export function severityTone(s: string): Tone {
  return s === "critical" || s === "high" ? "red" : s === "major" || s === "medium" ? "amber" : "zinc";
}

/** Severity as text + a small square marker (quieter than a coloured pill). */
export function Severity({ level }: { level: string }) {
  const tone = severityTone(level);
  const c = tone === "red" ? "bg-danger" : tone === "amber" ? "bg-estimate" : "bg-ink-4";
  const t = tone === "red" ? "text-danger" : tone === "amber" ? "text-estimate-ink" : "text-ink-2";
  return (
    <span className={`inline-flex items-center gap-2 whitespace-nowrap text-sm font-medium capitalize ${t}`}>
      <span className={`h-2 w-2 rounded-[1px] ${c}`} aria-hidden />
      {level}
    </span>
  );
}

// ------------------------------------------------------------------ tables

export function Th({ children, right, className = "" }: { children?: ReactNode; right?: boolean; className?: string }) {
  return (
    <th
      className={`whitespace-nowrap border-b border-line-2 px-3 pb-2 pt-1 align-bottom font-mono text-[10.5px] font-medium uppercase tracking-[0.06em] text-ink-2 first:pl-0 last:pr-0 ${
        right ? "text-right" : "text-left"
      } ${className}`}
    >
      {children}
    </th>
  );
}
export function Td({ children, right, className = "" }: { children?: ReactNode; right?: boolean; className?: string }) {
  return (
    <td className={`border-b border-line px-3 py-2.5 align-top first:pl-0 last:pr-0 ${right ? "text-right [&>span]:justify-end" : ""} ${className}`}>
      {children}
    </td>
  );
}
export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="-mx-1 overflow-x-auto px-1">
      <table className="w-full border-collapse text-base [&_tbody_tr:last-child_td]:border-b-0 [&_tbody_tr]:transition-colors [&_tbody_tr:hover]:bg-sunken">
        {children}
      </table>
    </div>
  );
}

/** Error boundary: a stage view that crashes falls back to `fallback` (usually the generic renderer). */
export class Boundary extends Component<{ children: ReactNode; fallback: ReactNode; resetKey?: string }, { failed: boolean; key?: string }> {
  state: { failed: boolean; key?: string } = { failed: false, key: this.props.resetKey };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  static getDerivedStateFromProps(props: { resetKey?: string }, state: { failed: boolean; key?: string }) {
    if (props.resetKey !== state.key) return { failed: false, key: props.resetKey };
    return null;
  }
  componentDidCatch(error: unknown) {
    console.warn("Stage view fell back to the generic renderer:", error);
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

/** A row of key numbers on one white surface, separated by hairlines (no boxes per stat). */
export function StatStrip({ items, className = "" }: { items: { label: ReactNode; value: ReactNode; sub?: ReactNode; accent?: boolean }[]; className?: string }) {
  const cols = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4", 5: "sm:grid-cols-3 lg:grid-cols-5" }[items.length] ?? "sm:grid-cols-4";
  return (
    <div className={`grid overflow-hidden rounded-md border border-line bg-surface ${cols} ${className}`}>
      {items.map((it, i) => (
        <div key={i} className="relative -ml-px -mt-px border-l border-t border-line px-5 py-4">
          {it.accent && <span className="absolute left-0 right-0 top-0 h-[2px] bg-accent" aria-hidden />}
          <Stat label={it.label} sub={it.sub}>
            {it.value}
          </Stat>
        </div>
      ))}
    </div>
  );
}
