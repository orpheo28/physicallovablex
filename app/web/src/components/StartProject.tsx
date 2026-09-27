"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { CreateProjectRequest, Project, ProjectMode, StageResult } from "@/types/contracts";
import { api, errorMessage } from "@/lib/api";
import { autofillLabel, startAutorun, useAutofillMax, type Through } from "@/lib/autofill";
import { studioStart } from "@/lib/studio";
import { Chevron, ErrorBox, Spinner } from "./ui";

// The 7 flagship use cases (Studio), then PRD Appendix A — the 10 test prompts (under "More examples").
const FLAGSHIP: { text: string; mode: ProjectMode }[] = [
  { text: "A Whoop competitor for kitesurfers, screenless, 5-day battery", mode: "idea" },
  { text: "A simple, safe changing table for babies", mode: "idea" },
  { text: "A next-gen home robot that tidies toys", mode: "idea" },
  { text: "A cordless stick vacuum, Dyson alternative", mode: "idea" },
  { text: "Smart irrigation for a 30 m² garden", mode: "idea" },
  { text: "Solar panels sized for my roof in Biarritz", mode: "idea" },
  { text: "A hydrodynamic surfboard for beginners", mode: "idea" },
];
const TEST_PROMPTS: { text: string; mode: ProjectMode }[] = [
  { text: "Magnetic rechargeable desk lamp, minimalist, sold €89", mode: "idea" },
  { text: "Bluetooth tracker card for wallets", mode: "idea" },
  { text: "Smart dog bowl that weighs food, Wi-Fi", mode: "idea" },
  { text: "Mechanical keyboard with hot-swap switches, aluminium case", mode: "idea" },
  { text: "Portable espresso maker, manual pump, no electronics", mode: "idea" },
  { text: "Kids' audio player with NFC figurines", mode: "idea" },
  { text: "Smart ring measuring sleep", mode: "prototype" },
  { text: "E-ink phone, minimalist", mode: "prototype" },
  { text: "Bike light with brake detection", mode: "idea" },
  { text: "Desktop air-quality monitor with CO2 sensor", mode: "idea" },
];
const PROMPTS = [...FLAGSHIP, ...TEST_PROMPTS];

const BOM_PLACEHOLDER = `part, qty, manufacturer pn, notes
nRF52832 BLE SoC, 1, nRF52832-QFAA, main MCU
MAX30102 PPG sensor, 1, MAX30102EFD+, heart rate / SpO2
LiPo 22 mAh, 1, , custom ring cell
Ti shell, 1, , CNC titanium`;

/** A small popover menu anchored to a quiet text button (closes on outside click and Escape). */
export function useDismiss(open: boolean, close: () => void) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => !box.current?.contains(e.target as Node) && close();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open, close]);
  return box;
}

