"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { CreateProjectRequest, Project, ProjectMode, StageResult } from "@/types/contracts";
import { api, errorMessage } from "@/lib/api";
import { Btn, ErrorBox, Spinner } from "./ui";

// PRD Appendix A — the 10 test prompts.
const PROMPTS: { text: string; mode: ProjectMode }[] = [
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

const BOM_PLACEHOLDER = `part, qty, manufacturer pn, notes
nRF52832 BLE SoC, 1, nRF52832-QFAA, main MCU
MAX30102 PPG sensor, 1, MAX30102EFD+, heart rate / SpO2
LiPo 22 mAh, 1, , custom ring cell
Ti shell, 1, , CNC titanium`;

/** Start a project: idea / prototype, prompt (+ BOM), the 10 test prompts. Reads ?mode= and ?prompt= to pre-fill. */
export function StartProject({ title = "Start a project" }: { title?: string }) {
  const router = useRouter();
  const sp = useSearchParams();
  const [mode, setMode] = useState<ProjectMode>(sp.get("mode") === "prototype" ? "prototype" : "idea");
  const [prompt, setPrompt] = useState(sp.get("prompt") ?? "");
  const [bom, setBom] = useState("");
  const [step, setStep] = useState<null | "create" | "brief">(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!prompt.trim()) {
      setError("Describe your product first.");
      return;
    }
    setError(null);
    try {
      setStep("create");
      const body: CreateProjectRequest = { mode, prompt: prompt.trim(), pasted_bom: mode === "prototype" && bom.trim() ? bom.trim() : null, name: null, example: null };
      const project = await api.post<Project>("/projects", body);
      setStep("brief");
      try {
        await api.post<StageResult>(`/projects/${project.id}/stages/1/run`, { inputs: {} });
      } catch {
        // The dashboard shows stage 1 with its own Run button if this failed.
      }
      router.push(`/projects/${project.id}?stage=1`);
    } catch (e) {
      setError(errorMessage(e));
      setStep(null);
    }
  }

  const busy = step !== null;

  return (
    <div className="max-w-[760px]">
      <h1 className="font-display text-[34px] font-semibold uppercase leading-[36px]">{title}</h1>
      <p className="mt-2 text-md text-ink-2">
        {mode === "idea"
          ? "Describe it in a sentence. Get the product, its cost and a factory shortlist in about a minute (measured on 10 test prompts)."
          : "Paste your BOM. We check what will slow your first production run."}
      </p>

      <div className="mt-8">
        <div role="radiogroup" aria-label="Starting point" className="inline-flex rounded border border-line-2 bg-surface p-0.5">
          {(["idea", "prototype"] as ProjectMode[]).map((m) => (
            <button
              key={m}
              role="radio"
              aria-checked={mode === m}
              onClick={() => setMode(m)}
              className={`h-8 rounded-sm px-4 text-sm font-medium transition-colors duration-150 ${mode === m ? "bg-ink text-white" : "text-ink-2 hover:text-ink"}`}
            >
              {m === "idea" ? "I have an idea" : "I have a prototype"}
            </button>
          ))}
        </div>
      </div>

      <form
        className="mt-5 flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label className="flex flex-col gap-2">
          <span className="sr-only">{mode === "idea" ? "Your product, in a sentence" : "Your prototype"}</span>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
            }}
            rows={3}
            placeholder={mode === "idea" ? "e.g. Smart dog bowl that weighs food, Wi-Fi" : "e.g. Smart ring measuring sleep — working prototype, 20 pre-orders"}
            className="field !px-4 !py-3 !text-lg !leading-7"
          />
        </label>
        {mode === "prototype" && (
          <label className="flex flex-col gap-2">
            <span className="micro">Your BOM — CSV, spreadsheet rows or plain text</span>
            <textarea value={bom} onChange={(e) => setBom(e.target.value)} rows={7} placeholder={BOM_PLACEHOLDER} className="field font-mono !text-sm" />
          </label>
        )}
        <div>
          <p className="text-sm text-ink-3">Or try an example prompt</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {PROMPTS.map((p) => (
              <button
                key={p.text}
                type="button"
                onClick={() => {
                  setPrompt(p.text);
                  setMode(p.mode);
                }}
                className={`h-7 rounded border px-2.5 text-sm transition-colors duration-150 ${
                  prompt === p.text ? "border-ink bg-ink text-white" : "border-line-2 bg-surface text-ink-2 hover:border-ink-4 hover:text-ink"
                }`}
              >
                {p.text}
                {p.mode === "prototype" && <span className={prompt === p.text ? "ml-1.5 text-white/60" : "ml-1.5 text-ink-3"}>prototype</span>}
              </button>
            ))}
          </div>
        </div>
        {error && <ErrorBox message={error} />}
        <div className="flex flex-wrap items-center gap-4">
          <Btn type="submit" variant="primary" size="lg" disabled={busy}>
            {busy && <Spinner />}
            {mode === "idea" ? "Start from the idea" : "Check my prototype"}
          </Btn>
          {step === "create" && <span className="text-base text-ink-2">Creating the project…</span>}
          {step === "brief" && <span className="text-base text-ink-2">Writing the brief (stage 1)…</span>}
        </div>
      </form>
    </div>
  );
}
