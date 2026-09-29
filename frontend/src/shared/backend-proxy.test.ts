import { describe, expect, it } from "vitest";
import { tryToParsePath } from "next/dist/lib/try-to-parse-path";
import { BACKEND_PROXY_PREFIX, backendProxyRewrites } from "./backend-proxy";

describe("backendProxyRewrites", () => {
  it("BACKEND_ORIGIN이 있으면 /api/backend/* 를 백엔드로 전달한다 (끝 슬래시 정규화)", () => {
    expect(backendProxyRewrites("http://127.0.0.1:8201/")).toEqual([
      { source: expect.any(String), destination: "http://127.0.0.1:8201/:path*" },
    ]);
  });

  it.each([
    ["/api/backend/analysis/a1/events", false],
    ["/api/backend/analysis/a1/events/", false],
    ["/api/backend/analysis/other-id/events", false],
    ["/api/backend/analysis", true],
    ["/api/backend/analysis/a1", true],
    ["/api/backend/analysis/a1/events/history", true],
    ["/api/backend/analysis/a1/events-extra", true],
    ["/api/backend/verdicts/1168064000", true],
    ["/api/backend", true],
  ])("SSE 경로만 rewrite에서 제외한다: %s → %s", (path, matches) => {
    const [rewrite] = backendProxyRewrites("http://127.0.0.1:8201");
    const { regexStr, error } = tryToParsePath(rewrite.source);
    expect(error).toBeUndefined();
    expect(new RegExp(regexStr!).test(path)).toBe(matches);
    expect(rewrite.source.startsWith(BACKEND_PROXY_PREFIX)).toBe(true);
  });

  it("BACKEND_ORIGIN이 없으면 프록시를 만들지 않는다 (Vercel·mock 기본 동작 유지)", () => {
    expect(backendProxyRewrites(undefined)).toEqual([]);
    expect(backendProxyRewrites("")).toEqual([]);
  });
});
