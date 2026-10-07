import { expect, it } from "vitest";
import { GET } from "./route";

function call(query = "") {
  return GET(new Request(`http://test/api/mock/funding/candidates${query}`));
}

it("후보 8건과 되돌아온 요청 값을 준다", async () => {
  const res = await call("?stage=pre&industry=cafe&need=31600000");
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.candidates).toHaveLength(8);
  expect(body.industry_id).toBe("cafe");
  expect(body.external_funding_need).toBe(31_600_000);
  expect(body.order).toBe("deadline");
});

it("질문이 있으면 관련 후보부터 정렬하고 관련도 순서를 표시한다", async () => {
  const res = await call(`?q=${encodeURIComponent("청년 창업")}`);
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.order).toBe("relevance");
  expect(body.candidates[0].title).toContain("청년창업");
  expect(body.candidates).toHaveLength(8);
});

it("공백뿐인 질문은 기존 후보 순서와 마감 순서 표시를 유지한다", async () => {
  const body = await (await call("?q=%20%20")).json();
  expect(body.order).toBe("deadline");
  expect(body.candidates).toEqual((await (await call()).json()).candidates);
});

it("모든 후보에 원문 링크와 걸린 규칙이 붙는다", async () => {
  const { candidates } = await (await call("?stage=pre")).json();
  for (const c of candidates) {
    expect(c.url).toMatch(/^https:\/\//);
    expect(c.why).not.toBe("");
    expect(c.is_expired).toBe(false);
  }
});

it("등록 전에는 창업 공고가, 등록 후에는 소상공인 공고가 앞선다", async () => {
  const pre = await (await call("?stage=pre")).json();
  const registered = await (await call("?stage=registered")).json();
  expect(pre.candidates[0].why).toContain("창업");
  expect(registered.candidates[0].why).toContain("소상공인");
});

it("파라미터가 전부 없어도 후보를 준다 — 셋 다 선택이다", async () => {
  const body = await (await call()).json();
  expect(body.candidates.length).toBeGreaterThan(0);
  expect(body.stage).toBeNull();
});
