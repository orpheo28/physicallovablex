/**
 * Local stand-in for W29's /parts and /anatomy (contracts/api.md "3D parts & anatomy"), used only while this API build
 * does not serve them (the viewer switches automatically when /openapi.json lists the routes).
 *
 * - Parts: one per GLB part node, measured on the loaded mesh (bbox, centroid), named from the node's material prefix.
 * - Anatomy: the exterior parts plus an ILLUSTRATIVE internal layout built from the BOM's electronic lines (board,
 *   battery, ICs), every internal labelled "estimate". Never a routed PCB — the viewer always says so.
 */
import type { VersionPreview } from "@/types/contracts";
import { ANATOMY_LABEL, fmtSize, type AnatomyLayer, type AnatomyStep, type EditableParam, type PartMeta, type ProjectAnatomy } from "./parts";

type V3 = [number, number, number];

/** What the viewer measured on the loaded GLB (mm, centred frame, +Y up). */
export type SceneNode = { id: string; raw: string; material: string; colour: string; bbox: V3; centroid: V3 };
export type SceneInfo = { nodes: SceneNode[]; bbox: V3 };

export type BomLine = { id: string; part: string; category: string; qty?: number; manufacturer_pn?: string | null; lcsc_pn?: string | null; description?: string };

const PREFIX: Record<string, { name: string; role: string }> = {
  body: { name: "Shell", role: "shell_top" },
  shell: { name: "Shell", role: "shell_top" },
  fabric: { name: "Strap", role: "strap" },
  strap: { name: "Strap", role: "strap" },
  glass: { name: "Window", role: "window" },
  lens: { name: "Lens", role: "lens" },
  led: { name: "Status light", role: "window" },
  diffuser: { name: "Light diffuser", role: "diffuser" },
  metal: { name: "Metal part", role: "frame" },
  rubber: { name: "Rubber part", role: "other" },
  coat: { name: "Painted part", role: "other" },
  accent: { name: "Accent trim", role: "other" },
  fin: { name: "Fin", role: "other" },
  prop: { name: "Propeller", role: "prop" },
  arm: { name: "Arm", role: "arm" },
  motor: { name: "Motor", role: "motor" },
  button: { name: "Button", role: "button" },
};

export const MATERIAL_OPTIONS = ["pc_abs", "aluminium", "stainless_steel", "tpu"];
export const FINISH_OPTIONS = ["Matte", "Satin", "Gloss", "Soft-touch", "Light texture"];

const prefixOf = (raw: string) => raw.toLowerCase().replace(/[._\-\s]*\d+$/, "").replace(/[^a-z]/g, "");
const vol = (b: V3) => b[0] * b[1] * b[2];
const round = (n: number) => Math.round(n * 10) / 10;

