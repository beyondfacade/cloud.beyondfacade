import { expect, it } from "vitest";
import type { SupportGuide } from "@/shared/api/types";
import { GET } from "./route";

function call(query = "") {
  return GET(new Request(`http://test/api/mock/funding/support${query}`));
}

it("세 묶음과 금리 참고값, 되돌아온 요청 값을 준다", async () => {
  const res = await call("?region=1168064000&industry=korean_food");
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.region_code).toBe("1168064000");
  expect(body.district_name).toBe("강남구");
  expect(body.industry_id).toBe("korean_food");
  expect(body.search).toBeNull();
  expect(body.loans.length).toBeGreaterThan(0);
  expect(body.district.length).toBeGreaterThan(0);
  expect(body.others.length).toBeGreaterThan(0);
  expect(body.rates.map((r: { rate_type: string }) => r.rate_type)).toEqual(["base", "loan_facility"]);
});

it("질문을 다듬어 검색 가능 여부와 가까운 공고를 최대 8건 준다", async () => {
  const query = `?region=1168064000&q=${encodeURIComponent("  소상공인 지원  ")}`;
  const res = await call(query);
  expect(res.status).toBe(200);
  const body: SupportGuide = await res.json();
  expect(body.search).toMatchObject({ query: "소상공인 지원", available: true });
  expect(body.search!.items).toHaveLength(8);
  expect(body.search!.items[0].title).toContain("소상공인");
  expect(body.search!.items[0].title).toContain("지원");
  expect((await (await call(query)).json()).search).toEqual(body.search);
  const original = await (await call("?region=1168064000")).json();
  expect({ ...body, search: null }).toEqual(original);
});

it("공백뿐인 질문은 검색 없는 응답을 준다", async () => {
  const body = await (await call("?q=%20%20%20")).json();
  expect(body.search).toBeNull();
});

it("201자 질문을 거절하지 않고 200자로 자르며 점수 없는 공고를 뺀다", async () => {
  const res = await call(`?q=${encodeURIComponent("가".repeat(201))}`);
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.search.query).toHaveLength(200);
  expect(body.search.items).toEqual([]);
});

it("대출 묶음은 금융 분야, 구 묶음은 구 전용 표시가 붙는다", async () => {
  const body = await (await call("?region=1168064000&industry=korean_food")).json();
  for (const loan of body.loans) expect(loan.field_category).toBe("금융");
  for (const program of body.district) {
    expect(program.district_match).toBe(true);
    expect(program.title).toContain("강남구");
  }
});

it("동이 없으면 구를 모르므로 구 묶음이 빈다", async () => {
  const body = await (await call()).json();
  expect(body.district_name).toBeNull();
  expect(body.district).toEqual([]);
  expect(body.loans.length).toBeGreaterThan(0);
});
