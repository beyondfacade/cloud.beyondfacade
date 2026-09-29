import { afterEach, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ProgressPanel } from "./progress-panel";
import { applyAgentEvent, initialAgentState } from "../lib/agent-events";

afterEach(() => vi.restoreAllMocks());

it("동일 tool+summary 이벤트가 반복돼도 key 중복 경고가 없다", () => {
  const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

  const ev = { type: "tool_call", agent: "market", tool: "sql.query", summary: "매출 추이 조회" } as const;
  let state = initialAgentState();
  state = applyAgentEvent(state, ev);
  state = applyAgentEvent(state, ev); // 같은 도구를 같은 요약으로 두 번 호출

  render(<ProgressPanel state={state} />);

  const dupKeyWarnings = errorSpy.mock.calls.filter((args) => String(args[0]).includes("same key"));
  expect(dupKeyWarnings).toHaveLength(0);
});

it("판정 읽기 스테이지와 두 도구를 상권 진단보다 먼저 표시한다", () => {
  let state = applyAgentEvent(initialAgentState(), { type: "agent_status", agent: "verdict", status: "running" });
  for (const tool of ["get_verdict", "get_verdict_alternatives"]) {
    state = applyAgentEvent(state, { type: "tool_call", agent: "verdict", tool, summary: "판정 근거 조회" });
  }
  render(<ProgressPanel state={state} />);
  const stages = within(screen.getByRole("status")).getAllByRole("listitem").filter((li) => li.parentElement?.tagName === "OL");
  expect(stages).toHaveLength(5);
  ["오케스트레이터", "판정 읽기", "상권 진단", "충격 분석", "정책자금"].forEach((label, index) => {
    expect(within(stages[index]).getByText(label)).toBeInTheDocument();
  });
  expect(within(stages[1]).getByText("진행 중")).toBeInTheDocument();
  expect(within(stages[1]).getAllByRole("listitem")).toHaveLength(2);
});
