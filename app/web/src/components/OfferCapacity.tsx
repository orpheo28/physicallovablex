"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Factory, ProcessType, RegisterFactoryRequest } from "@/types/contracts";
import { api, errorMessage } from "@/lib/api";
import { Btn, LabelBadge, Spinner } from "./ui";

const PROCESSES = ["injection_molding", "cnc", "sheet_metal", "die_casting", "extrusion", "pcba", "assembly", "other"] as const;
const LABEL: Record<string, string> = {
  injection_molding: "Injection molding",
  cnc: "CNC",
  sheet_metal: "Sheet metal",
  die_casting: "Die casting",
  extrusion: "Extrusion",
  pcba: "PCBA",
  assembly: "Assembly",
  other: "Other",
};

/**
 * "Offer your capacity" — the factory side of the production MCP (register_capacity).
 * Enabled only when the API exposes POST /factories (checked in /openapi.json); otherwise shown disabled.
 */
export function OfferCapacity({ onCreated }: { onCreated?: (f: Factory) => void }) {
  const [available, setAvailable] = useState<boolean | null>(null);
  const [procs, setProcs] = useState<ProcessType[]>(["injection_molding", "assembly"]);
  const [f, setF] = useState({ name: "", region: "", materials: "", moq: "1000", certifications: "", lead: "30", monthly: "20000", load: "50" });
  const [state, setState] = useState<{ busy?: boolean; created?: Factory; err?: string }>({});

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ paths?: Record<string, Record<string, unknown>> }>("/openapi.json")
      .then((o) => !cancelled && setAvailable(!!o.paths?.["/factories"]?.post))
      .catch(() => !cancelled && setAvailable(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const disabled = available !== true;
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF((s) => ({ ...s, [k]: e.target.value }));
  const list = (s: string) =>
    s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled) return;
    const num = (v: string) => Number(v.replace(/[^\d.]/g, ""));
    if (!f.name.trim() || !f.region.trim()) return setState({ err: "Add the factory name and its region." });
    if (procs.length === 0) return setState({ err: "Pick at least one process." });
    const body: RegisterFactoryRequest = {
      name: f.name.trim(),
      region: f.region.trim(),
      processes: procs as RegisterFactoryRequest["processes"],
      materials: list(f.materials),
      moq: num(f.moq),
      certifications: list(f.certifications),
      lead_time_days: num(f.lead),
      monthly_capacity: num(f.monthly),
      current_load_pct: num(f.load),
      archetype: "balanced",
      personality: null,
    };
    setState({ busy: true });
    try {
      const created = await api.post<Factory>("/factories", body);
      setState({ created });
      onCreated?.(created);
    } catch (err) {
      setState({ err: errorMessage(err) });
    }
  }

  const field = (k: keyof typeof f, label: string, { hint, mono, w }: { hint?: string; mono?: boolean; w?: string } = {}) => (
    <label key={k} className={`flex flex-col gap-1.5 ${w ?? ""}`}>
      <span className="micro">{label}</span>
      <input value={f[k]} onChange={set(k)} disabled={disabled} placeholder={hint} className={`field ${mono ? "font-mono" : ""}`} />
    </label>
  );

  return (
    <section aria-labelledby="offer-h" className="rounded-md border border-line bg-surface">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-6 py-4">
        <div>
          <h2 id="offer-h" className="text-md font-semibold tracking-[-0.01em]">
            Offer your capacity
          </h2>
          <p className="mt-0.5 text-base text-ink-2">Factories list what they can make, and any agent can ask for capacity and request a quote.</p>
        </div>
        {available === false && (
          <span className="inline-flex items-center gap-2 rounded-full bg-paper-2 px-2.5 py-1 text-sm text-ink-2">
            <span className="h-1.5 w-1.5 rounded-full bg-ink-4" aria-hidden />
            Coming via production MCP
          </span>
        )}
      </header>
      <form onSubmit={submit} className="grid gap-5 px-6 py-6 md:grid-cols-4">
        {field("name", "Factory name", { hint: "e.g. Harbor Tooling Co.", w: "md:col-span-2" })}
        {field("region", "Region", { hint: "e.g. Dongguan, CN", w: "md:col-span-2" })}
        <fieldset className="md:col-span-4" disabled={disabled}>
          <legend className="micro mb-2">Processes</legend>
          <div className="flex flex-wrap gap-2">
            {PROCESSES.map((p) => {
              const on = procs.includes(p);
              return (
                <button
                  key={p}
                  type="button"
                  aria-pressed={on}
                  onClick={() => setProcs((s) => (on ? s.filter((x) => x !== p) : [...s, p]))}
                  className={`h-7 rounded border px-2.5 text-sm transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${
                    on ? "border-ink bg-ink text-white" : "border-line-2 bg-surface hover:border-ink-4"
                  }`}
                >
                  {LABEL[p]}
                </button>
              );
            })}
          </div>
        </fieldset>
        {field("materials", "Materials", { hint: "PC/ABS, aluminium 6063", w: "md:col-span-2" })}
        {field("certifications", "Certifications", { hint: "ISO 9001, IATF 16949", w: "md:col-span-2" })}
        {field("moq", "MOQ (units)", { mono: true })}
        {field("lead", "Lead time (days)", { mono: true })}
        {field("monthly", "Monthly capacity", { mono: true })}
        {field("load", "Current load (%)", { mono: true })}
        <div className="flex flex-wrap items-center gap-3 md:col-span-4">
          <Btn type="submit" variant="primary" disabled={disabled || state.busy}>
            {state.busy && <Spinner />} Register capacity
          </Btn>
          {available === false && (
            <span className="text-sm text-ink-3">
              Not live in this demo: registration arrives with the production MCP (<span className="font-mono">register_capacity</span>).
            </span>
          )}
          {state.created && (
            <span className="flex flex-wrap items-center gap-2 text-sm text-ink-2" role="status">
              Registered
              <Link href={`/factories/${state.created.id}`} className="font-medium text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink">
                {state.created.name}
              </Link>
              <LabelBadge label="fictional" small />
              — it now answers capacity queries in the network.
            </span>
          )}
          {state.err && <span className="text-sm text-danger">Registration failed: {state.err}</span>}
        </div>
      </form>
    </section>
  );
}
