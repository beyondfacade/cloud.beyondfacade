import type { ReportFacts } from "@/shared/api/types";
import { expect, it } from "vitest";
import { applyAgentEvent, initialAgentState } from "./agent-events";

it("agent_status가 해당 에이전트 상태를 갱신한다", () => {
  const s = applyAgentEvent(initialAgentState(),
    { type: "agent_status", agent: "market", status: "running" });
  expect(s.agents.market.status).toBe("running");
});
it("tool_call은 해당 에이전트 타임라인에 누적된다", () => {
  let s = initialAgentState();
  s = applyAgentEvent(s, { type: "tool_call", agent: "market", tool: "지표조회", summary: "강남 카페 폐업률" });
  s = applyAgentEvent(s, { type: "tool_call", agent: "market", tool: "지표조회", summary: "경쟁밀도" });
  expect(s.agents.market.tools).toHaveLength(2);
});
it("report_delta는 섹션별로 이어붙는다", () => {
  let s = initialAgentState();
  s = applyAgentEvent(s, { type: "report_delta", section: "verdict", markdown: "## 결론\n" });
  s = applyAgentEvent(s, { type: "report_delta", section: "verdict", markdown: "가능" });
  expect(s.sections.verdict).toBe("## 결론\n가능");
});
it("report_done이면 done=true", () => {
  const s = applyAgentEvent(initialAgentState(),
    { type: "report_done", report_id: "r1", citations: [] });
  expect(s.done).toBe(true);
});

it("초기 상태는 사실 없이 여섯 스테이지를 대기로 둔다", () => {
  const state = initialAgentState();
  expect(state.facts).toBeNull();
  expect(Object.keys(state.agents)).toEqual(["orchestrator", "facts", "writer", "market", "shock", "funding"]);
  expect(Object.values(state.agents).every((slot) => slot.status === "idle")).toBe(true);
});

it("사실 수집과 리포트 작성 스테이지를 독립적으로 갱신한다", () => {
  let state = applyAgentEvent(initialAgentState(), { type: "agent_status", agent: "facts", status: "done" });
  state = applyAgentEvent(state, { type: "agent_status", agent: "writer", status: "running" });
  expect(state.agents.facts.status).toBe("done");
  expect(state.agents.writer.status).toBe("running");
});

it("facts는 자료 없음 항목도 그대로 저장하고 이후 본문 조각과 완료에도 유지한다", () => {
  const unavailable = { available: false, reason: "자료 없음" } as const;
  const facts: ReportFacts = {
    region: { code: "1168064000", name: "역삼1동", industry_id: "cafe", industry_name: "카페" },
    verdict: unavailable, alternatives: unavailable, profile: unavailable,
    hour_gap: unavailable, commerce_change: unavailable, metrics_history: unavailable,
    population: unavailable, shocks: unavailable, news: unavailable, funding_candidates: unavailable,
    budget: null,
  };
  const before = initialAgentState();
  let state = applyAgentEvent(before, { type: "facts", facts });
  expect(state.facts).toBe(facts);
  expect(before.facts).toBeNull();
  expect(state.sections).toEqual({});
  state = applyAgentEvent(state, { type: "report_delta", section: "verdict", markdown: "첫 문장. " });
  state = applyAgentEvent(state, { type: "report_delta", section: "verdict", markdown: "다음 문장." });
  state = applyAgentEvent(state, { type: "report_done", report_id: "r1", citations: [] });
  expect(state.facts).toBe(facts);
  expect(state.sections.verdict).toBe("첫 문장. 다음 문장.");
});
