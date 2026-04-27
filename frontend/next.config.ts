import type { NextConfig } from "next";

/** Where the dev server proxies `/pm-api/*` (override if uvicorn is not on 8000). */
const backendDevProxy =
  process.env.BACKEND_DEV_PROXY_URL?.trim().replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/pm-api/:path*",
        destination: `${backendDevProxy}/:path*`,
      },
    ];
  },
};

export default nextConfig;
