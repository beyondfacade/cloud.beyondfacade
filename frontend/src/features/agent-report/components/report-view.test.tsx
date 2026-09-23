import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReportView } from "./report-view";
import { applyAgentEvent, initialAgentState } from "../lib/agent-events";

it("일부 리포트 수신 후 오류가 나면 내용을 유지하며 작성 중단을 표시한다", () => {
  const state = applyAgentEvent(initialAgentState(), {
    type: "report_delta",
    section: "market",
    markdown: "## 상권 진단\n\n수신한 상권 분석 내용입니다.",
  });
  const { rerender } = render(<ReportView state={state} />);
  expect(screen.getByText("리포트 작성 중")).toBeInTheDocument();

  rerender(<ReportView state={{ ...state, error: "분석 스트림 연결에 실패했습니다." }} />);

  expect(screen.getByText("작성 중단")).toBeInTheDocument();
  expect(screen.queryByText("리포트 작성 중")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "상권 진단" })).toBeInTheDocument();
  expect(screen.getByText("수신한 상권 분석 내용입니다.")).toBeInTheDocument();
});
