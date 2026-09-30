import type { NextConfig } from "next";
import { backendProxyRewrites } from "./src/shared/backend-proxy";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  async redirects() {
    // 관리자 전용 로그인은 공용 로그인(/login)으로 합쳐졌다 — 쿼리(next)는 그대로 넘어간다
    return [{ source: "/admin/login", destination: "/login", permanent: false }];
  },
  async rewrites() {
    return backendProxyRewrites(process.env.BACKEND_ORIGIN);
  },
};

export default nextConfig;
