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

it("범위 물결표(50~299인)가 두 번 나와도 취소선으로 읽지 않는다", () => {
  const state = applyAgentEvent(initialAgentState(), {
    type: "report_delta",
    section: "analogs",
    markdown: "주 52시간제(50~299인 사업장)와 5~49인 사업장 시행 시기. ~~취소~~",
  });
  const { container } = render(<ReportView state={state} />);
  expect(screen.getByText(/50~299인 사업장\)와 5~49인 사업장 시행 시기\./)).toBeInTheDocument();
  expect([...container.querySelectorAll("del")].map((d) => d.textContent)).toEqual(["취소"]);
});

it("유사 사례 본문은 근거 표기마다 문단을, 표기 뒤와 문장마다 줄을 나눠 보여 준다", () => {
  const state = applyAgentEvent(initialAgentState(), {
    type: "report_delta",
    section: "analogs",
    markdown: "[확인된 사실] 카페는 약했습니다. 메르스 때도 약세였습니다. [참고 신호] 최근 30일 조치 소식은 없습니다.",
  });
  const { container } = render(<ReportView state={state} />);
  const paragraphs = [...container.querySelectorAll(".report-markdown p")];
  expect(paragraphs.map((p) => p.textContent)).toEqual([
    "[확인된 사실]\n카페는 약했습니다.\n메르스 때도 약세였습니다.",
    "[참고 신호]\n최근 30일 조치 소식은 없습니다.",
  ]);
  expect(paragraphs[0].querySelectorAll("br")).toHaveLength(2);
});

const SECTIONS = [
  ["verdict", "판정"], ["reasons", "왜 안 되나"], ["analogs", "유사 사례"], ["conditions", "그래도 한다면"],
  ["alternatives", "대안 동네·업종"], ["funding", "대안 업종 지원사업"],
] as const;

it("도착 순서와 무관하게 계약의 여섯 섹션 순서로 마크다운 제목을 표시한다", () => {
  let state = initialAgentState();
  for (const [section, title] of [...SECTIONS].reverse()) {
    state = applyAgentEvent(state, { type: "report_delta", section, markdown: `### ${title}\n\n본문` });
  }
  render(<ReportView state={state} />);
  expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(SECTIONS.map(([, title]) => title));
});

it("빈 리포트에도 같은 여섯 섹션의 아웃라인을 표시한다", () => {
  render(<ReportView state={initialAgentState()} />);
  const titles = screen.getAllByText(/^(판정|왜 안 되나|유사 사례|그래도 한다면|대안 동네·업종|대안 업종 지원사업)$/);
  expect(titles.map((el) => el.textContent?.replace(/^0[1-6]/, ""))).toEqual(SECTIONS.map(([, title]) => title));
});

import type { ReportFacts } from "@/shared/api/types";
import { reportFacts } from "../lib/report-facts.fixture";

