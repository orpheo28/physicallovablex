import { readDoc } from "@/lib/docs";

// Served verbatim from web/content/docs/llms.txt (synced from ../docs/public), built once at build time.
export const dynamic = "force-static";

export function GET() {
  const body = readDoc("llms.txt") ?? "# PhysicalLovableX\n\n> Documentation index is being written. See /docs.\n";
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
