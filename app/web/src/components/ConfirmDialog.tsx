"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { Btn } from "./ui";

/** In-app confirmation (no native confirm()): title, one short body, Cancel + one action. Esc / backdrop cancel. */
export function ConfirmDialog({
  title,
  body,
  confirm,
  onConfirm,
  onCancel,
  tone = "ink",
}: {
  title: string;
  body: ReactNode;
  confirm: string;
  onConfirm: () => void;
  onCancel: () => void;
  tone?: "ink" | "primary";
}) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    box.current?.querySelector<HTMLButtonElement>("[data-confirm-wrap] button")?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <div ref={box} role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" className="w-full max-w-[440px] rounded-lg bg-surface p-6 shadow-float">
        <h2 id="confirm-title" className="text-md font-semibold tracking-[-0.01em]">
          {title}
        </h2>
        <div className="mt-2 text-base text-ink-2">{body}</div>
        <div className="mt-5 flex justify-end gap-2">
          <Btn variant="ghost" onClick={onCancel}>
            Cancel
          </Btn>
          <span data-confirm-wrap>
            <Btn variant={tone} onClick={onConfirm}>
              {confirm}
            </Btn>
          </span>
        </div>
      </div>
    </div>
  );
}
