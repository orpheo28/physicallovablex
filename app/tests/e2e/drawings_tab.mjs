// C3 — Studio "Drawings" tab end to end (Playwright, headless Chromium). Needs the isolated stack:
//   API  : CAD_DRAWINGS=1 DB_PATH=api/data/c3.db FILES_DIR=api/data/files_c3 uv run uvicorn api.main:app --port 8133
//   Web  : (cd web && NEXT_PUBLIC_API_URL=http://localhost:8133 npx next dev -p 3133)
//   then : curl -X POST localhost:8133/demo/reset && node tests/e2e/drawings_tab.mjs
// Checks: tab visible (route in OpenAPI), sheets + thumbnails load, zoom, sheet switch, downloads resolve, stage 3 link
// opens the tab; 0 console errors / page errors / 5xx. Screenshots → docs/screens/drawings/.
import { createRequire } from "module";
import { mkdirSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const require = createRequire(process.env.PLAYWRIGHT_REQUIRE ?? "/Users/orpheohellandsjo/.npm/_npx/e41f203b7505f1fb/package.json");
const { chromium } = require("playwright");
const WEB = process.env.WEB_URL ?? "http://localhost:3133";
const OUT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../docs/screens/drawings");
mkdirSync(OUT, { recursive: true });

const errs = [];
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const p = await ctx.newPage();
p.on("console", (m) => m.type() === "error" && errs.push(`${p.url()} console: ${m.text().slice(0, 240)}`));
p.on("pageerror", (e) => errs.push(`${p.url()} pageerror: ${e.message.slice(0, 240)}`));
p.on("response", (r) => r.status() >= 500 && errs.push(`HTTP ${r.status()} ${r.url()}`));
const check = (cond, msg) => {
  if (!cond) throw new Error(`FAIL: ${msg}`);
  console.log(`ok  ${msg}`);
};

async function openDrawings(pid) {
  await p.goto(`${WEB}/projects/${pid}/studio`, { waitUntil: "domcontentloaded" });
  const tab = p.getByRole("tab", { name: "Drawings" });
  await tab.waitFor({ timeout: 60000 });
  await tab.click();
  await p.getByTestId("drawings-tab").waitFor({ timeout: 90000 });
  await p.waitForFunction(() => {
    const ok = (i) => !!i && i.complete && i.naturalWidth > 0;
    return ok(document.querySelector('[data-testid="drawing-viewer"] img')) && ok(document.querySelector('[aria-label="Sheets"] img'));
  }, null, { timeout: 60000 });
  await p.waitForTimeout(400); // let the visible (lazy) thumbnails paint before the screenshot
}

const shots = [
  ["demo_whoop_kitesurf", "studio_drawings_whoop"],
  ["demo_stick_vacuum", "studio_drawings_vacuum"],
  ["demo_drone_follow", "studio_drawings_drone"],
  ["demo_surfboard_beginner", "studio_drawings_surfboard"],
  ["demo_changing_table", "studio_drawings_changing_table"],
];
for (const [pid, name] of shots) {
  await openDrawings(pid);
  const thumbs = p.locator('[aria-label="Sheets"] li');
  const n = await thumbs.count();
  check(n >= 2, `${pid}: ${n} sheets listed`);
  check(await p.getByText("Generated from CAD — verify before release").first().isVisible(), `${pid}: disclaimer shown`);
  await p.screenshot({ path: `${OUT}/${name}.png` });
}

// whoop: switch to a moulded shell sheet, zoom in, downloads resolve
await openDrawings("demo_whoop_kitesurf");
await p.locator('[aria-label="Sheets"] button', { hasText: "M01" }).click();
await p.waitForFunction(() => document.querySelector('[data-testid="drawing-viewer"] img')?.getAttribute("src")?.includes("_M01.svg"));
await p.getByRole("button", { name: "Zoom in" }).click();
await p.getByRole("button", { name: "Zoom in" }).click();
check((await p.getByRole("button", { name: "Fit sheet" }).innerText()).trim() === "225%", "zoom 225 %");
await p.screenshot({ path: `${OUT}/studio_drawings_whoop_M01_zoom.png` });
for (const label of ["PDF", "SVG", "All sheets"]) {
  const href = await p.locator("a[download]", { hasText: label }).getAttribute("href");
  const r = await p.request.get(`${WEB}${href}`);
  const body = await r.body();
  check(r.ok() && (label === "SVG" ? body.subarray(0, 4).toString() === "<svg" : body.subarray(0, 5).toString() === "%PDF-"), `download ${label} ${href}`);
}
await p.getByRole("button", { name: "Fit sheet" }).click();

// stage 3: "Technical drawings" link → Studio with the Drawings tab open
await p.goto(`${WEB}/projects/demo_whoop_kitesurf?stage=3`, { waitUntil: "domcontentloaded" });
const link = p.getByRole("link", { name: /Technical drawings/ });
await link.waitFor({ timeout: 60000 });
await link.scrollIntoViewIfNeeded();
await p.screenshot({ path: `${OUT}/stage3_drawings_link.png` });
await link.click();
await p.getByTestId("drawings-tab").waitFor({ timeout: 90000 });
check(p.url().includes("tab=drawings"), "stage 3 link opens the Drawings tab");

await b.close();
if (errs.length) {
  console.error(errs.join("\n"));
  throw new Error(`FAIL: ${errs.length} console / page errors`);
}
console.log("ok  0 console errors");
