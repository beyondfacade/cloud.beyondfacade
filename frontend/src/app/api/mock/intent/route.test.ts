import { expect, it } from "vitest";
import { POST } from "./route";

function call(body: unknown) {
  return POST(new Request("http://test/api/mock/intent", { method: "POST", body: JSON.stringify(body) }));
}

it("동·업종·예산이 다 있으면 A유형과 진단 문장을 준다", async () => {
  const res = await call({ text: "역삼1동에 카페, 예산 5천" });
  expect(res.status).toBe(200);
  const r = await res.json();
  expect(r.intent_type).toBe("A");
  expect(r.region_code).toBe("1168064000");
  expect(r.industry_id).toBe("cafe");
  expect(r.budget_krw).toBe(50_000_000);
  expect(r.diagnosis.sentence).toMatch(/^역삼1동은 .+이고, 카페는 .+에 돈이 돕니다\.$/);
  expect(r.source).toBe("rule");
});

it("'역삼동'처럼 번호 동으로 갈라지는 이름은 후보 2개로 되묻는다 (주 경로)", async () => {
  const r = await (await call({ text: "역삼동에 카페" })).json();
  expect(r.intent_type).toBe("C");
  expect(r.missing).toContain("region");
  expect(r.candidates.map((c: { region_name: string }) => c.region_name).sort()).toEqual(["역삼1동", "역삼2동"]);
  expect(r.candidates[0].district_name).toBe("강남구");
});

it("동만 있으면 B유형, 업종이 결측이다", async () => {
  const r = await (await call({ text: "연남동에서 뭘 하면 좋을까" })).json();
  expect(r.intent_type).toBe("B");
  expect(r.region_code).toBe("1144071000");
  expect(r.missing).toEqual(["industry", "budget"]);
  expect(r.diagnosis).toBeNull();
});

it("랜드마크(홍대)는 LLM 경로로 서교동을 찾는다", async () => {
  const r = await (await call({ text: "홍대 근처 미용실" })).json();
  expect(r.intent_type).toBe("A");
  expect(r.region_code).toBe("1144066000");
  expect(r.source).toBe("llm");
});

it("예산은 단위를 합산하고 맨숫자는 무시한다", async () => {
  expect((await (await call({ text: "1억 5천으로 2층에 헬스장" })).json()).budget_krw).toBe(150_000_000);
  expect((await (await call({ text: "2층에 헬스장" })).json()).budget_krw).toBeNull();
});

it("두 번째 형태(코드 쌍)는 파서를 건너뛰고 진단만 준다", async () => {
  const r = await (await call({ region_code: "1168064000", industry_id: "karaoke" })).json();
  expect(r.intent_type).toBe("A");
  expect(r.diagnosis.sentence).toContain("노래방은");
});

it("빈 문장은 500이 아니라 400 INTENT_TEXT_EMPTY다", async () => {
  const res = await call({ text: "   " });
  expect(res.status).toBe(400);
  expect((await res.json()).error.code).toBe("INTENT_TEXT_EMPTY");
});
