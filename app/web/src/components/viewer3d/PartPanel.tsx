"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { fmtValue, LABEL_DOT, LABEL_TEXT } from "@/lib/meta";
import { fmtNum, fmtSize, materialName, SWATCHES, type EditableParam, type PartEdit, type PartMeta } from "@/lib/parts";
import { FINISH_OPTIONS } from "@/lib/partsMock";
import { LabelBadge, Spinner } from "../ui";
import type { EditHandler } from "./Stage";

const ROLE: Record<string, string> = {
  shell_top: "Top shell",
  shell_bottom: "Bottom shell",
  strap: "Strap",
  button: "Button",
  window: "Window",
  lens: "Lens",
  diffuser: "Diffuser",
  frame: "Frame",
  arm: "Arm",
  prop: "Propeller",
  motor: "Motor",
  pcb: "Circuit board",
  component: "Component",
  battery: "Battery",
  antenna: "Antenna",
  connector: "Connector",
  cable: "Cable",
  fastener: "Fastener",
  other: "Part",
};

function Dot({ label }: { label: string }) {
  const l = (label in LABEL_TEXT ? label : "estimate") as keyof typeof LABEL_TEXT;
  return <span className={`tdot ${LABEL_DOT[l]}`} aria-label={LABEL_TEXT[l]} />;
}

/** Hover tooltip on a part (BRAND tooltip: ink panel, white text): name, material · finish, measured size + its dot. */
export function PartTip({ part, x, y, w, h, dark }: { part: PartMeta; x: number; y: number; w: number; h: number; dark: boolean }) {
  const left = Math.min(x + 16, w - 250);
  const top = Math.min(y + 18, h - 90);
  const look = [part.material, part.finish?.split("·")[0]?.trim()].filter(Boolean).join(" · ");
  return (
    <div
      role="tooltip"
      data-part-tip={part.part_id}
      className={`pointer-events-none absolute z-30 max-w-[240px] rounded-[10px] px-2.5 py-2 text-[12.5px] leading-[18px] text-white ${dark ? "bg-white/12 backdrop-blur-sm" : "bg-ink"}`}
      style={{ left, top }}
    >
      <p className="font-medium">{part.name}</p>
      {look && <p className="text-white/75">{look}</p>}
      <p className="mt-0.5 flex items-center gap-1.5 text-white/75">
        <span className="font-mono">{fmtSize(part.measured_bbox_mm)}</span>
        <Dot label={part.label} />
        <span className="text-white/60">{LABEL_TEXT[(part.label in LABEL_TEXT ? part.label : "estimate") as keyof typeof LABEL_TEXT]}</span>
      </p>
    </div>
  );
}

/**
 * "Edit this part" (Studio) or a read-only part card (Overview, anatomy, internal parts): colour swatches + custom
 * picker, material and finish, a slider per editable parameter. Apply → a new version, like any refine.
 */
