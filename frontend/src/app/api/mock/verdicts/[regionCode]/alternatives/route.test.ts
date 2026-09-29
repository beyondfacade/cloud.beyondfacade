import { expect, it } from "vitest";
import { GET } from "./route";

const RANK: Record<string, number> = { clear: 0, orange: 1, red: 2, insufficient: 3 };
const key = (v: { verdict_code: string; strong_count: number; on_count: number }) => [RANK[v.verdict_code], v.strong_count, v.on_count];
const less = (a: number[], b: number[]) => a.some((x, i) => (x === b[i] ? false : x < b[i])) && a.join() !== b.join();

function call(regionCode: string, query = "?industry=korean_food") {
  return GET(new Request(`http://test/api/mock/verdicts/${regionCode}/alternatives${query}`), {
    params: Promise.resolve({ regionCode }),
  });
}

it("두 축 모두 기준보다 신호가 적은 clear·orange만 3개까지, 자기 자신은 빠진다", async () => {
  const { GET: single } = await import("../route");
  const base = await (await single(new Request("http://test/api/mock/verdicts/1168064000?industry=korean_food"), { params: Promise.resolve({ regionCode: "1168064000" }) })).json();
  const res = await call("1168064000");
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.region_code).toBe("1168064000");
  expect(body.industry_id).toBe("korean_food");
  expect(typeof body.neighborhood_type).toBe("string");
  for (const list of [body.industries, body.regions]) {
    expect(list.length).toBeLessThanOrEqual(3);
    for (const a of list) {
      expect(["clear", "orange"]).toContain(a.verdict_code);
      expect(less(key(a), key(base))).toBe(true);
    }
  }
  expect(body.industries.map((a: { industry_id: string }) => a.industry_id)).not.toContain("korean_food");
  expect(body.regions.map((a: { region_code: string }) => a.region_code)).not.toContain("1168064000");
  for (const a of body.industries) expect(a.industry_name.length).toBeGreaterThan(0);
  for (const a of body.regions) expect(a.region_name).toMatch(/동$/);
});

it("업종 고정 축의 동은 기준 동과 같은 동네 유형이다", async () => {
  const body = await (await call("1168064000")).json();
  const { GET: profiles } = await import("../../../profiles/types/route");
  const rows = await (await profiles(new Request("http://test/api/mock/profiles/types?year_quarter=20262"))).json();
  const typeOf = (code: string) => rows.find((r: { region_code: string }) => r.region_code === code)?.type_code;
  for (const a of body.regions) expect(typeOf(a.region_code)).toBe(body.neighborhood_type);
});

it("모르는 동은 404 VERDICT_NOT_FOUND, 판정 대상이 아닌 업종은 404 INDUSTRY_NOT_FOUND", async () => {
  const missing = await call("0000000000");
  expect(missing.status).toBe(404);
  expect((await missing.json()).error.code).toBe("VERDICT_NOT_FOUND");
  const excluded = await call("1168064000", "?industry=convenience_store");
  expect(excluded.status).toBe(404);
  expect((await excluded.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
});