it("사실만 와도 여섯 섹션의 그림과 본문 스켈레톤을 즉시 표시한다", () => {
  render(<ReportView state={{ ...initialAgentState(), facts: reportFacts() }} />);
  expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual(SECTIONS.map(([, title]) => title));
  expect(screen.getAllByLabelText("본문 작성 중")).toHaveLength(6);
  expect(screen.getByRole("status", { name: "카페 판정: 조건부" })).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "점포수 추세" })).toBeInTheDocument();
  expect(screen.getByText("원두 가격 상승")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "하루 4블록 유동 강도" })).toBeInTheDocument();
  expect(screen.getByText("창업 지원")).toBeInTheDocument();
  expect(screen.queryByText(/^대상:/)).toBeNull();
});
it("본문 조각이 그림 아래에 붙고 해당 스켈레톤만 사라지며 인용은 유지된다", () => {
  const initial = { ...initialAgentState(), facts: reportFacts() };
  const { rerender } = render(<ReportView state={initial} />);
  const next = applyAgentEvent(initial, { type: "report_delta", section: "verdict", markdown: "판정 해석입니다." });
  rerender(<ReportView state={{ ...next, done: true, citations: [{ title: "공공 자료", url: "https://example.com", grade: "fact" }] }} />);
  const chart = screen.getByRole("status", { name: "카페 판정: 조건부" });
  expect(chart.compareDocumentPosition(screen.getByText("판정 해석입니다.")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getAllByLabelText("본문 작성 중")).toHaveLength(5);
  expect(screen.getByRole("link", { name: "공공 자료" })).toBeInTheDocument();
});
it("사실 조회 실패와 필드 누락을 각 그림 자리의 자료 없음으로 처리한다", () => {
  const facts = reportFacts();
  const unavailable = { available: false, reason: "조회 실패" } as const;
  const { rerender } = render(<ReportView state={{ ...initialAgentState(), facts: { ...facts, verdict: unavailable, alternatives: unavailable, profile: unavailable, hour_gap: unavailable, commerce_change: unavailable, metrics_history: unavailable, funding_candidates: unavailable, shocks: unavailable, analogs: unavailable } }} />);
  expect(screen.getAllByText("자료 없음")).toHaveLength(11);
  rerender(<ReportView state={{ ...initialAgentState(), facts: { region: facts.region } as ReportFacts }} />);
  expect(screen.getAllByText("자료 없음")).toHaveLength(11);
});

it("리포트가 끝나면 하단에 창업 지원 정보와 다른 창업 알아보기 버튼을 동네·업종·예산과 함께 보여 준다", () => {
  const facts = { ...reportFacts(), budget: 50_000_000 };
  render(<ReportView state={{ ...initialAgentState(), facts, done: true }} />);
  const nav = screen.getByRole("navigation", { name: "다음 단계" });
  expect(nav).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /창업 지원·대출 정보 보기/ })).toHaveAttribute("href", "/support?region=1168064000&industry=cafe&budget=50000000");
  expect(screen.getByRole("link", { name: /다른 창업 알아보기/ })).toHaveAttribute("href", "/map?region=1168064000&industry=cafe&budget=50000000");
});

it("예산이 없으면 버튼 주소에서 예산을 뺀다", () => {
  render(<ReportView state={{ ...initialAgentState(), facts: reportFacts(), done: true }} />);
  expect(screen.getByRole("link", { name: /창업 지원·대출 정보 보기/ })).toHaveAttribute("href", "/support?region=1168064000&industry=cafe");
});

it("리포트가 끝나기 전이나 사실이 없으면 하단 버튼을 보여 주지 않는다", () => {
  const { rerender } = render(<ReportView state={{ ...initialAgentState(), facts: reportFacts() }} />);
  expect(screen.queryByRole("navigation", { name: "다음 단계" })).toBeNull();
  rerender(<ReportView state={{ ...initialAgentState(), done: true, sections: { verdict: "판정" } }} />);
  expect(screen.queryByRole("navigation", { name: "다음 단계" })).toBeNull();
});

it("사실 섹션 제목과 같은 마크다운 제목은 중복하지 않고 본문을 유지한다", () => {
  render(<ReportView state={{ ...initialAgentState(), facts: reportFacts(), sections: { verdict: "## 판정\n\n첫 해석입니다." } }} />);
  expect(screen.getAllByRole("heading", { name: "판정", exact: true })).toHaveLength(1);
  expect(screen.getByText("첫 해석입니다.")).toBeInTheDocument();
});

it.each(["## 판정", "판정"])("첫 본문 조각이 제목 '%s'뿐이어도 중복 제목을 지우고 후속 본문을 유지한다", (markdown) => {
  const initial = { ...initialAgentState(), facts: reportFacts() };
  const next = applyAgentEvent(initial, { type: "report_delta", section: "verdict", markdown });
  const { rerender } = render(<ReportView state={next} />);
  expect(screen.getAllByText("판정", { exact: true })).toHaveLength(1);

  rerender(<ReportView state={applyAgentEvent(next, { type: "report_delta", section: "verdict", markdown: "\n\n첫 해석입니다." })} />);
  expect(screen.getAllByText("판정", { exact: true })).toHaveLength(1);
  expect(screen.getByText("첫 해석입니다.")).toBeInTheDocument();
});

it.each([
  ["카페", "카페는 언제 돈이 도나"],
  ["미용실", "미용실은 언제 돈이 도나"],
])("사실의 업종 %s에 맞춰 시간대 제목과 조사를 표시한다", (industryName, title) => {
  const facts = reportFacts();
  render(<ReportView state={{ ...initialAgentState(), facts: { ...facts, region: { ...facts.region, industry_name: industryName } } }} />);
  expect(screen.getByRole("heading", { level: 3, name: title })).toBeInTheDocument();
});
