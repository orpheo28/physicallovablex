// Server-side existence check for API files (GLB/STEP/STL), so a missing file
// never shows up as a 404 in the browser console.
import { apiKeyHeaders } from "@/lib/apiKey";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function GET(request: Request) {
  const path = new URL(request.url).searchParams.get("path") ?? "";
  const allowed = /^\/files\/[\w.\-/]+$/.test(path) || /^\/projects\/[\w-]+\/cad\/code\/\d+$/.test(path); // + the Studio's CAD program (W19)
  if (!allowed || path.includes("..")) return Response.json({ exists: false });
  try {
    // The API file route only answers GET (HEAD → 405): read the status, drop the body.
    const res = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      headers: { Range: "bytes=0-0", ...apiKeyHeaders() },
      signal: AbortSignal.timeout(5000),
    });
    await res.arrayBuffer(); // 1 byte (Range) or a small error body
    return Response.json({ exists: res.ok });
  } catch {
    return Response.json({ exists: false });
  }
}
