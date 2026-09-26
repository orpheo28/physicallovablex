// Thin client for the PhysicalLovableX API (contracts/api.md).
// All calls go through the same-origin /backend proxy declared in next.config.ts,
// which forwards to NEXT_PUBLIC_API_URL (default http://localhost:8000).
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const API_BASE = "/backend";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(method: string, path: string, body?: unknown, timeoutMs?: number): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      signal: timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined,
    });
  } catch {
    throw new ApiError(0, `API unreachable (${API_URL}). Is the API running?`);
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      if (j && typeof j.detail === "string") detail = j.detail;
      else if (j && j.detail) detail = JSON.stringify(j.detail).slice(0, 300);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError(res.status, "Invalid JSON from the API");
  }
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  /** GET that gives up after `ms` (polling: a stuck request must never hold a browser connection). */
  poll: <T>(path: string, ms = 5000) => request<T>("GET", path, undefined, ms),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
};

/** URL of a file served by the API (CadFile.url, glb_url…), through the proxy. */
export function fileUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^https?:\/\//.test(url)) return url;
  return `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
}

export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
