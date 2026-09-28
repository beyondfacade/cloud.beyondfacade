import { expect, it } from "vitest";
import { GET } from "./route";

function call(query: string) {
  return GET(new Request(`http://test/api/mock/verdicts${query}`));
}

it("판정 대상 업종은 200과 region_code·value(판정 코드) 쌍 목록을 준다", async () => {
  const res = await call("?industry=korean_food");
  expect(res.status).toBe(200);
  const rows = await res.json();
  expect(rows.length).toBeGreaterThan(400);
  expect(Object.keys(rows[0]).sort()).toEqual(["region_code", "value"]);
  const codes = new Set(rows.map((r: { value: string }) => r.value));
  expect([...codes].sort()).toEqual(["clear", "insufficient", "orange", "red"]); // 네 판정이 전부 나와야 지도 범례·QA가 가능하다
  for (const r of rows) expect(["red", "orange", "clear", "insufficient"]).toContain(r.value);
});

it("학원·어린이집·치킨·편의점·미등록 업종은 404 INDUSTRY_NOT_FOUND (실 API 미러)", async () => {
  for (const industry of ["academy", "childcare", "chicken", "restaurant_other", "convenience_store", "unknown"]) {
    const res = await call(`?industry=${industry}`);
    expect(res.status, industry).toBe(404);
    expect((await res.json()).error.code).toBe("INDUSTRY_NOT_FOUND");
  }
});

it("업종이 다르면 같은 동의 판정이 달라질 수 있다 (해시 기반 결정적)", async () => {
  const a = await (await call("?industry=korean_food")).json();
  const b = await (await call("?industry=cafe")).json();
  expect(a).not.toEqual(b);
  expect(a).toEqual(await (await call("?industry=korean_food")).json());
});