export function PartPanel({
  part,
  dark,
  projectId,
  onEdit,
  editNote,
  viaRoute,
  onPreview,
  onClose,
  onApplied,
  editLink,
  top = 12,
}: {
  /** Overview: where this part can be edited (Studio) or read in full (the 3D-model step). */
  editLink?: { href: string; label: string };
  /** The edit was accepted (202): the stage closes the panel, the preview stays until the new version loads. */
  onApplied?: () => void;
  top?: number;
  part: PartMeta;
  dark: boolean;
  projectId?: string;
  onEdit?: EditHandler;
  editNote?: string | null;
  viaRoute: boolean;
  onPreview: (colour: string | null) => void;
  onClose: () => void;
}) {
  const [colour, setColour] = useState<string | null>(null);
  const [material, setMaterial] = useState<string>(part.material);
  const [finish, setFinish] = useState<string>(part.finish?.split("·")[0]?.trim() ?? "");
  const [params, setParams] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const pickId = useId();
  const internal = part.label === "estimate";
  const editable = !!onEdit && !internal && (part.colour_editable || part.material_options.length > 0 || part.editable.length > 0);

  const changedParam = part.editable.find((p) => params[p.param] !== undefined && params[p.param] !== p.value);
  const edit: PartEdit | null = colour
    ? { colour_hex: colour }
    : changedParam
      ? { param: changedParam.param, value: params[changedParam.param] }
      : material !== part.material || (finish && finish !== (part.finish?.split("·")[0]?.trim() ?? ""))
        ? { ...(material !== part.material ? { material } : {}), ...(finish ? { finish } : {}) }
        : null;

  async function apply() {
    if (!edit || !onEdit) return;
    setBusy(true);
    setError(null);
    const err = await onEdit(part, edit);
    setBusy(false);
    if (err) setError(err);
    else {
      setSent(true);
      onApplied?.();
    }
  }

  const tone = dark ? "bg-[#161618] text-white" : "bg-surface text-ink shadow-float";
  const sub = dark ? "text-white/60" : "text-ink-3";
  return (
    <aside
      data-part-panel={part.part_id}
      aria-label={editable ? `Edit ${part.name}` : part.name}
      className={`absolute right-3 z-30 flex w-[300px] flex-col overflow-y-auto rounded-lg p-4 ${tone}`}
      style={{ top, maxHeight: `calc(100% - ${top + 64}px)` }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className={`text-2xs ${sub}`}>{editable ? "Edit this part" : (ROLE[part.role] ?? "Part")}</p>
          <h3 className="title text-md leading-6">{part.name}</h3>
        </div>
        <button onClick={onClose} aria-label="Close" className={`press -mr-1 -mt-1 flex h-7 w-7 items-center justify-center rounded ${dark ? "text-white/70 hover:bg-white/10" : "text-ink-2 hover:bg-paper-2 hover:text-ink"}`}>
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden>
            <path d="m4 4 8 8M12 4l-8 8" />
          </svg>
        </button>
      </div>

      <dl className="mt-3 grid grid-cols-[72px_minmax(0,1fr)] gap-x-2 gap-y-1.5 text-sm">
        <dt className={sub}>Size</dt>
        <dd className="flex items-center gap-1.5">
          <span className="font-mono">{fmtSize(part.measured_bbox_mm)}</span>
          {dark ? <Dot label={part.label} /> : <LabelBadge label={part.label} tip={part.label === "measured" ? "Bounding box of this part, measured on our CAD" : "Illustrative size from the part's package — not measured"} small />}
        </dd>
        {(part.material || part.finish) && (
          <>
            <dt className={sub}>Look</dt>
            <dd className="flex items-start gap-2">
              {!internal && <span className="mt-[3px] h-3.5 w-3.5 shrink-0 rounded-full shadow-[inset_0_0_0_1px_rgb(0_0_0/0.14)]" style={{ background: colour ?? part.colour_hex }} aria-hidden />}
              <span className="min-w-0">{[part.material, part.finish?.split("·")[0]?.trim()].filter(Boolean).join(" · ")}</span>
            </dd>
          </>
        )}
        {part.package && (
          <>
            <dt className={sub}>Package</dt>
            <dd className="min-w-0">{part.package}</dd>
          </>
        )}
        {part.lcsc_pn && (
          <>
            <dt className={sub}>LCSC</dt>
            <dd className="font-mono">{part.lcsc_pn}</dd>
          </>
        )}
        {part.unit_price && (
          <>
            <dt className={sub}>Unit price</dt>
            <dd className="flex items-center gap-1.5">
              <span className="font-mono">{fmtValue(part.unit_price)}</span>
              {dark ? <Dot label={part.unit_price.label} /> : <LabelBadge label={part.unit_price.label} tip={part.unit_price.source_or_assumption} small />}
              <span className={`text-2xs ${sub}`}>{LABEL_TEXT[(part.unit_price.label in LABEL_TEXT ? part.unit_price.label : "estimate") as keyof typeof LABEL_TEXT]}</span>
            </dd>
          </>
        )}
      </dl>
      {part.bom_item_id && projectId && (
        <Link href={`/projects/${projectId}?stage=5`} className={`mt-2 text-sm underline underline-offset-4 ${dark ? "text-white/80 decoration-white/30 hover:text-white" : "text-ink-2 decoration-line-2 hover:text-ink"}`}>
          BOM line {part.bom_item_id} in Costs &amp; investment →
        </Link>
      )}
      {internal && <p className={`mt-2 text-2xs ${sub}`}>Illustrative placement — not a routed PCB.</p>}
      {editLink && !internal && (
        <Link href={editLink.href} className="mt-3 text-sm font-medium text-ink underline decoration-line-2 underline-offset-4 hover:decoration-ink">
          {editLink.label}
        </Link>
      )}

      {editable && (
        <div className="mt-4 flex flex-col gap-4">
          {part.colour_editable && (
            <fieldset>
              <legend className="text-sm text-ink-3">Colour</legend>
              <div className="mt-2 flex flex-wrap items-center gap-2" role="radiogroup" aria-label="Colour">
                {SWATCHES.map((s) => {
                  const on = (colour ?? part.colour_hex)?.toUpperCase() === s.hex;
                  return (
                    <button
                      key={s.hex}
                      role="radio"
                      aria-checked={on}
                      aria-label={s.name}
                      title={s.name}
                      data-swatch={s.name}
                      onClick={() => {
                        setColour(s.hex);
                        setParams({});
                        setSent(false);
                        onPreview(s.hex);
                      }}
                      className={`press h-6 w-6 rounded-full shadow-[inset_0_0_0_1px_rgb(0_0_0/0.14)] transition-shadow duration-150 ${on ? "outline outline-2 outline-offset-2 outline-ink" : ""}`}
                      style={{ background: s.hex }}
                    />
                  );
                })}
                <label htmlFor={pickId} className="press relative flex h-6 w-6 cursor-pointer items-center justify-center rounded-full bg-paper-2 text-ink-2 hover:text-ink" title="Custom colour">
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden>
                    <path d="M8 3v10M3 8h10" />
                  </svg>
                  <input
                    id={pickId}
                    type="color"
                    aria-label="Custom colour"
                    className="absolute inset-0 cursor-pointer opacity-0"
                    value={colour ?? part.colour_hex ?? "#cccccc"}
                    onChange={(e) => {
                      const hex = e.target.value.toUpperCase();
                      setColour(hex);
                      setParams({});
                      setSent(false);
                      onPreview(hex);
                    }}
                  />
                </label>
              </div>
              {colour && <p className="mt-1.5 font-mono text-2xs text-ink-3">{colour} · {SWATCHES.find((s) => s.hex === colour)?.name ?? "Custom"}</p>}
            </fieldset>
          )}

          {part.material_options.length > 0 && (
            <div className="flex flex-col gap-2">
              <label className="flex flex-col gap-1 text-sm text-ink-3">
                Material
                <select
                  value={material}
                  onChange={(e) => {
                    setMaterial(e.target.value);
                    setColour(null);
                    onPreview(null);
                    setSent(false);
                  }}
                  className="h-8 rounded border border-line-2 bg-surface px-2 text-sm text-ink hover:border-ink-4 focus:border-ink"
                >
                  <option value={part.material}>{part.material}</option>
                  {part.material_options
                    .filter((k) => materialName(k) !== part.material)
                    .map((k) => (
                      <option key={k} value={k}>
                        {materialName(k)}
                      </option>
                    ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm text-ink-3">
                Finish
                <select
                  value={finish}
                  onChange={(e) => {
                    setFinish(e.target.value);
                    setColour(null);
                    onPreview(null);
                    setSent(false);
                  }}
                  className="h-8 rounded border border-line-2 bg-surface px-2 text-sm text-ink hover:border-ink-4 focus:border-ink"
                >
                  {Array.from(new Set([finish, ...FINISH_OPTIONS].filter(Boolean))).map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {part.editable.map((p) => (
            <Slider
              key={p.param}
              p={p}
              value={params[p.param] ?? p.value}
              onChange={(v) => {
                setParams({ [p.param]: v });
                setColour(null);
                onPreview(null);
                setSent(false);
              }}
            />
          ))}

          <div className="flex items-center gap-2">
            <button
              onClick={apply}
              disabled={!edit || busy || !!editNote}
              data-apply
              className="press inline-flex h-8 items-center gap-2 rounded bg-ink px-3 text-sm font-medium text-white transition-colors duration-150 hover:bg-[#2a2a2a] disabled:cursor-not-allowed disabled:bg-paper-2 disabled:text-ink-3"
            >
              {busy && <Spinner className="!h-3 !w-3" />} Apply
            </button>
            {edit && !busy && (
              <button
                onClick={() => {
                  setColour(null);
                  setParams({});
                  setMaterial(part.material);
                  setFinish(part.finish?.split("·")[0]?.trim() ?? "");
                  onPreview(null);
                }}
                className="press h-8 rounded px-2.5 text-sm text-ink-2 hover:bg-paper-2 hover:text-ink"
              >
                Reset
              </button>
            )}
          </div>
          {editNote && <p className="text-2xs text-ink-3">{editNote}</p>}
          {error && (
            <p role="status" className="rounded bg-estimate-soft px-2.5 py-1.5 text-2xs text-estimate-ink">
              {error}
            </p>
          )}
          {sent && !error && <p role="status" className="text-2xs text-ink-2">Building the new version… it appears in the conversation.</p>}
          {!viaRoute && !sent && <p className="text-2xs text-ink-3">Sent to the Studio as a prompt; the new version is built like any refine.</p>}
        </div>
      )}
    </aside>
  );
}

function Slider({ p, value, onChange }: { p: EditableParam; value: number; onChange: (v: number) => void }) {
  const id = useId();
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <label htmlFor={id} className="text-ink-3">
          {p.label}
        </label>
        <span className="font-mono text-ink">
          {fmtNum(value)} <span className="text-ink-3">{p.unit}</span>
          {value !== p.value && <span className="ml-1.5 text-ink-4 line-through">{fmtNum(p.value)}</span>}
        </span>
      </div>
      <input
        id={id}
        type="range"
        data-param={p.param}
        min={p.min}
        max={p.max}
        step={p.step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="range mt-1.5 w-full"
      />
      <div className="flex justify-between font-mono text-2xs text-ink-3">
        <span>{fmtNum(p.min)}</span>
        <span>{fmtNum(p.max)}</span>
      </div>
    </div>
  );
}
