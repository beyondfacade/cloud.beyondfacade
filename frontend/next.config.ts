import type { NextConfig } from "next";
import { backendProxyRewrites } from "./src/shared/backend-proxy";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return backendProxyRewrites(process.env.BACKEND_ORIGIN);
  },
};

export default nextConfig;
