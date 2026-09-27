"use client";

import Link from "next/link";
import { Component, useState, type ReactNode } from "react";
import type { Assumption, Label, LabeledValue } from "@/types/contracts";
import { fmtValue, LABEL_DOT, LABEL_HELP, LABEL_INK, LABEL_TEXT, LAYER_CLASS, type Layer } from "@/lib/meta";

// ------------------------------------------------------------------ trust labels

/**
 * Trust label as a quiet coloured dot (W26). The full label and its source show in the tooltip (TipLayer);
 * screen readers get the label as text. `text` also prints the label next to the dot (legends, section headers).
 */
export function LabelBadge({ label, tip, small, text }: { label: Label | string; tip?: string | null; small?: boolean; text?: boolean }) {
  const l = (label in LABEL_TEXT ? label : "estimate") as Label;
  return (
    <span
      data-tip={tip ?? LABEL_HELP[l]}
      data-tip-label={l}
      className={`relative inline-flex shrink-0 cursor-help items-center gap-1.5 whitespace-nowrap align-middle font-sans font-normal normal-case tracking-normal ${
        text ? `${small ? "text-2xs" : "text-sm"} ${LABEL_INK[l]}` : "-m-1.5 p-1.5"
      }`}
    >
      <span className={`tdot ${LABEL_DOT[l]}`} aria-hidden />
      <span className={text ? "" : "sr-only"}>{LABEL_TEXT[l]}</span>
    </span>
  );
}

/** A LabeledValue: value + unit + trust dot; hovering the value shows the label and source_or_assumption. */
export function LV({ v, big, noBadge, className = "" }: { v: LabeledValue | null | undefined; big?: boolean; noBadge?: boolean; className?: string }) {
  if (!v) return <span className="text-ink-4">—</span>;
  return (
    <span className={`inline-flex items-center gap-x-1.5 ${className}`} data-tip={v.source_or_assumption} data-tip-label={v.label}>
      <span className={`font-mono tabular-nums ${big ? "text-xl font-medium tracking-tight" : ""}`}>{fmtValue(v)}</span>
      {!noBadge && <LabelBadge label={v.label} tip={v.source_or_assumption} small={!big} />}
    </span>
  );
}

export function LayerTag({ layer }: { layer: Layer }) {
  return (
    <span className={`inline-flex h-5 items-center rounded-full px-2 text-2xs font-medium ${LAYER_CLASS[layer]}`}>
      {layer}
    </span>
  );
}

// ------------------------------------------------------------------ structure

/** Uppercase micro-label header with a hairline; optional right-side content. */
export function SectionHeader({ title, right, className = "" }: { title: ReactNode; right?: ReactNode; className?: string }) {
  return (
    <div className={`flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2 pb-1 ${className}`}>
      <h3 className="text-base font-semibold tracking-[-0.01em] text-ink">{title}</h3>
      {right && <div className="flex flex-wrap items-center gap-2 text-sm text-ink-2">{right}</div>}
    </div>
  );
}

/**
 * A titled section (W26b): no box at all — a title and its content on paper, separated from the next section by space.
 * `fictional` marks simulated network records: a violet rule + the label as text, never hidden.
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
    <section className={`relative ${fictional ? "pl-4" : ""} ${className}`}>
      {fictional && <span className="absolute inset-y-1 left-0 w-[2px] rounded-full bg-fictional/50" aria-hidden />}
      {(title || fictional || right) && (
        <header className="flex min-h-9 flex-wrap items-center justify-between gap-x-3 gap-y-1 pb-1">
          <h3 className="text-md font-semibold tracking-[-0.01em] text-ink">{title}</h3>
          <div className="flex flex-wrap items-center gap-3 text-sm text-ink-2">
            {right}
            {fictional && <LabelBadge label="fictional" tip="Simulated network record — demo data" small text />}
          </div>
        </header>
      )}
      <div className={flush ? "" : "pt-1"}>{children}</div>
    </section>
  );
}

/** A key number with its label. */
export function Stat({ label, children, sub, accent }: { label: ReactNode; children: ReactNode; sub?: ReactNode; accent?: boolean }) {
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <span className="micro">{label}</span>
      <div className={accent ? "[&_.font-mono]:font-semibold" : ""}>{children}</div>
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
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-md bg-danger-soft px-4 py-3 text-sm text-danger">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
        <circle cx="8" cy="8" r="6.5" />
        <path d="M8 4.5v4M8 10.8v.2" strokeLinecap="round" />
      </svg>
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="rounded px-2 py-0.5 text-xs font-medium underline decoration-danger/30 underline-offset-4 transition-colors hover:decoration-danger">
          Retry
        </button>
      )}
    </div>
  );
}

