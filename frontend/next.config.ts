import type { NextConfig } from "next";
import { backendProxyRewrites } from "./src/shared/backend-proxy";

const nextConfig: NextConfig = {
  async rewrites() {
    return backendProxyRewrites(process.env.BACKEND_ORIGIN);
  },
};

export default nextConfig;
