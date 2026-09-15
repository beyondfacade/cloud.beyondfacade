import { afterEach, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
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
