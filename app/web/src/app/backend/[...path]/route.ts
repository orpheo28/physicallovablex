// Same-origin proxy to the API (/backend/* → API_URL/*), replacing the next.config rewrite (W28b, QA M3): an idempotent
// GET / HEAD that hits a dropped keep-alive socket (ECONNRESET, "socket hang up", "other side closed") is retried once
// server-side before an error ever reaches the page. Other methods are forwarded once (never replayed).
import { apiKeyHeaders } from "@/lib/apiKey";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const TIMEOUT_MS = 60_000; // on-demand AI renders (27 s server budget) and the PDF export fit; a stuck request fails
const HOP = ["connection", "keep-alive", "transfer-encoding", "content-length", "content-encoding", "host", "cookie"];

function transient(e: unknown): boolean {
  const err = e as { code?: string; message?: string; cause?: { code?: string; message?: string } };
  const text = `${err?.code ?? ""} ${err?.message ?? ""} ${err?.cause?.code ?? ""} ${err?.cause?.message ?? ""}`;
  return /ECONNRESET|socket hang up|other side closed|UND_ERR_SOCKET|EPIPE/i.test(text);
}

async function forward(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const target = `${API_URL}${url.pathname.slice("/backend".length) || "/"}${url.search}`;
  const headers = new Headers(request.headers);
  HOP.forEach((h) => headers.delete(h));
  for (const [k, v] of Object.entries(apiKeyHeaders())) headers.set(k, v);
  const idempotent = request.method === "GET" || request.method === "HEAD";
  const body = idempotent ? undefined : await request.arrayBuffer();

  let res: Response | null = null;
  for (let attempt = 0; ; attempt++) {
    try {
      res = await fetch(target, { method: request.method, headers, body, cache: "no-store", redirect: "follow", signal: AbortSignal.timeout(TIMEOUT_MS) });
      break;
    } catch (e) {
      if (idempotent && attempt === 0 && transient(e)) {
        await new Promise((r) => setTimeout(r, 150));
        continue;
      }
      return Response.json({ detail: "API unreachable. Is the API running?" }, { status: 502 });
    }
  }
  const out = new Headers(res.headers);
  HOP.forEach((h) => out.delete(h));
  return new Response(request.method === "HEAD" ? null : res.body, { status: res.status, statusText: res.statusText, headers: out });
}

export const GET = forward;
export const HEAD = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
