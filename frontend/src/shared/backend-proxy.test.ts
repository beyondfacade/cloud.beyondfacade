import { describe, expect, it } from "vitest";
import { BACKEND_PROXY_PREFIX, backendProxyRewrites } from "./backend-proxy";

describe("backendProxyRewrites", () => {
  it("BACKEND_ORIGIN이 있으면 /api/backend/* 를 백엔드로 전달한다 (끝 슬래시 정규화)", () => {
    expect(backendProxyRewrites("http://127.0.0.1:8201/")).toEqual([
      { source: `${BACKEND_PROXY_PREFIX}/:path*`, destination: "http://127.0.0.1:8201/:path*" },
    ]);
  });

  it("BACKEND_ORIGIN이 없으면 프록시를 만들지 않는다 (Vercel·mock 기본 동작 유지)", () => {
    expect(backendProxyRewrites(undefined)).toEqual([]);
    expect(backendProxyRewrites("")).toEqual([]);
  });
});
