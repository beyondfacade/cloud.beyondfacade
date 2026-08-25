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