/** "All prompts": the full list of example prompts in a small popover (the page shows the flagship chips). */
function MoreExamples({ onPick }: { onPick: (p: { text: string; mode: ProjectMode }) => void }) {
  const [open, setOpen] = useState(false);
  const box = useDismiss(open, () => setOpen(false));
  return (
    <div ref={box} className="relative">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="press inline-flex h-8 items-center gap-1 rounded-full px-3 text-sm text-ink-3 hover:bg-paper-2 hover:text-ink"
      >
        All prompts <Chevron open={open} />
      </button>
      {open && (
        <ul role="listbox" aria-label="Example prompts" className="absolute right-0 top-10 z-40 max-h-[52vh] w-[420px] overflow-y-auto rounded-lg bg-surface p-1.5 shadow-float">
          {PROMPTS.map((p, i) => (
            <li key={p.text} className={i === FLAGSHIP.length ? "mt-1.5 border-t border-line pt-1.5" : ""}>
              <button
                type="button"
                onClick={() => {
                  onPick(p);
                  setOpen(false);
                }}
                className="flex w-full items-center justify-between gap-3 rounded-sm px-3 py-2 text-left text-sm text-ink transition-colors hover:bg-paper"
              >
                {p.text}
                {p.mode === "prototype" && <span className="text-2xs text-ink-3">prototype</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** "More ways to start": autofill all steps, or go step by step (the Studio is the default, Enter). */
function MoreWays({ label, onPick, disabled }: { label: string; onPick: (p: "autofill" | "steps") => void; disabled: boolean }) {
  const [open, setOpen] = useState(false);
  const box = useDismiss(open, () => setOpen(false));
  const items: { id: "autofill" | "steps"; title: string; sub: string }[] = [
    { id: "autofill", title: label, sub: "Runs every step with sensible defaults, then opens the overview." },
    { id: "steps", title: "Go step by step", sub: "Starts with the brief; you run and check each step." },
  ];
  return (
    <div ref={box} className="relative">
      <button
        type="button"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className="press inline-flex h-8 items-center gap-1 rounded-full px-3 text-sm text-ink-2 hover:bg-paper-2 hover:text-ink disabled:opacity-45"
      >
        More ways to start <Chevron open={open} />
      </button>
      {open && (
        <div className="absolute left-0 top-10 z-40 w-[340px] rounded-lg bg-surface p-1.5 shadow-float">
          {items.map((i) => (
            <button
              key={i.id}
             
              type="button"
              onClick={() => {
                setOpen(false);
                onPick(i.id);
              }}
              className="flex w-full flex-col items-start gap-0.5 rounded-sm px-3 py-2 text-left transition-colors hover:bg-paper"
            >
              <span className="text-sm font-medium text-ink">{i.title}</span>
              <span className="text-2xs text-ink-3">{i.sub}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

type Plan = "studio" | "autofill" | "steps";

/**
 * Start a project: idea / prototype, prompt (+ BOM), example prompts. Reads ?mode= and ?prompt= to pre-fill.
 * Primary: autofill all 13 steps (POST /autorun?through=13, then the stepper). Secondary: steps 1-7. Or step by step.
 */
export function StartProject({ title = "What do you want to make?" }: { title?: string }) {
  const router = useRouter();
  const sp = useSearchParams();
  const max = useAutofillMax();
  const [mode, setMode] = useState<ProjectMode>(sp.get("mode") === "prototype" ? "prototype" : "idea");
  const [prompt, setPrompt] = useState(sp.get("prompt") ?? "");
  const [bom, setBom] = useState("");
  const [step, setStep] = useState<null | "create" | "brief" | "autorun" | "studio">(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(plan: Plan) {
    if (!prompt.trim()) {
      setError("Describe your product first.");
      return;
    }
    setError(null);
    try {
      setStep("create");
      const body: CreateProjectRequest = { mode, prompt: prompt.trim(), pasted_bom: mode === "prototype" && bom.trim() ? bom.trim() : null, name: null, example: null };
      const project = await api.post<Project>("/projects", body);
      if (plan === "studio") {
        setStep("studio");
        await studioStart(project.id);
        router.push(`/projects/${project.id}/studio`);
        return;
      }
      if (plan === "autofill") {
        const through: Through = max;
        setStep("autorun");
        await startAutorun(project.id, through);
        router.push(`/projects/${project.id}?autorun=${through}`);
        return;
      }
      setStep("brief");
      try {
        await api.post<StageResult>(`/projects/${project.id}/stages/1/run`, { inputs: {} });
      } catch {
        // The stage page shows step 1 with its own Run button if this failed.
      }
      router.push(`/projects/${project.id}?stage=1`);
    } catch (e) {
      setError(errorMessage(e));
      setStep(null);
    }
  }

  const busy = step !== null;
  const pick = (p: { text: string; mode: ProjectMode }) => {
    setPrompt(p.text);
    setMode(p.mode);
  };

  const ready = !!prompt.trim() && !busy;

  return (
    <div className="flex w-full flex-col items-center text-center">
      <h1 className="font-display text-[clamp(44px,7.4vh,72px)] font-semibold uppercase leading-[0.95] text-balance">{title}</h1>
      <p className="mt-3 max-w-[560px] text-md text-ink-2 text-pretty">
        {mode === "idea"
          ? "Describe it in a sentence. Get a 3D model, its cost and a factory shortlist, then change anything by asking."
          : "Paste your BOM. We check what will slow your first production run."}
      </p>

      <form
        className="mt-[clamp(18px,3.4vh,32px)] w-full max-w-[760px] text-left"
        onSubmit={(e) => {
          e.preventDefault();
          submit("studio");
        }}
      >
        <div className="rounded-lg bg-surface shadow-float transition-shadow duration-150 focus-within:shadow-[0_0_0_1px_rgb(17_17_17/0.18),0_2px_4px_rgb(17_17_17/0.04),0_12px_32px_-12px_rgb(17_17_17/0.18)]">
          <label className="block">
            <span className="sr-only">{mode === "idea" ? "Your product, in a sentence" : "Your prototype"}</span>
            <textarea
              name="prompt"
              autoComplete="off"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  submit("studio");
                }
              }}
              rows={2}
              placeholder={mode === "idea" ? "A Whoop competitor for kitesurfers, screenless, 5-day battery…" : "Smart ring measuring sleep, working prototype, 20 pre-orders…"}
              className="block w-full resize-none rounded-t-lg bg-transparent px-5 pb-1 pt-4 text-lg leading-7 text-ink outline-none placeholder:text-ink-3 focus-visible:outline-none"
            />
          </label>
          {mode === "prototype" && (
            <label className="mx-5 mt-1 block border-t border-line pt-2">
              <span className="text-2xs text-ink-3">Your BOM: CSV, spreadsheet rows or plain text</span>
              <textarea
                name="bom"
                autoComplete="off"
                value={bom}
                onChange={(e) => setBom(e.target.value)}
                rows={4}
                placeholder={BOM_PLACEHOLDER}
                className="mt-1 block w-full resize-none bg-transparent font-mono text-sm leading-5 text-ink outline-none placeholder:text-ink-4 focus-visible:outline-none"
              />
            </label>
          )}
          <div className="flex items-center gap-1 px-3 pb-3 pt-1">
            <div role="radiogroup" aria-label="Starting point" className="inline-flex rounded-full bg-paper-2/70 p-0.5">
              {(["idea", "prototype"] as ProjectMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  role="radio"
                  aria-checked={mode === m}
                  onClick={() => setMode(m)}
                  className={`h-7 rounded-full px-3 text-sm transition-[color,background-color,box-shadow] duration-150 ${
                    mode === m ? "bg-surface font-medium text-ink shadow-[0_1px_2px_rgb(17_17_17/0.1)]" : "text-ink-2 hover:text-ink"
                  }`}
                >
                  {m === "idea" ? "Idea" : "Prototype"}
                </button>
              ))}
            </div>
            <MoreWays label={autofillLabel(max)} onPick={submit} disabled={busy} />
            <span className="ml-auto" />
            <button
              type="submit"
              aria-label="Start designing"
              disabled={!ready}
              className={`press flex h-9 w-9 items-center justify-center rounded-full ${ready ? "bg-accent text-ink hover:bg-[#ff6a26]" : "bg-paper-2 text-ink-4"} disabled:cursor-not-allowed`}
            >
              {busy ? (
                <Spinner />
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
                  <path d="M8 13V3M3.5 7.5 8 3l4.5 4.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          </div>
        </div>
        <p className="mt-2 min-h-5 px-1 text-center text-sm text-ink-2" role="status" aria-live="polite">
          {step === "create" && "Creating the project…"}
          {step === "brief" && "Writing the brief (step 1)…"}
          {step === "autorun" && "Starting autofill…"}
          {step === "studio" && "Opening the Studio. The first version takes about 30 s…"}
        </p>
        {error && (
          <div className="mt-1">
            <ErrorBox message={error} />
          </div>
        )}
      </form>

      <div className="mt-1 flex w-full max-w-[1080px] flex-wrap items-center justify-center gap-2">
        {FLAGSHIP.slice(0, 3).map((p) => (
          <button
            key={p.text}
            type="button"
            onClick={() => pick(p)}
            className={`press h-8 rounded-full px-3.5 text-sm ${prompt === p.text ? "bg-ink text-white" : "bg-paper-2/80 text-ink-2 hover:bg-paper-2 hover:text-ink"}`}
          >
            {p.text}
          </button>
        ))}
        <MoreExamples onPick={pick} />
      </div>
    </div>
  );
}
