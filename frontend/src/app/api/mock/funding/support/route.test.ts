import { expect, it } from "vitest";
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
  expect(body.loans.length).toBeGreaterThan(0);
  expect(body.district.length).toBeGreaterThan(0);
  expect(body.others.length).toBeGreaterThan(0);
  expect(body.rates.map((r: { rate_type: string }) => r.rate_type)).toEqual(["base", "loan_facility"]);
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
