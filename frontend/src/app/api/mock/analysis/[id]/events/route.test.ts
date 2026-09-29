import { afterEach, expect, it, vi } from "vitest";
import type { AgentEvent } from "@/shared/api/types";
import { GET } from "./route";

afterEach(() => vi.useRealTimers());

async function readEvents() {
  vi.useFakeTimers();
  const response = await GET(new Request("http://test/api/mock/analysis/a1/events"));
  expect(response.status).toBe(200);
  expect(response.headers.get("Content-Type")).toBe("text/event-stream");
  const body = response.text();
  await vi.runAllTimersAsync();
  const frames = (await body).trim().split("\n\n");
  const events = frames.map((frame) => {
    const [event, data] = frame.split("\n");
    const parsed: AgentEvent = JSON.parse(data.slice("data: ".length));
    expect(event).toBe(`event: ${parsed.type}`);
    return parsed;
  });
  return events;
}

it("SSE는 판정 스테이지를 다른 분석 스테이지보다 먼저 연다", async () => {
  const events = await readEvents();
  expect(events.filter((e): e is Extract<AgentEvent, { type: "agent_status" }> => e.type === "agent_status" && e.status === "running").map((e) => e.agent))
    .toEqual(["orchestrator", "verdict", "market", "shock", "funding"]);
});

it("SSE는 판정과 대안 조회 도구를 순서대로 보낸다", async () => {
  const events = await readEvents();
  expect(events.filter((e): e is Extract<AgentEvent, { type: "tool_call" }> => e.type === "tool_call" && e.agent === "verdict").map((e) => e.tool))
    .toEqual(["get_verdict", "get_verdict_alternatives"]);
});

it("SSE는 다섯 섹션을 계약 제목과 순서로 보낸 뒤 완료한다", async () => {
  const events = await readEvents();
  expect(events.filter((e) => e.type === "report_delta").map((e) => [e.section, e.markdown.split("\n")[0]]))
    .toEqual([
      ["verdict", "### 판정"], ["reasons", "### 왜 안 되나"], ["conditions", "### 그래도 한다면"],
      ["alternatives", "### 대안 동네·업종"], ["funding", "### 대안 업종 지원사업"],
    ]);
  expect(events.at(-1)).toMatchObject({ type: "report_done", report_id: expect.any(String), citations: expect.any(Array) });
});
