"use client";

import type { ReactNode } from "react";
import { humanize, isLabeledValue } from "@/lib/meta";
import { Boundary, LabelBadge, LV } from "./ui";

const SKIP = new Set(["project_id", "status", "fallback", "fallback_reason", "generated_by", "generated_at", "assumptions", "stage", "label", "fictional"]);

function isFictionalRecord(o: Record<string, unknown>) {
  return o.label === "fictional" && !isLabeledValue(o);
}

/** Walks any JSON value. LabeledValues get their badge; fictional records are badged as a whole. Never throws. */
export function Generic(props: { value: unknown; depth?: number; skipKeys?: boolean }) {
  return (
    <Boundary fallback={<span className="text-ink-4">(unreadable value)</span>}>
      <GenericInner {...props} />
    </Boundary>
  );
}

function GenericInner({ value, depth = 0, skipKeys = true }: { value: unknown; depth?: number; skipKeys?: boolean }): ReactNode {
  {
    if (value === null || value === undefined) return <span className="text-ink-4">—</span>;
    if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
    if (typeof value === "number") return <span className="font-mono tabular-nums">{value.toLocaleString("en-US")}</span>;
    if (typeof value === "string") {
      if (/^(https?:\/\/|\/files\/)/.test(value))
        return (
          <a className="break-all text-ink underline decoration-line-2 underline-offset-4" href={value.startsWith("/") ? `/backend${value}` : value} target="_blank" rel="noreferrer">
            {value}
          </a>
        );
      return <span className="whitespace-pre-wrap">{value}</span>;
    }
    if (isLabeledValue(value)) return <LV v={value} />;
    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-ink-4">none</span>;
      if (value.every((x) => typeof x !== "object" || x === null))
        return <span>{value.map((x) => String(x)).join(", ")}</span>;
      return (
        <ul className="flex flex-col gap-2">
          {value.map((x, i) => (
            <li key={i} className="rounded-sm bg-sunken p-3">
              <GenericInner value={x} depth={depth + 1} skipKeys={false} />
            </li>
          ))}
        </ul>
      );
    }
    if (typeof value === "object") {
      const o = value as Record<string, unknown>;
      const entries = Object.entries(o).filter(([k]) => !(SKIP.has(k) && (skipKeys || k === "label" || k === "fictional")));
      const body = (
        <dl className={`grid gap-x-4 gap-y-1.5 ${depth === 0 ? "sm:grid-cols-[minmax(140px,max-content)_1fr]" : "sm:grid-cols-[minmax(110px,max-content)_1fr]"}`}>
          {entries.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="micro sm:pt-0.5">{humanize(k)}</dt>
              <dd className="text-base">
                <GenericInner value={v} depth={depth + 1} skipKeys={false} />
              </dd>
            </div>
          ))}
        </dl>
      );
      if (isFictionalRecord(o))
        return (
          <div className="relative rounded-sm border border-line py-2 pl-4 pr-2">
            <span className="absolute inset-y-0 left-0 w-[2px] bg-fictional/50" aria-hidden />
            <div className="mb-1 flex justify-end">
              <LabelBadge label="fictional" tip="Simulated network record — demo data" small />
            </div>
            {body}
          </div>
        );
      return body;
    }
    return <span>{String(value)}</span>;
  }
}
