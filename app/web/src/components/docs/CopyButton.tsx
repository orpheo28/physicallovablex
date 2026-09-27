"use client";

import { useState } from "react";

export function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1800);
        } catch {
          setDone(false);
        }
      }}
      className="rounded-sm border border-line-2 bg-surface px-2 py-0.5 font-sans text-2xs font-medium text-ink-2 transition-colors hover:border-ink-4 hover:text-ink"
    >
      {done ? "Copied" : "Copy"}
    </button>
  );
}
