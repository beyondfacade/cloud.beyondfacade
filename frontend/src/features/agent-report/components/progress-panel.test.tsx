import { afterEach, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ProgressPanel } from "./progress-panel";
import { applyAgentEvent, initialAgentState } from "../lib/agent-events";

afterEach(() => vi.restoreAllMocks());

it("동일 tool+summary 이벤트가 반복돼도 key 중복 경고가 없다", () => {
  const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

  const ev = { type: "tool_call", agent: "market", tool: "sql.query", summary: "매출 추이 조회" } as const;
  let state = initialAgentState();
  state = applyAgentEvent(state, { type: "agent_status", agent: "market", status: "running" });
  state = applyAgentEvent(state, ev);
  state = applyAgentEvent(state, ev); // 같은 도구를 같은 요약으로 두 번 호출

  render(<ProgressPanel state={state} />);

  const dupKeyWarnings = errorSpy.mock.calls.filter((args) => String(args[0]).includes("same key"));
  expect(dupKeyWarnings).toHaveLength(0);
});

it("기본 진행 패널은 사실 수집과 리포트 작성만 오케스트레이터 뒤에 표시한다", () => {
  render(<ProgressPanel state={initialAgentState()} />);
  const stages = within(screen.getByRole("status")).getAllByRole("listitem");
  expect(stages).toHaveLength(3);
  ["오케스트레이터", "사실 수집", "리포트 작성"].forEach((label, index) => {
    expect(within(stages[index]).getByText(label)).toBeInTheDocument();
  });
  for (const label of ["판정 읽기", "상권 진단", "충격 분석", "정책자금"]) {
    expect(screen.queryByText(label)).not.toBeInTheDocument();
  }
});

it.each([
  ["market", "상권 진단", "running", "진행 중"],
  ["shock", "충격 분석", "done", "완료"],
  ["funding", "정책자금", "error", "오류"],
] as const)("%s 도구 스테이지는 이벤트로 열린 상태와 도구 내역을 표시한다", (agent, label, status, statusLabel) => {
  let state = applyAgentEvent(initialAgentState(), { type: "agent_status", agent, status });
  state = applyAgentEvent(state, { type: "tool_call", agent, tool: "search", summary: "추가 자료 조회" });
  render(<ProgressPanel state={state} />);
  const stage = screen.getByText(label).closest("li")!;
  expect(within(stage).getByText(statusLabel)).toBeInTheDocument();
  expect(within(stage).getByText("search")).toBeInTheDocument();
  expect(within(screen.getByRole("status")).getAllByRole("listitem").filter((li) => li.parentElement?.tagName === "OL")).toHaveLength(4);
});
