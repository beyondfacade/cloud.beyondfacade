import { expect, it } from "vitest";
import { GET } from "./route";
import { SNAPSHOT_YEAR } from "@/features/map-explorer/lib/metric-coverage";

it("지원하는 metric·industry는 200과 행 배열을 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=cafe"));
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual(
    expect.arrayContaining([{ region_code: expect.any(String), value: expect.any(Number) }]),
  );
});

it("미지원 metric은 500이 아니라 404 METRIC_NOT_FOUND를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics?metric=unknown_metric&industry=cafe"));
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("METRIC_NOT_FOUND");
});

it("지원하지 않는 industry는 404 INDUSTRY_NOT_FOUND를 반환한다", async () => {
  const res = await GET(
    new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=unknown_industry"),
  );
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});

it("업종이 다르면 같은 region·metric이어도 값이 달라진다", async () => {
  const cafeRes = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=cafe"));
  const gymRes = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=gym"));
  expect(await cafeRes.json()).not.toEqual(await gymRes.json());
});

it("같은 업종은 같은 (region, industry, metric)에 대해 항상 동일한 값을 반환한다", async () => {
  const first = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=cafe"));
  const second = await GET(new Request("http://test/api/mock/metrics?metric=growth_rate&year=2026&industry=cafe"));
  expect(await first.json()).toEqual(await second.json());
});

it("스냅샷 업종은 관측 연도의 점포수만 준다 — 실 API의 빈 배열을 그대로 흉내 낸다", async () => {
  // mock이 늘 427행을 주면 mock으로 개발하는 동안 "빈 지도" 경로를 한 번도 못 본다 (§15 미러 규칙).
  // 2026-09-24 실 API 실측: childcare×store_count×2026 426행 / 2024 0행 / closure_rate 0행
  const rows = async (query: string) =>
    (await (await GET(new Request(`http://test/api/mock/metrics?${query}`))).json()).length;

  expect(await rows(`industry=childcare&metric=store_count&year=${SNAPSHOT_YEAR}`)).toBeGreaterThan(0);
  expect(await rows("industry=childcare&metric=store_count&year=2024")).toBe(0);
  expect(await rows(`industry=childcare&metric=closure_rate&year=${SNAPSHOT_YEAR}`)).toBe(0);
  expect(await rows(`industry=convenience_store&metric=growth_rate&year=${SNAPSHOT_YEAR}`)).toBe(0);
});

it("학원은 점포수는 전 연도에 주고 폐업률·성장률은 빈 배열이다", async () => {
  // 서울 학원 API는 폐원일자를 주지 않는다 — 실 API(백엔드 v0.35.3)는 폐업률·성장률 0행, 점포수는 2019~2026
  const rows = async (query: string) =>
    (await (await GET(new Request(`http://test/api/mock/metrics?${query}`))).json()).length;

  expect(await rows("industry=academy&metric=store_count&year=2019")).toBeGreaterThan(0);
  expect(await rows("industry=academy&metric=closure_rate&year=2026")).toBe(0);
  expect(await rows("industry=academy&metric=growth_rate&year=2026")).toBe(0);
});

it("일반 업종은 전 연도·전 지표에 값이 있다", async () => {
  const rows = async (query: string) =>
    (await (await GET(new Request(`http://test/api/mock/metrics?${query}`))).json()).length;

  expect(await rows("industry=cafe&metric=store_count&year=2019")).toBeGreaterThan(0);
  expect(await rows("industry=cafe&metric=closure_rate&year=2026")).toBeGreaterThan(0);
});
