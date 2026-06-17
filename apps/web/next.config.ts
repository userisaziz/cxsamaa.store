import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output: bundles only what's needed to run (~50MB vs ~200MB)
  // Critical for 1GB VM — produces .next/standalone/server.js
  output: "standalone",
  compress: true,
};

export default nextConfig;
