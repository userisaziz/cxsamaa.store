import type { NextConfig } from "next";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // Standalone output: bundles only what's needed to run (~50MB vs ~200MB)
  // Critical for 1GB VM — produces .next/standalone/server.js
  output: "standalone",
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_BASE_URL}/api/:path*`,
      },
    ];
  },
  compress: true,
};

export default nextConfig;