/** Parts of a GLB without W29 extras. `preview` gives the look and the size parameters the refine understands. */
export function mockParts(info: SceneInfo, preview?: VersionPreview | null): PartMeta[] {
  const byPrefix = new Map<string, SceneNode[]>();
  for (const n of info.nodes) {
    const p = prefixOf(n.raw);
    byPrefix.set(p, [...(byPrefix.get(p) ?? []), n]);
  }
  // The main body carries the size parameters: the largest shell (body.*), else the largest part.
  const shells = info.nodes.filter((n) => PREFIX[prefixOf(n.raw)]?.role === "shell_top");
  const main = [...(shells.length ? shells : info.nodes)].sort((a, b) => vol(b.bbox) - vol(a.bbox))[0];
  const d = preview?.dimensions;
  const wearable = /wearable|ring/.test(preview?.shape_family ?? "");
  const sizeParams: EditableParam[] = d
    ? (
        [
          ["length", "Length", d.length.value],
          ["width", "Width", d.width.value],
          ["height", wearable ? "Pod thickness" : "Height", d.height.value],
        ] as const
      ).map(([param, label, value]) => {
        const step = value >= 200 ? 5 : value >= 40 ? 1 : 0.5;
        const snap = (x: number) => Math.round(x / step) * step;
        return { param, label, value, step, unit: "mm", min: Math.max(step, snap(value * 0.6)), max: snap(value * 1.4) };
      })
    : [];

  return info.nodes.map((n) => {
    const p = prefixOf(n.raw);
    const def = PREFIX[p] ?? { name: p ? p.charAt(0).toUpperCase() + p.slice(1) : "Part", role: "other" };
    const siblings = byPrefix.get(p) ?? [n];
    let name = def.name;
    let role = def.role;
    if (def.role === "shell_top" && siblings.length === 2) {
      const top = siblings[0].centroid[1] >= siblings[1].centroid[1] ? siblings[0] : siblings[1];
      name = n === top ? "Top shell" : "Bottom shell";
      role = n === top ? "shell_top" : "shell_bottom";
    } else if (def.role === "shell_top" && siblings.length === 1) name = "Body";
    else if (siblings.length > 1) name = `${def.name} ${siblings.indexOf(n) + 1}`;
    const isMain = n === main;
    const exterior = ["shell_top", "shell_bottom", "strap", "frame", "arm", "other"].includes(role);
    return {
      part_id: n.id,
      name,
      role,
      layer_id: role === "shell_bottom" || (exterior && n.centroid[1] < 0 && role !== "shell_top") ? "exterior_bottom" : role === "strap" ? "strap" : "exterior_top",
      material: (shells.includes(n) ? preview?.material : null) ?? humanMaterial(n.material),
      finish: (shells.includes(n) ? preview?.finish : null) ?? "",
      colour_hex: n.colour,
      measured_bbox_mm: n.bbox.map(round) as V3,
      centroid_mm: n.centroid.map(round) as V3,
      label: "measured",
      editable: isMain ? sizeParams : [],
      colour_editable: exterior || role === "strap",
      material_options: exterior ? MATERIAL_OPTIONS : [],
    };
  });
}

/** GLB material names are short descriptions ("wipe-clean fabric", "dark glass"): capitalise them. */
const humanMaterial = (m: string) => (m ? m.charAt(0).toUpperCase() + m.slice(1) : "—");

// ------------------------------------------------------------------ illustrative anatomy

type Kind = "pcb" | "battery" | "component" | "sensor" | "motor" | "connector" | "antenna" | "skip";

function kindOf(b: BomLine): Kind {
  const t = `${b.part} ${b.description ?? ""}`.toLowerCase();
  if (/passive|resistor|capacitor|inductor|screw|fastener/.test(b.part.toLowerCase())) return "skip";
  if (/\bpcb\b|circuit board|mainboard|board\b/.test(b.part.toLowerCase())) return "pcb";
  if (/batter|li-?po|li-?ion|\bcell\b|mah/.test(t)) return "battery";
  if (/motor|fan|pump|servo|haptic|vibration/.test(t)) return "motor";
  if (/sensor|imu|accelero|gyro|camera|gps|gnss|microphone|\bmic\b|lidar|tof/.test(t)) return "sensor";
  if (/antenna/.test(t)) return "antenna";
  if (/connector|usb|contact|jack|port/.test(t)) return "connector";
  return "component";
}

