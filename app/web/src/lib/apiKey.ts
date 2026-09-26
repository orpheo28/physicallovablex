// Server-only: the header the API expects when API_SHARED_KEY is set (api/auth.py). Never a NEXT_PUBLIC_ variable.
export function apiKeyHeaders(): Record<string, string> {
  const key = process.env.API_SHARED_KEY;
  return key ? { "X-App-Key": key } : {};
}
