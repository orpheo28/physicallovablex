import { readDoc } from "@/lib/docs";

// Served verbatim from web/content/docs/agents.md (synced from ../docs/public), built once at build time.
export const dynamic = "force-static";

export function GET() {
  const body = readDoc("agents.md") ?? "# agents.md\n\nInstructions for AI agents are being written. See /llms.txt and /docs meanwhile.\n";
  return new Response(body, { headers: { "Content-Type": "text/markdown; charset=utf-8" } });
}