/** "PCB with BLE antenna and charging-contact pads" → "PCB"; "BLE microcontroller, WCH CH582M" → "BLE microcontroller". */
const short = (s: string) => s.split(/,| with | for | and |\(/)[0].trim();

/**
 * An illustrative internal layout inside the largest exterior part: battery at the bottom, the board above it,
 * the ICs on the board. Steps walk from the product to its layers like an anatomy atlas.
 */
export function mockAnatomy(parts: PartMeta[], info: SceneInfo, bom: BomLine[], productName: string, version: number, glbUrl: string): ProjectAnatomy {
  const [X, Y, Z] = info.bbox;
  const R = Math.hypot(X, Y, Z) / 2;
  const main = [...parts].filter((p) => p.role !== "strap").sort((a, b) => vol(b.measured_bbox_mm) - vol(a.measured_bbox_mm))[0] ?? parts[0];
  const elec = bom.filter((b) => b.category === "electronic").map((b) => ({ b, k: kindOf(b) })).filter((x) => x.k !== "skip");
  const [mx, my, mz] = main?.measured_bbox_mm ?? info.bbox;
  const [cx, cy, cz] = main?.centroid_mm ?? [0, 0, 0];
  const wall = Math.max(1.2, Math.min(mx, my, mz) * 0.1);
  const inner: V3 = [mx - 2 * wall, my - 2 * wall, mz - 2 * wall];
  const electronics = elec.length > 0 && inner.every((v) => v > 1.5);
  const internals: PartMeta[] = [];

  const internal = (id: string, name: string, role: string, layer: string, size: V3, c: V3, b?: BomLine, material = "", colour = "#1A1A1C"): PartMeta => ({
    part_id: id,
    name,
    role,
    layer_id: layer,
    material,
    finish: "",
    colour_hex: colour,
    measured_bbox_mm: size.map(round) as V3,
    centroid_mm: c.map(round) as V3,
    label: "estimate",
    bom_item_id: b?.id ?? null,
    lcsc_pn: b?.lcsc_pn ?? null,
    package: b ? packageOf(kindOf(b), size) : null,
    unit_price: null,
    editable: [],
    colour_editable: false,
    material_options: [],
  });

  if (electronics) {
    const floor = cy - inner[1] / 2;
    const bat = elec.find((e) => e.k === "battery");
    const pcbLine = elec.find((e) => e.k === "pcb");
    const batH = bat ? inner[1] * 0.38 : 0;
    const pcbT = Math.max(0.8, Math.min(1.6, inner[1] * 0.08));
    if (bat) internals.push(internal("int_battery", short(bat.b.part), "battery", "battery", [inner[0] * 0.78, batH, inner[2] * 0.72], [cx, floor + batH / 2, cz], bat.b, "Li-Po pouch", "#9EA3A8"));
    const pcbY = floor + batH + pcbT / 2 + inner[1] * 0.04;
    internals.push(internal("int_pcb", pcbLine ? short(pcbLine.b.part) : "Main board", "pcb", "board", [inner[0] * 0.9, pcbT, inner[2] * 0.86], [cx, pcbY, cz], pcbLine?.b, "FR-4, black solder mask", "#16181A"));
    const chips = elec.filter((e) => e.k !== "battery" && e.k !== "pcb").slice(0, 8);
    const room = inner[1] - (pcbY + pcbT / 2 - floor);
    const base = Math.min(Math.max(Math.min(inner[0], inner[2]) * 0.2, 2.5), 40);
    const cols = Math.min(4, Math.max(2, Math.ceil(Math.sqrt(chips.length))));
    const rows = Math.max(1, Math.ceil(chips.length / cols));
    chips.forEach((e, i) => {
      const w = e.k === "connector" ? base * 0.7 : e.k === "sensor" ? base * 0.8 : e.k === "motor" ? base * 1.1 : base;
      const h = Math.max(0.6, Math.min(room * (e.k === "motor" ? 0.7 : 0.35), base * (e.k === "motor" ? 0.9 : 0.3)));
      const col = i % cols;
      const row = Math.floor(i / cols);
      const x = cx - inner[0] * 0.36 + ((col + 0.5) / cols) * inner[0] * 0.72;
      const z = cz - inner[2] * 0.3 + ((row + 0.5) / rows) * inner[2] * 0.6;
      const colour = e.k === "motor" ? "#8C9096" : e.k === "sensor" ? "#23262B" : e.k === "connector" ? "#C9A45C" : "#101112";
      const role = e.k === "sensor" || e.k === "component" ? "component" : e.k;
      internals.push(internal(`int_${e.b.id}`, short(e.b.part), role, "components", [w, h, w * (e.k === "connector" ? 0.5 : 1)], [x, pcbY + pcbT / 2 + h / 2, z], e.b, e.k === "motor" ? "Steel can" : "Epoxy package", colour));
    });
  }

  const all = [...parts, ...internals];
  const top = parts.filter((p) => p.layer_id === "exterior_top").map((p) => p.part_id);
  const bottom = parts.filter((p) => p.layer_id === "exterior_bottom").map((p) => p.part_id);
  const strap = parts.filter((p) => p.layer_id === "strap").map((p) => p.part_id);
  const ids = (layer: string) => internals.filter((p) => p.layer_id === layer).map((p) => p.part_id);
  // Layer travel: a share of the product's height, never more than its overall radius (tall products stay framed).
  const h = Math.min(Math.max(Y, 8), R * 0.9);
  const layers: AnatomyLayer[] = [];
  const add = (id: string, name: string, list: string[], v: V3, dist: number, caption: string) => list.length && layers.push({ id, name, order: layers.length, parts: list, explode_vector: v, explode_distance_mm: round(dist), caption });

  const mainName = main?.name.toLowerCase() ?? "body";
  if (electronics) {
    add("exterior_top", "Top shell", top, [0, 1, 0], h * 1.25, `The ${top.length > 1 ? "top parts" : mainName} lift away.`);
    add("components", "Components", ids("components"), [0, 1, 0], h * 0.75, "The chips that sense, think and talk.");
    add("board", "Main board", ids("board"), [0, 1, 0], h * 0.4, "One board carries the electronics.");
    add("battery", "Battery", ids("battery"), [0, -1, 0], h * 0.15, "The energy store, under the board.");
    add("exterior_bottom", "Bottom shell", bottom, [0, -1, 0], h * 0.7, "The base closes the product.");
    add("strap", "Strap", strap, [0, -1, 0], h * 1.1, "The strap holds it on the body.");
  } else {
    // Construction products: the exterior parts, split by height, open like layers.
    const sorted = [...parts].sort((a, b) => b.centroid_mm[1] - a.centroid_mm[1]);
    const groups = [sorted.slice(0, Math.ceil(sorted.length / 3)), sorted.slice(Math.ceil(sorted.length / 3), Math.ceil((2 * sorted.length) / 3)), sorted.slice(Math.ceil((2 * sorted.length) / 3))];
    groups.forEach((g, i) =>
      add(`layer_${i + 1}`, ["Upper parts", "Core", "Lower parts"][i], g.map((p) => p.part_id), [0, i === 0 ? 1 : i === 1 ? 0 : -1, i === 1 ? 1 : 0], h * (i === 1 ? 0.4 : 0.8), ["The upper layer lifts off.", "The core, measured on our CAD.", "The lower layer drops away."][i]),
    );
  }

  // ---- cameras (mm, centred frame): a ¾ view that fits the product, then closer views on each subject.
  const fov = 30;
  const fit = R / Math.sin(((fov / 2) * Math.PI) / 180);
  const dir: V3 = normalize([-0.62, 0.55, 0.9]);
  const cam = (target: V3, dist: number, d: V3 = dir): AnatomyStep["camera"] => ({ position_mm: target.map((t, i) => round(t + d[i] * dist)) as V3, target_mm: target.map(round) as V3, fov_deg: fov });
  const offsetOf = (id: string, exploded: string[]): V3 => {
    const l = layers.find((x) => x.parts.includes(id));
    if (!l || !exploded.includes(l.id)) return [0, 0, 0];
    return l.explode_vector.map((v) => v * l.explode_distance_mm) as V3;
  };
  const focusCam = (id: string, exploded: string[], zoom = 1): AnatomyStep["camera"] => {
    const p = all.find((x) => x.part_id === id);
    if (!p) return cam([0, 0, 0], fit * 1.1);
    const o = offsetOf(id, exploded);
    const c = p.centroid_mm.map((v, i) => v + o[i]) as V3;
    const r = Math.hypot(...p.measured_bbox_mm) / 2;
    return cam(c, Math.max(r * 6, fit * 0.5) * zoom, normalize([-0.5, 0.95, 0.75]));
  };
  const everything = layers.map((l) => l.id);
  const name = productName || "The product";
  const steps: AnatomyStep[] = [];
  const step = (title: string, caption: string, camera: AnatomyStep["camera"], exploded: string[], focus: string[]) =>
    steps.push({ id: `s${steps.length + 1}`, kicker: `${String(steps.length + 1).padStart(2, "0")} · ${title.toUpperCase()}`, title, caption, camera, layers_exploded: exploded, focus_parts: focus });

  step("The product", `${name}. ${fmtSize(info.bbox)} overall, measured on our CAD.`, cam([0, 0, 0], fit * 1.15), [], []);
  if (electronics) {
    const open = ["exterior_top", "strap"].filter((l) => everything.includes(l));
    step("The shell opens", `The ${mainName} lifts away: ${main?.material || "moulded shell"}${main?.finish ? `, ${main.finish.split("·")[0].trim()}` : ""}.`, cam([0, h * 0.35, 0], fit * 1.2), open, top);
    const pcb = internals.find((p) => p.role === "pcb");
    const onBoard = internals.filter((p) => p.layer_id === "components");
    if (pcb) step("Inside", `One board carries the electronics: ${onBoard.length} main parts from the BOM, placed for illustration.`, focusCam(pcb.part_id, open, 1.25), open, [pcb.part_id]);
    const brain = onBoard.find((p) => /micro|mcu|soc|processor|controller|bluetooth|ble|wi-?fi/i.test(p.name)) ?? onBoard[0];
    if (brain) step("The brain", `${brain.name}${brain.package ? ` · ${brain.package}` : ""}. It runs the firmware and the radio.`, focusCam(brain.part_id, open, 0.9), open, [brain.part_id]);
    const sensors = onBoard.filter((p) => p !== brain && /sensor|imu|accel|gyro|camera|gps|ppg|heart|optical|temperature|mic/i.test(p.name));
    if (sensors.length) step("Sensing", `${sensors.map((s) => s.name).join(" · ")}.`, focusCam(sensors[0].part_id, open, 1.1), open, sensors.map((s) => s.part_id));
    const bat = internals.find((p) => p.role === "battery");
    const deep = everything.filter((l) => l !== "battery");
    if (bat) step("Power", `${bat.name}, under the board.`, focusCam(bat.part_id, deep, 1.2), deep, [bat.part_id]);
  } else {
    layers.forEach((l, i) => step(l.name, l.caption, cam([0, 0, 0], fit * 1.2), everything.slice(0, i + 1), l.parts));
  }
  step("Every layer", `${all.length} parts. Exterior measured on our CAD; internals are an estimate.`, cam([0, 0, 0], fit * 1.55, normalize([-0.7, 0.5, 0.85])), everything, []);

  return { version, glb_url: glbUrl, label: ANATOMY_LABEL, kind: electronics ? "electronics" : "construction", bbox_mm: info.bbox.map(round) as V3, layers, steps, parts: all, mock: true };
}

function packageOf(k: Kind, s: V3): string | null {
  if (k === "battery") return `Pouch cell ≈ ${fmtSize(s)}`;
  if (k === "pcb") return `${Math.round(s[1] * 10) / 10} mm board`;
  if (k === "connector") return "Contact pads";
  if (k === "motor") return "Coin / can motor";
  return `IC package ≈ ${Math.round(s[0])} × ${Math.round(s[2])} mm (illustrative)`;
}

function normalize(v: V3): V3 {
  const l = Math.hypot(...v) || 1;
  return v.map((x) => x / l) as V3;
}
