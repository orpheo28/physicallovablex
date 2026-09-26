// Web password gate (APP_PASSWORD). The cookie holds a digest of the password, never the password itself.
export const SESSION_COOKIE = "plx_session";
export const SESSION_MAX_AGE = 7 * 24 * 3600; // 7 days

export async function sessionToken(password: string): Promise<string> {
  const data = new TextEncoder().encode(`physicallovablex:v1:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Constant-time string equality (both sides are fixed-length hex digests here). */
export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/** Only same-site paths: "/x?y" is fine; "//evil.com", "/\\evil.com", "https://…" and anything with a control character
 * (browsers strip tab/newline, so "/\t/evil.com" would become "//evil.com") is not. */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || /[\\\u0000-\u001f\u007f]/.test(next)) return "/";
  return next;
}
