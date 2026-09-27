// Server-side check that the API exposes the production MCP over HTTP (W22, mounted at /mcp).
// A mounted MCP app is not in /openapi.json, so probe it: 404 = absent; any other answer (405/406/400…) = present.
import { apiKeyHeaders } from "@/lib/apiKey";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/mcp`, { cache: "no-store", headers: { Accept: "text/event-stream", ...apiKeyHeaders() }, signal: AbortSignal.timeout(4000) });
    res.body?.cancel().catch(() => undefined); // an SSE stream may stay open: never wait for it
    return Response.json({ exists: res.status !== 404 && res.status < 500 });
  } catch {
    return Response.json({ exists: false });
  }
}
