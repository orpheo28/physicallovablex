// Copy the public documentation (../docs/public, written by W25) into web/content/docs, which is what the web
// app builds from: Vercel only builds web/, so the docs must live inside it. Usage: npm run sync-docs
import { copyFileSync, existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(web, "..", "docs", "public");
const dst = join(web, "content", "docs");

if (!existsSync(src)) {
  console.log(`sync-docs: ${src} not found, keeping web/content/docs as is`);
  process.exit(0);
}
mkdirSync(dst, { recursive: true });
let n = 0;
for (const f of readdirSync(src)) {
  const p = join(src, f);
  if (!statSync(p).isFile() || !/\.(md|json|txt)$/.test(f)) continue;
  copyFileSync(p, join(dst, f));
  n++;
  console.log(`  ${f}`);
}
console.log(`sync-docs: ${n} file(s) copied to web/content/docs`);
