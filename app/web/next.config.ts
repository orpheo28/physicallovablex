import type { NextConfig } from "next";

// The browser talks to the API through the same-origin proxy /backend/* (src/app/backend/[...path]/route.ts, W28b:
// it retries an idempotent GET once on a reset socket), so the demo works on any web port without touching the API's CORS.
const nextConfig: NextConfig = {
  // Clean screen shares and screenshots.
  devIndicators: false,
};

export default nextConfig;
