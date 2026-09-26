"use client";

import { useState } from "react";
import type { BriefArtifact, DesignArtifact, DesignDirection, Dimensions, LabeledValue, SpecArtifact, SpecPart, StageResult, ElectronicsBlock, ElectronicsEdge } from "@/types/contracts";
import { api, fileUrl } from "@/lib/api";
import { useFileExists } from "@/lib/useApi";
import { directionGlb, directionRender } from "@/lib/assets";
import { humanize } from "@/lib/meta";
import { BOMTable, DimsView, FileLink, PartsTable } from "../blocks";
import { ModelViewer } from "../ModelViewer";
import { RetryImg } from "../RetryImg";
import { Btn, Card, KV, LabelBadge, LV, Pill, Segmented, Spinner, Table, Td, Th } from "../ui";
import type { StageViewProps } from "./types";

// ---------------------------------------------------------------- Stage 1
export function BriefView({ artifact: a, busy, run, onAutorun }: StageViewProps<BriefArtifact>) {
  const questions = a.clarifying_questions ?? [];
  const [answers, setAnswers] = useState<Record<string, string>>(() =>
    Object.fromEntries(questions.filter((q) => q.answer).map((q) => [q.id, q.answer as string])),
  );
  const [skipped, setSkipped] = useState<Record<string, boolean>>({});
  const set = (id: string, v: string) => {
    setAnswers((s) => ({ ...s, [id]: v }));
    setSkipped((s) => ({ ...s, [id]: false }));
  };
  const pending = questions.filter((q) => !q.answer && !q.skipped).length;

  return (
    <div className="flex flex-col gap-6">
      <Card title={a.product_name} right={<Pill>{a.mode === "prototype" ? "Prototype mode" : "Idea mode"}</Pill>}>
        <p className="max-w-[64ch] text-lg tracking-[-0.01em]">{a.one_liner}</p>
        <p className="mt-2 text-sm text-ink-3">Prompt: &ldquo;{a.prompt}&rdquo;</p>
        <div className="mt-6 grid gap-x-8 gap-y-5 border-t border-line pt-5 sm:grid-cols-2 lg:grid-cols-3">
          <KV k="Category">{a.category}</KV>
          <KV k="Target markets">{a.target_markets.join(", ") || "—"}</KV>
          <KV k="Target retail price">
            <LV v={a.target_retail_price} />
          </KV>
          <KV k="Volume tiers">
            <span className="font-mono">{a.target_volumes.map((v) => v.toLocaleString("en-US")).join(" / ")}</span> units
          </KV>
          <KV k="Battery">{a.has_battery ? "Yes" : "No"}</KV>
          <KV k="Wireless">{a.wireless.length ? a.wireless.join(", ") : "None"}</KV>
        </div>
        <div className="mt-6 grid gap-8 border-t border-line pt-5 md:grid-cols-2">
          <KV k="Key features">
            <ul className="mt-1 flex flex-col gap-1">
              {a.key_features.map((f) => (
                <li key={f} className="flex gap-2.5">
                  <span className="mt-[9px] h-px w-2.5 shrink-0 bg-ink-3" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
          </KV>
          <KV k="Constraints">
            <ul className="mt-1 flex flex-col gap-1">
              {a.constraints.map((f) => (
                <li key={f} className="flex gap-2.5">
                  <span className="mt-[9px] h-px w-2.5 shrink-0 bg-ink-3" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
          </KV>
        </div>
      </Card>

      {a.pasted_bom?.length > 0 && (
        <Card title="Pasted BOM (prototype)">
          <BOMTable items={a.pasted_bom} />
        </Card>
      )}

      <Card
        title={
          <>
            Clarifying questions <span className="font-mono text-ink-3">{questions.length}</span>
            <span className="ml-2 text-sm font-normal text-ink-3">All optional</span>
          </>
        }
        right={pending > 0 ? <Pill tone="amber" dot>{pending} open</Pill> : undefined}
      >
        {questions.length === 0 ? (
          <p className="text-base text-ink-3">No clarifying questions for this brief.</p>
        ) : (
          <div className="flex flex-col">
            {questions.map((q) => (
              <div key={q.id} className={`flex flex-col gap-3 border-b border-line py-4 first:pt-0 transition-opacity duration-150 ${skipped[q.id] ? "opacity-45" : ""}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-base font-medium">{q.question}</span>
                  <span className="text-sm text-ink-3">{humanize(q.topic)}</span>
                  {q.skipped && !answers[q.id] && <Pill>skipped</Pill>}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {q.options.map((o) => (
                    <button
                      key={o}
                      onClick={() => set(q.id, o)}
                      aria-pressed={answers[q.id] === o}
                      className={`h-7 rounded border px-2.5 text-sm transition-colors duration-150 ${
                        answers[q.id] === o ? "border-ink bg-ink text-white" : "border-line-2 bg-surface text-ink hover:border-ink-4"
                      }`}
                    >
                      {o}
                    </button>
                  ))}
                  <input
                    value={answers[q.id] && !q.options.includes(answers[q.id]) ? answers[q.id] : ""}
                    onChange={(e) => set(q.id, e.target.value)}
                    placeholder="Other…"
                    aria-label={`Other answer to: ${q.question}`}
                    className="field !h-7 !w-44 !py-0 !text-sm"
                  />
                  <button
                    onClick={() => {
                      setSkipped((s) => ({ ...s, [q.id]: true }));
                      setAnswers((s) => {
                        const n = { ...s };
                        delete n[q.id];
                        return n;
                      });
                    }}
                    className="px-1 text-sm text-ink-3 underline decoration-line-2 underline-offset-4 hover:text-ink"
                  >
                    Skip
                  </button>
                </div>
              </div>
            ))}
            <div className="flex flex-wrap items-center gap-2 pt-5">
              <Btn variant="primary" disabled={busy} onClick={() => run({ answers })}>
                {busy && <Spinner />} Update brief with answers
              </Btn>
              <Btn variant="ghost" onClick={onAutorun} disabled={busy}>
                Skip questions, autorun stages 2–7
              </Btn>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------- Stage 2
type RenderState = "idle" | "busy" | "unavailable";

function DirectionMedia({ projectId, d }: { projectId: string; d: DesignDirection }) {
  const [renderUrl, setRenderUrl] = useState<string | null>(directionRender(d));
  const [state, setState] = useState<RenderState>("idle");
  const render = fileUrl(renderUrl);
  const { ok: hasRender, checking } = useFileExists(render);
  const [view, setView] = useState<"render" | "3d">("render");
  const v = hasRender ? view : "3d";

  async function generate() {
    setState("busy");
    try {
      const r = await api.post<StageResult>(`/projects/${projectId}/stages/2/render?direction_id=${encodeURIComponent(d.id)}`);
      const url = (r.artifact as DesignArtifact).directions.find((x) => x.id === d.id)?.render_url ?? null;
      if (url) {
        setRenderUrl(url);
        setView("render");
        setState("idle");
      } else setState("unavailable");
    } catch {
      setState("unavailable");
    }
  }

  return (
    <div className="relative bg-paper-2/50">
      {checking && render ? (
        <div className="h-[260px]" />
      ) : v === "render" && render ? (
        <figure className="relative h-[260px]">
          <RetryImg
            src={render}
            alt={`${d.name}, concept render`}
            className="h-full w-full object-cover"
            fallback={<ModelViewer url={directionGlb(projectId, d)} alt={d.name} height={260} />}
          />
          <figcaption className="absolute bottom-2.5 left-2.5 rounded-sm bg-surface/90 px-1.5 py-0.5 text-[10.5px] font-medium text-ink-2">
            AI concept render — illustrative, not the CAD
          </figcaption>
        </figure>
      ) : (
        <div className="relative">
          <ModelViewer url={directionGlb(projectId, d)} alt={d.name} height={260} />
          {!hasRender && (
            <div className="absolute inset-x-2.5 bottom-2.5 flex items-center justify-between gap-2">
              {state === "unavailable" ? (
                <span role="status" className="rounded-sm bg-surface/90 px-1.5 py-0.5 text-[10.5px] font-medium text-ink-2">
                  Render unavailable — 3D shown instead
                </span>
              ) : (
                <Btn size="sm" variant="secondary" onClick={generate} disabled={state === "busy"}>
                  {state === "busy" ? <Spinner /> : null}
                  {state === "busy" ? "Rendering…" : "Generate concept render"}
                </Btn>
              )}
            </div>
          )}
        </div>
      )}
      {hasRender && (
        <div className="absolute right-2.5 top-2.5">
          <Segmented
            label={`${d.name} view`}
            value={v}
            onChange={setView}
            options={[
              { value: "render", label: "Render" },
              { value: "3d", label: "3D" },
            ]}
          />
        </div>
      )}
    </div>
  );
}

export function DesignView({ artifact: a, busy, save, runOther }: StageViewProps<DesignArtifact>) {
  const [picking, setPicking] = useState<string | null>(null);
  async function pick(id: string) {
    setPicking(id);
    try {
      await save({ ...a, chosen_direction_id: id });
      await runOther(3, { direction_id: id });
    } finally {
      setPicking(null);
    }
  }
  return (
    <div className="grid gap-5 lg:grid-cols-3">
      {a.directions.map((d, i) => {
        const chosen = a.chosen_direction_id === d.id;
        return (
          <section
            key={d.id}
            className={`flex flex-col overflow-hidden rounded-md border bg-surface transition-colors duration-150 ${chosen ? "border-ink" : "border-line hover:border-line-2"}`}
          >
            <DirectionMedia projectId={a.project_id} d={d} />
            <div className="flex flex-1 flex-col gap-4 border-t border-line p-5">
              <div className="flex items-center justify-between gap-2">
                <h3 className="flex items-baseline gap-2.5 text-lg font-semibold tracking-[-0.015em]">
                  <span className="font-mono text-sm font-normal text-ink-3">{String.fromCharCode(65 + i)}</span>
                  {d.name}
                </h3>
                {chosen && <Pill tone="accent" dot>Chosen</Pill>}
              </div>
              <p className="text-base text-ink-2">{d.description}</p>
              <dl className="grid grid-cols-[88px_1fr] gap-x-3 gap-y-2 border-t border-line pt-4 text-base">
                <dt className="text-ink-3">Shape</dt>
                <dd>{d.shape}</dd>
                <dt className="text-ink-3">Material</dt>
                <dd>{d.material}</dd>
                <dt className="text-ink-3">Finish</dt>
                <dd>{d.finish}</dd>
                <dt className="text-ink-3">Size</dt>
                <dd>
                  <DimsView d={d.dimensions} />
                </dd>
              </dl>
              <div className="mt-auto pt-2">
                <Btn variant={chosen ? "ghost" : "secondary"} disabled={busy || picking !== null} onClick={() => pick(d.id)} className={chosen ? "-ml-3" : ""}>
                  {picking === d.id && <Spinner />}
                  {chosen ? "Re-generate CAD from this direction" : "Pick this direction"}
                </Btn>
              </div>
            </div>
          </section>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------- Stage 3
export function BlockDiagram({ blocks, edges, functional }: { blocks: ElectronicsBlock[]; edges: ElectronicsEdge[]; functional?: boolean }) {
  if (!blocks.length) return <p className="text-base text-ink-3">{functional ? "No functional blocks listed." : "No electronics in this product."}</p>;
  // Order blocks by depth (longest path from a source, cycle-safe), then let them wrap.
  const depth: Record<string, number> = Object.fromEntries(blocks.map((b) => [b.id, 0]));
  for (let i = 0; i < blocks.length; i++)
    for (const e of edges) if (e.source in depth && e.target in depth) depth[e.target] = Math.max(depth[e.target], Math.min(depth[e.source] + 1, blocks.length));
  const ordered = [...blocks].sort((x, y) => depth[x.id] - depth[y.id]);
  const name = (id: string) => blocks.find((b) => b.id === id)?.name ?? id;
  return (
    <div className="flex flex-col gap-5">
      <ol className="grid grid-cols-[repeat(auto-fill,minmax(184px,1fr))] gap-3" aria-label={functional ? "Functional blocks" : "Electronics blocks"}>
        {ordered.map((b) => {
          const links = edges.filter((e) => e.source === b.id || e.target === b.id).length;
          return (
            <li key={b.id} className="flex flex-col gap-1 rounded-sm border border-line-2 bg-surface px-3 py-2.5" title={b.function}>
              <span className="flex items-center justify-between font-mono text-2xs text-ink-3">
                {b.id}
                {links > 0 && <span>{links} link{links > 1 ? "s" : ""}</span>}
              </span>
              <span className="text-base font-medium leading-5">{b.name}</span>
              <span className="text-sm text-ink-2">{b.function}</span>
            </li>
          );
        })}
      </ol>
      {edges.length > 0 && (
        <div>
          <p className="micro border-b border-line-2 pb-2">{functional ? "Links" : "Signals"}</p>
          <ul className="grid gap-x-8 sm:grid-cols-2">
            {edges.map((e, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-x-2 border-b border-line py-2 text-base">
                <span>{name(e.source)}</span>
                <span className="text-ink-4" aria-label="to">
                  →
                </span>
                <span>{name(e.target)}</span>
                <span className="ml-auto font-mono text-sm text-ink-2">{e.signal}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- Stage 3 — editable spec
/** A user edit turns a number into an Estimate that says where it came from. */
function editLV(v: LabeledValue, raw: string): LabeledValue {
  const n = parseFloat(raw.replace(",", "."));
  if (!Number.isFinite(n) || n === v.value) return v;
  return { ...v, value: n, label: "estimate", source_or_assumption: `Edited by you (was ${v.value} ${v.unit}; ${v.source_or_assumption})` };
}

function NumIn({ v, onChange, label, w = "w-20" }: { v: LabeledValue; onChange: (v: LabeledValue) => void; label: string; w?: string }) {
  const [raw, setRaw] = useState(String(v.value));
  return (
    <span className="inline-flex items-center gap-1">
      <input
        aria-label={label}
        inputMode="decimal"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        onBlur={() => onChange(editLV(v, raw))}
        className={`field !h-7 !px-2 !py-0 text-right font-mono !text-sm ${w}`}
      />
      <span className="text-sm text-ink-3">{v.unit}</span>
    </span>
  );
}

function DimsIn({ d, onChange, label }: { d: Dimensions; onChange: (d: Dimensions) => void; label: string }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      <NumIn w="w-16" label={`${label} length`} v={d.length} onChange={(length) => onChange({ ...d, length })} />
      <span className="text-ink-4">×</span>
      <NumIn w="w-16" label={`${label} width`} v={d.width} onChange={(width) => onChange({ ...d, width })} />
      <span className="text-ink-4">×</span>
      <NumIn w="w-16" label={`${label} height`} v={d.height} onChange={(height) => onChange({ ...d, height })} />
    </span>
  );
}

function PartsEditor({ parts, onChange }: { parts: SpecPart[]; onChange: (p: SpecPart[]) => void }) {
  const upd = (i: number, patch: Partial<SpecPart>) => onChange(parts.map((p, j) => (j === i ? { ...p, ...patch } : p)));
  return (
    <Table>
      <thead>
        <tr>
          <Th>Part</Th>
          <Th>Material</Th>
          <Th>Finish</Th>
          <Th>Dimensions (L × W × H)</Th>
          <Th>Wall</Th>
          <Th>Tolerance</Th>
        </tr>
      </thead>
      <tbody>
        {parts.map((p, i) => (
          <tr key={p.id}>
            <Td className="min-w-[140px]">
              <span className="font-medium">{p.name}</span>
              <div className="font-mono text-2xs text-ink-3">{p.id}</div>
            </Td>
            <Td>
              <input aria-label={`${p.name} material`} value={p.material} onChange={(e) => upd(i, { material: e.target.value })} className="field !h-7 !py-0 !text-sm min-w-[150px]" />
            </Td>
            <Td>
              <input aria-label={`${p.name} finish`} value={p.finish} onChange={(e) => upd(i, { finish: e.target.value })} className="field !h-7 !py-0 !text-sm min-w-[150px]" />
            </Td>
            <Td>{p.dimensions ? <DimsIn label={p.name} d={p.dimensions} onChange={(dimensions) => upd(i, { dimensions })} /> : <span className="text-ink-4">—</span>}</Td>
            <Td>
              {p.wall_thickness ? (
                <NumIn w="w-16" label={`${p.name} wall thickness`} v={p.wall_thickness} onChange={(wall_thickness) => upd(i, { wall_thickness })} />
              ) : (
                <span className="text-ink-4">—</span>
              )}
            </Td>
            <Td>
              <input
                aria-label={`${p.name} tolerance`}
                value={p.tolerance ?? ""}
                placeholder="e.g. ±0.1 mm"
                onChange={(e) => upd(i, { tolerance: e.target.value || null })}
                className="field !h-7 !py-0 !text-sm min-w-[140px]"
              />
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function SpecView({ artifact: a, project, busy, save }: StageViewProps<SpecArtifact>) {
  const [draft, setDraft] = useState<SpecArtifact | null>(null);
  const [tolText, setTolText] = useState("");
  const editing = draft !== null;
  const s = draft ?? a;
  const functional = !a.bom.some((b) => b.category === "electronic");
  const glb = directionGlb(project.id, null, a.direction_id) ?? a.cad_files.find((f) => f.format === "glb")?.url;

  function startEdit() {
    setDraft(structuredClone(a));
    setTolText(a.tolerances.join("\n"));
  }
  async function commit() {
    if (!draft) return;
    const tolerances = tolText
      .split("\n")
      .map((t) => t.trim())
      .filter(Boolean);
    await save({ ...draft, tolerances });
    setDraft(null);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="flex flex-col">
          <ModelViewer url={glb} alt={a.product_name} height={420} tone="surface" />
          <p className="mt-2 text-sm text-ink-3">Full product from the CAD, direction {a.direction_id}. Drag to rotate.</p>
        </div>
        <Card
          title="Overall"
          right={
            editing ? (
              <span className="text-sm text-accent-ink">Editing</span>
            ) : (
              <Btn size="sm" variant="secondary" onClick={startEdit} disabled={busy}>
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
                  <path d="M10.5 2.5 13.5 5.5 5.5 13.5H2.5v-3l8-8Z" strokeLinejoin="round" />
                </svg>
                Edit spec
              </Btn>
            )
          }
        >
          <div className="flex flex-col gap-5">
            <KV k="Overall dimensions (L × W × H)">
              {editing ? (
                <DimsIn label="Overall" d={s.overall_dimensions} onChange={(overall_dimensions) => setDraft({ ...s, overall_dimensions })} />
              ) : (
                <DimsView d={s.overall_dimensions} />
              )}
            </KV>
            <KV k="Weight">{editing ? <NumIn label="Weight" v={s.weight} onChange={(weight) => setDraft({ ...s, weight })} /> : <LV v={s.weight} />}</KV>
            <KV k="Tolerances">
              {editing ? (
                <textarea
                  aria-label="Tolerances, one per line"
                  value={tolText}
                  onChange={(e) => setTolText(e.target.value)}
                  rows={Math.max(3, tolText.split("\n").length)}
                  className="field mt-1 font-mono !text-sm"
                />
              ) : s.tolerances.length ? (
                <ul className="flex flex-col gap-1">
                  {s.tolerances.map((t) => (
                    <li key={t} className="font-mono text-sm">
                      {t}
                    </li>
                  ))}
                </ul>
              ) : (
                <span className="text-ink-3">None specified</span>
              )}
            </KV>
            <KV k="CAD files">
              <div className="flex flex-col">
                {a.cad_files.length === 0 && <span className="text-ink-3">No CAD files yet.</span>}
                {a.cad_files.map((f) => (
                  <FileLink key={f.url} file={f} />
                ))}
              </div>
            </KV>
          </div>
        </Card>
      </div>

      <Card
        title={
          <>
            Parts <span className="font-mono text-ink-3">{s.parts.length}</span>
          </>
        }
      >
        {editing ? <PartsEditor parts={s.parts} onChange={(parts) => setDraft({ ...s, parts })} /> : <PartsTable parts={s.parts} />}
        {editing && (
          <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-line pt-5">
            <Btn variant="primary" onClick={commit} disabled={busy}>
              {busy && <Spinner />} Save spec
            </Btn>
            <Btn variant="ghost" onClick={() => setDraft(null)} disabled={busy}>
              Cancel
            </Btn>
            <span className="ml-2 flex items-center gap-2 text-sm text-ink-2">
              Edited numbers become <LabelBadge label="estimate" small /> with the original value in their source.
            </span>
          </div>
        )}
      </Card>
      <Card title={functional ? "Functional blocks" : "Electronics block diagram"} right={functional ? <span>No electronics — mechanical sub-assemblies</span> : undefined}>
        <BlockDiagram blocks={a.electronics_blocks} edges={a.electronics_edges} functional={functional} />
      </Card>
      <Card
        title={
          <>
            BOM <span className="font-mono text-ink-3">{a.bom.length}</span>
          </>
        }
      >
        <BOMTable items={a.bom} />
      </Card>
    </div>
  );
}
