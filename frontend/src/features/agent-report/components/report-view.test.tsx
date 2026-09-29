import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReportView } from "./report-view";
import { applyAgentEvent, initialAgentState } from "../lib/agent-events";

it("일부 리포트 수신 후 오류가 나면 내용을 유지하며 작성 중단을 표시한다", () => {
  const state = applyAgentEvent(initialAgentState(), {
    type: "report_delta",
    section: "reasons",
    markdown: "### 왜 안 되나\n\n수신한 상권 분석 내용입니다.",
  });
  const { rerender } = render(<ReportView state={state} />);
  expect(screen.getByText("리포트 작성 중")).toBeInTheDocument();

  rerender(<ReportView state={{ ...state, error: "분석 스트림 연결에 실패했습니다." }} />);

  expect(screen.getByText("작성 중단")).toBeInTheDocument();
  expect(screen.queryByText("리포트 작성 중")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "왜 안 되나" })).toBeInTheDocument();
  expect(screen.getByText("수신한 상권 분석 내용입니다.")).toBeInTheDocument();
});

const SECTIONS = [
  ["verdict", "판정"], ["reasons", "왜 안 되나"], ["conditions", "그래도 한다면"],
  ["alternatives", "대안 동네·업종"], ["funding", "대안 업종 지원사업"],
] as const;

it("도착 순서와 무관하게 계약의 다섯 섹션 순서로 마크다운 제목을 표시한다", () => {
  let state = initialAgentState();
  for (const [section, title] of [...SECTIONS].reverse()) {
    state = applyAgentEvent(state, { type: "report_delta", section, markdown: `### ${title}\n\n본문` });
  }
  render(<ReportView state={state} />);
  expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(SECTIONS.map(([, title]) => title));
});

it("빈 리포트에도 같은 다섯 섹션의 아웃라인을 표시한다", () => {
  render(<ReportView state={initialAgentState()} />);
  const titles = screen.getAllByText(/^(판정|왜 안 되나|그래도 한다면|대안 동네·업종|대안 업종 지원사업)$/);
  expect(titles.map((el) => el.textContent?.replace(/^0[1-5]/, ""))).toEqual(SECTIONS.map(([, title]) => title));
});
