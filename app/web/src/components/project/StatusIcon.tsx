import type { StageStatus } from "@/types/contracts";

export type StepState = "done" | "draft" | "current" | "running" | "todo";

export function stepState(status: StageStatus | string | undefined, opts: { active?: boolean; running?: boolean } = {}): StepState {
  if (opts.running) return "running";
  if (status === "validated") return "done";
  if (status === "draft") return "draft";
  return opts.active ? "current" : "todo";
}

const LABEL: Record<StepState, string> = {
  done: "Done — validated",
  draft: "Done — draft, not validated yet",
  current: "Current step",
  running: "Running now",
  todo: "To do",
};

/** Step status: done (ink check), draft (amber check), current (accent ring), running (accent ring + dot), to do (hollow ring). */
export function StatusIcon({ state, size = 16, quiet }: { state: StepState; size?: number; quiet?: boolean }) {
  const common = { width: size, height: size, viewBox: "0 0 16 16", "aria-label": LABEL[state], role: "img" as const };
  if (state === "done" || state === "draft")
    return (
      <svg {...common} className="shrink-0">
        <title>{LABEL[state]}</title>
        <circle cx="8" cy="8" r="7.25" fill={state === "done" ? (quiet ? "#8A8883" : "#111111") : "#FBF4E4"} stroke={state === "done" ? (quiet ? "#8A8883" : "#111111") : "#C98A0B"} strokeWidth="1.5" />
        <path
          data-check
          d="m4.8 8.3 2.2 2.1 4.3-4.6"
          fill="none"
          stroke={state === "done" ? "#FFFFFF" : "#8A5D00"}
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={1}
          strokeDasharray="1"
          strokeDashoffset="0"
        />
      </svg>
    );
  if (state === "current" || state === "running")
    return (
      <svg {...common} className="shrink-0">
        <title>{LABEL[state]}</title>
        <circle cx="8" cy="8" r="7" fill="#FFFFFF" stroke="#FF4F00" strokeWidth="1.5" />
        <circle cx="8" cy="8" r={state === "running" ? 3 : 2.25} fill="#FF4F00" />
      </svg>
    );
  return (
    <svg {...common} className="shrink-0">
      <title>{LABEL[state]}</title>
      <circle cx="8" cy="8" r="7" fill="none" stroke="#D6D3CC" strokeWidth="1.25" />
    </svg>
  );
}
