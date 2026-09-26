// Server-side helper for page titles: the project's name, or its id if the API is unreachable.
import { apiKeyHeaders } from "./apiKey";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function projectName(id: string): Promise<string> {
  try {
    const res = await fetch(`${API_URL}/projects/${encodeURIComponent(id)}`, { cache: "no-store", headers: apiKeyHeaders(), signal: AbortSignal.timeout(2000) });
    if (!res.ok) return id;
    const j = (await res.json()) as { project?: { name?: string } };
    return j.project?.name ?? id;
  } catch {
    return id;
  }
}
