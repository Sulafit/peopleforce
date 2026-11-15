import type { NextConfig } from "next";

// Where the Next.js server reaches the FastAPI backend. The browser never sees this address:
// it calls /api/v1/* on the web origin and the rewrite below forwards the request, so cookies
// stay first-party. Rewrites are resolved at build time, so set this as a build argument.
const apiUrl = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // Self-contained server bundle for the production Docker image.
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${apiUrl}/api/v1/:path*` }];
  },
};

export default nextConfig;
