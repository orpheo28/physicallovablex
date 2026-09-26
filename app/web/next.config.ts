import type { NextConfig } from "next";

// The browser talks to the API through this same-origin proxy (/backend/*), so the
// demo works on any web port without touching the API's CORS settings.
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Clean screen shares and screenshots.
  devIndicators: false,
  // Autorun is async (202 + polling), so no request should take long. 60 s covers the slowest routes:
  // on-demand AI renders (27 s server budget) and the PDF export. A stuck request fails instead of hanging.
  experimental: { proxyTimeout: 60_000 },
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${API_URL}/:path*` }];
  },
};

export default nextConfig;