/** Calm load failure (N3): after the automatic retries — one neutral line and a Retry action, never a red box. */
export function CouldntLoad({ what = "this", onRetry, className = "" }: { what?: string; onRetry: () => void; className?: string }) {
  return (
    <div role="status" className={`flex flex-wrap items-center gap-3 rounded-md bg-paper-2/60 px-4 py-3 text-sm text-ink-2 ${className}`}>
      <span className="flex-1">Couldn&rsquo;t load {what}. The rest of the project is fine.</span>
      <Btn size="sm" variant="secondary" onClick={onRetry}>
        Retry
      </Btn>
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
    <div className="flex items-start gap-3 rounded-md bg-estimate-soft px-4 py-2.5 text-sm text-estimate-ink" role="status">
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
    <div className="flex flex-col items-start gap-2 rounded-md bg-surface px-6 py-8">
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
    <div className="rounded-md bg-surface">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-md px-5 py-3 text-left transition-colors hover:bg-sunken"
      >
        <span className="text-base font-medium">
          Assumptions <span className="font-mono text-ink-3">{items.length}</span>
        </span>
        <Chevron open={open} />
      </button>
      {open && (
        <ul className="divide-y divide-line px-5 pb-2">
          {items.map((a) => (
            <li key={a.id} className="grid grid-cols-[150px_1fr] items-start gap-3 py-2.5 text-base">
              <span>
                <LabelBadge label={a.label} tip={a.source ?? undefined} small text />
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
  // Disabled is unmistakable (W26): a neutral grey fill, never a pale version of the enabled colour.
  const v = {
    primary: "bg-accent text-ink hover:bg-[#ff6a26] disabled:bg-paper-2 disabled:text-ink-3",
    ink: "bg-ink text-white hover:bg-[#2a2a2a] disabled:bg-paper-2 disabled:text-ink-3",
    secondary: "bg-surface text-ink shadow-[inset_0_0_0_1px_var(--color-line-2)] hover:bg-sunken hover:shadow-[inset_0_0_0_1px_var(--color-ink-4)] disabled:text-ink-3",
    ghost: "text-ink-2 hover:text-ink hover:bg-paper-2 disabled:text-ink-4 disabled:hover:bg-transparent",
  }[variant];
  const s = { sm: "h-7 px-2.5 text-sm gap-1.5", md: "h-8 px-3 text-sm gap-2", lg: "h-10 px-4 text-base gap-2" }[size];
  return `press inline-flex shrink-0 select-none items-center justify-center whitespace-nowrap rounded font-medium disabled:cursor-not-allowed ${s} ${v} ${className}`;
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
    <div role="radiogroup" aria-label={label} className="inline-flex rounded bg-paper-2 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={value === o.value}
          disabled={o.disabled}
          onClick={() => onChange(o.value)}
          className={`h-6 rounded-sm px-2.5 text-xs font-medium transition-[color,background-color,box-shadow] duration-150 disabled:opacity-40 ${
            value === o.value ? "bg-surface text-ink shadow-[0_1px_2px_rgb(17_17_17/0.08),0_0_0_1px_rgb(17_17_17/0.04)]" : "text-ink-2 hover:text-ink"
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
      className={`whitespace-nowrap border-b border-line px-3 pb-2 pt-1 align-bottom text-[12.5px] font-medium text-ink-3 first:pl-0 last:pr-0 ${
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

/** A row of key numbers on one white surface, grouped by space (no boxes per stat, no rules). */
export function StatStrip({ items, className = "" }: { items: { label: ReactNode; value: ReactNode; sub?: ReactNode; accent?: boolean }[]; className?: string }) {
  const cols = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4", 5: "sm:grid-cols-3 lg:grid-cols-5" }[items.length] ?? "sm:grid-cols-4";
  return (
    <div className={`grid gap-y-2 overflow-hidden rounded-md bg-surface px-1 py-2 ${cols} ${className}`}>
      {items.map((it, i) => (
        <div key={i} className="relative px-5 py-3">
          <Stat label={it.label} sub={it.sub} accent={it.accent}>
            {it.value}
          </Stat>
        </div>
      ))}
    </div>
  );
}
